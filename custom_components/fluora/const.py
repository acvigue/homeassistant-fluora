"""Constants for the Koios Digital Clock integration."""

DOMAIN = "koiosdigital"

# Device models
MODEL_FIBONACCI = "fibonacci"
MODEL_NIXIE = "nixie"
MODEL_WORDCLOCK = "wordclock"
MODEL_MATRX = "matrx"
MODEL_TRANQUIL = "tranquil"

# API endpoints
API_ABOUT = "/api/about"
API_SYSTEM_CONFIG = "/api/system/config"
API_TIME_ZONEDB = "/api/time/zonedb"
API_LED_EFFECTS = "/api/led/effects"
API_LED_CONFIG = "/api/led/config"
API_LED_CHANNEL = "/api/led/channel"  # Base path, append /{channelIndex}
API_NIXIE = "/api/nixie"
API_NIXIE_WS = "/api/nixie/ws"
API_FIBONACCI = "/api/fibonacci"
API_FIBONACCI_WS = "/api/fibonacci/ws"

# LED effects mapping (API ID -> Display Name)
LED_EFFECTS = {
    "SOLID": "Solid",
    "BLINK": "Blink", 
    "BREATHE": "Breathe",
    "CYCLIC": "Cyclic",
    "RAINBOW": "Rainbow",
    "COLOR_WIPE": "Color Wipe",
    "THEATER_CHASE": "Theater Chase",
    "SPARKLE": "Sparkle",
}

# Default LED channel indices
LED_CHANNEL_BACKLIGHT = 0

# Default update interval (30 seconds as requested)
DEFAULT_UPDATE_INTERVAL = 30

# zeroconf service type
ZEROCONF_TYPE = "_koiosdigital._tcp.local."
