"""PixelAirDevice - Individual device management and OSC control.

This module provides the PixelAirDevice class that handles individual device state,
packet decoding, and OSC command sending.
"""

import asyncio
import threading
import logging
import socket
import time
from typing import Any

from pythonosc.osc_message_builder import OscMessageBuilder

from .fragmented_state_manager import FragmentedStateManager
from .pixelair_generated import PixelAirDevice as PixelAirDeviceFB
from .pixelair_state import PixelAirState


class PixelAirDevice:
    """A PixelAir device."""

    def __init__(self, ip_address: str) -> None:
        """Initialize a PixelAir device.

        Args:
            ip_address: IP address of the device (used as the device identifier)
        """
        self.ip_address = ip_address
        self.last_seen = 0.0
        self.fragment_manager = FragmentedStateManager(self._complete_packet_handler)

        # UDP listener thread for receiving state packets
        self._udp_listener_thread = None
        self._udp_listener_running = False
        self._udp_socket = None

        # Device state tracking
        self.last_decoded_state: PixelAirDeviceFB | None = None
        self.state = PixelAirState()
        # State packet waiting infrastructure
        # Store tuples of (asyncio.Event, loop) so notifications from other
        # threads can call loop.call_soon_threadsafe(event.set).
        self._state_waiters: list[tuple[asyncio.Event, asyncio.AbstractEventLoop]] = []
        self._state_waiters_lock: asyncio.Lock | None = None

        # Logger for this device
        self.logger = logging.getLogger(f"PixelAirDevice:{self.ip_address}")
        # Thread lock to allow thread-safe notifications from non-async threads
        self._state_waiters_thread_lock = threading.Lock()

        # Start UDP listener thread
        self._start_udp_listener()

    def _complete_packet_handler(self, payload: bytes):
        """Handle a complete packet from the fragment manager.
        
        This is the callback passed to FragmentedStateManager.
        
        Args:
            payload: Complete assembled payload bytes
        """
        self._update_last_seen()
        self._handle_state_packet(payload)

    def _start_udp_listener(self):
        """Start the UDP listener thread."""
        if self._udp_listener_thread is not None and self._udp_listener_thread.is_alive():
            return
            
        self._udp_listener_running = True
        self._udp_listener_thread = threading.Thread(
            target=self._udp_listener_worker,
            daemon=True,
            name=f"UDP-Listener-{self.ip_address}"
        )
        self._udp_listener_thread.start()
        self.logger.debug("Started UDP listener thread for %s", self.ip_address)

    def _stop_udp_listener(self):
        """Stop the UDP listener thread."""
        self._udp_listener_running = False
        if self._udp_socket:
            try:
                self._udp_socket.close()
            except Exception:
                pass
        if self._udp_listener_thread and self._udp_listener_thread.is_alive():
            self._udp_listener_thread.join(timeout=1.0)
        self.logger.debug("Stopped UDP listener thread for %s", self.ip_address)

    def _udp_listener_worker(self):
        """UDP listener worker thread that receives packets on port 12345."""
        try:
            # Create UDP socket with reuse address/port options
            self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Try to set SO_REUSEPORT if available (not available on all platforms)
            try:
                self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except (AttributeError, OSError):
                # SO_REUSEPORT not available or not supported
                pass
                
            self._udp_socket.bind(('', 12345))  # Bind to all interfaces on port 12345
            self._udp_socket.settimeout(1.0)  # 1 second timeout for recv
            
            self.logger.debug("UDP listener bound to port 12345 for device %s", self.ip_address)
            
            while self._udp_listener_running:
                try:
                    data, addr = self._udp_socket.recvfrom(4096)  # 4KB buffer
                    self.logger.debug(
                        "Received UDP packet from %s:%s for device %s (%d bytes)",
                        addr[0], addr[1], self.ip_address, len(data)
                    )
                    
                    # Process the packet through the fragment manager
                    try:
                        self.fragment_manager.process_buffer(data)
                    except ValueError as e:
                        self.logger.warning(
                            "Invalid packet received from %s:%s for device %s: %s",
                            addr[0], addr[1], self.ip_address, e
                        )
                        
                except socket.timeout:
                    # Timeout is expected, continue listening
                    continue
                except OSError as e:
                    if self._udp_listener_running:
                        self.logger.error(
                            "UDP listener error for device %s: %s", self.ip_address, e
                        )
                    break
                        
        except Exception as e:
            self.logger.error(
                "UDP listener thread failed for device %s: %s", self.ip_address, e
            )
        finally:
            if self._udp_socket:
                try:
                    self._udp_socket.close()
                except Exception:
                    pass
                self._udp_socket = None
            self.logger.debug("UDP listener thread finished for %s", self.ip_address)

    def _ensure_async_lock(self):
        """Ensure the async lock exists (create it lazily)."""
        if self._state_waiters_lock is None:
            self._state_waiters_lock = asyncio.Lock()

    async def set_power(self, on: bool) -> bool:
        """Set the power state of the device.

        Args:
            on: True to turn on, False to turn off

        Returns:
            bool: True if command was sent successfully, False otherwise
        """
        route = "/SyYOTiXjQBjW"
        params = [1 if on else 0]
        await self._send_osc_message(route, params)
        await self.get_state()  # Request updated state after changing power
        return True

    async def set_brightness(self, brightness: int) -> bool:
        """Set the brightness of the device.

        Args:
            brightness: Brightness level (0-100)

        Returns:
            bool: True if command was sent successfully, False otherwise
        """
        if brightness < 0 or brightness > 100:
            self.logger.error("Brightness must be between 0 and 100")
            return False

        route = "/Uv7aMFw5P2lX"
        params = [float(brightness) / 100.0]
        await self._send_osc_message(route, params)
        await self.get_state()  # Request updated state after changing brightness
        return True

    async def get_state(self, timeout: float = 5.0) -> bool:
        """Request the current state from the device.

        Returns:
            bool: True if command was sent successfully and response received, False otherwise
        """
        route = "/fluoraDiscovery"
        ip = self._get_recv_ip()
        self.logger.warning("Getting state for device %s, local IP: %s", self.ip_address, ip)

        # convert to list of ascii chars
        ip_chars = [ord(c) for c in ip]
        self.logger.info(ip)

        result = await self._send_osc_and_wait_for_state(
            route, ip_chars, timeout=timeout, port=9090
        )
        self.logger.debug("get_state result for %s: %s", self.ip_address, result)
        return result

    async def _send_osc_message(
        self,
        route: str,
        params: list[int | float | str | bool] | None = None,
        port: int = 6767,
    ) -> bool:
        """Send a binary OSC message to the device on port 6767.

        This is a private helper method for sending OSC commands to the device.

        Args:
            route: OSC route/address (e.g., "/device/brightness")
            params: Optional list of parameters to include in the message
            port: UDP port to send the message to (default 6767)

        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if params is None:
            params = []

        try:
            # Build the OSC message
            msg_builder = OscMessageBuilder(route)

            # Add parameters to the message
            for param in params:
                if isinstance(param, int):
                    msg_builder.add_arg(param, "i")  # integer
                elif isinstance(param, float):
                    msg_builder.add_arg(param, "f")  # float
                elif isinstance(param, str):
                    msg_builder.add_arg(param, "s")  # string
                elif isinstance(param, bool):
                    msg_builder.add_arg(param, "T" if param else "F")  # true/false
                else:
                    # Try to convert to string as fallback
                    msg_builder.add_arg(str(param), "s")

            # Build the binary message
            osc_message = msg_builder.build()

            # Send the message asynchronously
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, self._send_udp_message, osc_message.dgram, port
            )
            self.logger.debug(
                "Sent OSC message to %s:%s - Route: %s, Params: %s",
                self.ip_address,
                port,
                route,
                params,
            )
        except Exception as e:  # noqa: BLE001
            self.logger.error(
                "Failed to send OSC message to %s:%s - Route: %s, Error: %s",
                self.ip_address,
                port,
                route,
                e,
            )
            return False
        return True

    def _get_recv_ip(self) -> str:
        """Fallback method to get local IP by attempting to connect to the device.

        Returns:
            Local IP address that would be used to connect to the device
        """
        # Create a socket and connect to the device to see which local IP is used
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            # Connect to the device IP (doesn't actually send data for UDP)
            sock.connect((self.ip_address, 6767))
            return sock.getsockname()[0]

    def _handle_state_packet(self, payload: bytes):
        """Handle a decoded PixelAir device state packet.

        This method can be overridden by subclasses to implement
        device-specific state handling logic.

        Args:
            device_state: Decoded PixelAir device state FlatBuffer
            is_response: True if this is a response to a request, False if proactive
        """
        # Default implementation logs basic device information
        device_state = PixelAirDeviceFB.GetRootAs(payload)
        self.last_decoded_state = device_state
        
        model = device_state.Model().decode('utf-8') or "Unknown"
        serial = device_state.SerialNumber().decode('utf-8') or "Unknown"
        mac = device_state.Network().MacAddress().decode("utf-8") or "Unknown"

        self.state.model = model
        self.state.serial_number = serial
        self.state.mac_address = mac

        if device_state.Nickname():
            self.state.nickname = device_state.Nickname().Value().decode('utf-8')

        if device_state.Engine():
            self.state.is_on = device_state.Engine().IsDisplaying().Value()
            if device_state.Engine().Brightness():
                self.state.brightness = (
                    device_state.Engine().Brightness().Value() * 100.0
                )

        # Notify any waiting coroutines. Prefer scheduling via the event loop
        # if available; otherwise, use thread-safe notifications so packet
        # handlers running on non-event-loop threads still wake waiters.
        try:
            # If we're already in an event loop, schedule the async notifier
            asyncio.get_running_loop()
            asyncio.ensure_future(self._notify_state_waiters())
        except RuntimeError:
            # Not in async loop, notify waiters directly in a thread-safe way
            self._notify_state_waiters_threadsafe()

    async def _notify_state_waiters(self):
        """Notify all state waiters that a new state packet has arrived."""
        self._ensure_async_lock()
        async with self._state_waiters_lock:
            # Copy waiters under lock and notify them
            with self._state_waiters_thread_lock:
                waiters_copy = list(self._state_waiters)
                
            for event, _ in waiters_copy:
                try:
                    event.set()
                except Exception:
                    self.logger.debug("Failed to notify one state waiter (async)")

    def _notify_state_waiters_threadsafe(self):
        """Notify state waiters from any thread using their event loops."""
        # Copy waiters under thread lock and call loop.call_soon_threadsafe
        with self._state_waiters_thread_lock:
            waiters_copy = list(self._state_waiters)

        for event, loop in waiters_copy:
            try:
                loop.call_soon_threadsafe(event.set)
            except Exception:
                try:
                    event.set()
                except Exception:
                    self.logger.debug("Failed to notify one state waiter (threadsafe)")

    async def _send_osc_and_wait_for_state(
        self,
        route: str,
        params: list[int | float | str | bool] | None = None,
        timeout: float = 5.0,
        max_responses: int = 1,
        port: int = 6767,
    ) -> bool:
        """Send an OSC packet and wait for state packet responses.

        Args:
            route: OSC route/address (e.g., "/device/brightness")
            params: Optional list of parameters to include in the message
            timeout: Maximum time to wait for responses in seconds
            max_responses: Maximum number of state responses to wait for (1 or more)
            port: UDP port to send the message to (default 6767)

        Returns:
            bool: True if the OSC message was sent and at least one state response was received, False otherwise
        """
        if params is None:
            params = []

        # Create an event to wait for state packet responses
        # Create an event to wait for state packet responses
        response_event = asyncio.Event()
        response_loop = asyncio.get_running_loop()
        responses_received = 0

        # Add our event to the waiters list
        self._ensure_async_lock()
        async with self._state_waiters_lock:
            # Also acquire thread lock briefly to mutate the list safely for
            # thread-based notifiers.
            with self._state_waiters_thread_lock:
                self._state_waiters.append((response_event, response_loop))
            self.logger.debug("Added response event to waiters list. Total waiters: %d", len(self._state_waiters))

        try:
            start_time = time.time()
            last_send_time = 0.0
            
            # Initial send
            self.logger.debug("Sending OSC message to %s:%s - Route: %s", self.ip_address, port, route)
            send_success = await self._send_osc_message(route, params, port)
            if not send_success:
                self.logger.warning("Failed to send OSC message to %s:%s", self.ip_address, port)
                return False
            
            last_send_time = time.time()
            self.logger.debug("OSC message sent successfully, waiting for response...")
            
            # Wait for state packet responses with retry logic
            while responses_received < max_responses:
                try:
                    # Calculate remaining timeout
                    elapsed_time = time.time() - start_time
                    remaining_timeout = timeout - elapsed_time
                    
                    if remaining_timeout <= 0:
                        self.logger.warning(
                            "Overall timeout reached waiting for response from %s",
                            self.ip_address,
                        )
                        break
                    
                    # Wait for response with 1 second timeout max (for retry interval)
                    wait_timeout = min(1.0, remaining_timeout)
                    self.logger.debug("Waiting for state response %d/%d...", responses_received + 1, max_responses)
                    await asyncio.wait_for(response_event.wait(), timeout=wait_timeout)
                    responses_received += 1
                    self.logger.debug("Received state response %d/%d", responses_received, max_responses)

                    # If we're expecting more responses, clear the event and continue waiting
                    if responses_received < max_responses:
                        response_event.clear()

                except TimeoutError:
                    # Check if we should retry sending
                    current_time = time.time()
                    if current_time - last_send_time >= 1.0:  # Retry every second
                        elapsed_time = current_time - start_time
                        if elapsed_time < timeout:
                            self.logger.debug("Retrying OSC message to %s:%s after 1 second", self.ip_address, port)
                            retry_success = await self._send_osc_message(route, params, port)
                            if retry_success:
                                last_send_time = current_time
                            else:
                                self.logger.warning("Failed to retry OSC message to %s:%s", self.ip_address, port)
                        else:
                            self.logger.warning(
                                "Overall timeout reached waiting for state response %d/%d from %s",
                                responses_received + 1,
                                max_responses,
                                self.ip_address,
                            )
                            break

            return responses_received > 0

        finally:
            # Clean up: remove our event from the waiters list
            self._ensure_async_lock()
            async with self._state_waiters_lock:
                # Remove the tuple matching our event. Use thread lock while
                # mutating to keep thread notifiers safe.
                to_remove = None
                with self._state_waiters_thread_lock:
                    for ev, lp in self._state_waiters:
                        if ev is response_event:
                            to_remove = (ev, lp)
                            break
                    if to_remove is not None:
                        self._state_waiters.remove(to_remove)
                if to_remove is not None:
                    self.logger.debug("Removed response event from waiters list. Remaining waiters: %d", len(self._state_waiters))

    def _send_udp_message(self, dgram: bytes, port: int = 6767) -> None:
        """Send a UDP datagram synchronously.

        This method is called from an executor to avoid blocking the event loop.

        Args:
            dgram: The UDP datagram to send
            port: The port to send to (default 6767)
        """
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5.0)  # 5 second timeout
            sock.sendto(dgram, (self.ip_address, port))

    def _update_last_seen(self):
        """Update the last seen timestamp."""
        self.last_seen = time.time()

    def close(self):
        """Clean up resources and stop background threads."""
        self._stop_udp_listener()

    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.close()
        except Exception:
            pass

    def __str__(self) -> str:
        """String representation of the device."""
        return f"PixelAirDevice({self.ip_address})"

    def __repr__(self) -> str:
        """Detailed string representation of the device."""
        return self.__str__()
