"""Exceptions for Koios Digital Clock integration."""


class KoiosClockError(Exception):
    """Base exception for Koios Clock integration."""


class KoiosClockConnectionError(KoiosClockError):
    """Exception to indicate connection issues."""


class KoiosClockAuthError(KoiosClockError):
    """Exception to indicate authentication issues."""


class KoiosClockAPIError(KoiosClockError):
    """Exception to indicate API call issues."""


class KoiosClockConfigError(KoiosClockError):
    """Exception to indicate configuration issues."""


class KoiosClockTimeoutError(KoiosClockError):
    """Exception to indicate timeout issues."""
