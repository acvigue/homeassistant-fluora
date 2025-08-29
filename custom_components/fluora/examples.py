"""Examples of automations for Koios Digital Clock integration."""

# Example automation configurations for Home Assistant

EXAMPLE_AUTOMATIONS = [
    {
        "alias": "Koios Clock Sunrise Colors",
        "description": "Change clock colors based on time of day",
        "trigger": [
            {"platform": "sun", "event": "sunrise"},
            {"platform": "sun", "event": "sunset"},
        ],
        "action": [
            {
                "choose": [
                    {
                        "conditions": [
                            {"condition": "sun", "after": "sunrise", "before": "sunset"}
                        ],
                        "sequence": [
                            {
                                "service": "light.turn_on",
                                "target": {"entity_id": "light.koiosdigital_backlight"},
                                "data": {
                                    "rgbw_color": [255, 255, 0, 0],  # Yellow for day
                                    "effect": "Solid",
                                    "brightness": 200,
                                },
                            }
                        ],
                    },
                    {
                        "conditions": [
                            {"condition": "sun", "after": "sunset"}
                        ],
                        "sequence": [
                            {
                                "service": "light.turn_on",
                                "target": {"entity_id": "light.koiosdigital_backlight"},
                                "data": {
                                    "rgbw_color": [255, 100, 0, 0],  # Orange for evening
                                    "effect": "Breathe",
                                    "brightness": 100,
                                },
                            }
                        ],
                    },
                ]
            }
        ],
    },
    {
        "alias": "Koios Clock Night Mode",
        "description": "Dim clock at night",
        "trigger": [
            {"platform": "time", "at": "22:00:00"},
            {"platform": "time", "at": "07:00:00"},
        ],
        "action": [
            {
                "choose": [
                    {
                        "conditions": [
                            {"condition": "time", "after": "22:00:00"}
                        ],
                        "sequence": [
                            {
                                "service": "number.set_value",
                                "target": {"entity_id": "number.koiosdigital_led_brightness"},
                                "data": {"value": 50},
                            }
                        ],
                    },
                    {
                        "conditions": [
                            {"condition": "time", "after": "07:00:00", "before": "22:00:00"}
                        ],
                        "sequence": [
                            {
                                "service": "number.set_value",
                                "target": {"entity_id": "number.koiosdigital_led_brightness"},
                                "data": {"value": 200},
                            }
                        ],
                    },
                ]
            }
        ],
    },
    {
        "alias": "Koios Fibonacci Theme Rotation",
        "description": "Rotate through Fibonacci themes hourly",
        "trigger": [
            {"platform": "time_pattern", "minutes": 0}
        ],
        "action": [
            {
                "service": "select.select_next",
                "target": {"entity_id": "select.koiosdigital_fibonacci_theme"},
            }
        ],
        "condition": [
            {"condition": "state", "entity_id": "binary_sensor.workday_sensor", "state": "on"}
        ],
    },
    {
        "alias": "Koios Clock Holiday Effects",
        "description": "Special effects for holidays",
        "trigger": [
            {"platform": "homeassistant", "event": "start"},
            {"platform": "time", "at": "00:00:00"},
        ],
        "action": [
            {
                "choose": [
                    {
                        "conditions": [
                            {"condition": "template", "value_template": "{{ now().month == 12 and now().day == 25 }}"}
                        ],
                        "sequence": [
                            {
                                "service": "light.turn_on",
                                "target": {"entity_id": "light.koiosdigital_backlight"},
                                "data": {
                                    "rgbw_color": [255, 0, 0, 0],  # Red for Christmas
                                    "effect": "blink",
                                },
                            }
                        ],
                    },
                    {
                        "conditions": [
                            {"condition": "template", "value_template": "{{ now().month == 10 and now().day == 31 }}"}
                        ],
                        "sequence": [
                            {
                                "service": "light.turn_on",
                                "target": {"entity_id": "light.koiosdigital_backlight"},
                                "data": {
                                    "rgbw_color": [255, 165, 0, 0],  # Orange for Halloween
                                    "effect": "cyclic",
                                },
                            }
                        ],
                    },
                ]
            }
        ],
    },
    {
        "alias": "Koios Clock Weather Colors",
        "description": "Change colors based on weather",
        "trigger": [
            {"platform": "state", "entity_id": "weather.home"},
        ],
        "action": [
            {
                "choose": [
                    {
                        "conditions": [
                            {"condition": "state", "entity_id": "weather.home", "state": "sunny"}
                        ],
                        "sequence": [
                            {
                                "service": "light.turn_on",
                                "target": {"entity_id": "light.koiosdigital_backlight"},
                                "data": {
                                    "rgbw_color": [255, 255, 0, 0],  # Yellow for sunny
                                    "effect": "solid",
                                },
                            }
                        ],
                    },
                    {
                        "conditions": [
                            {"condition": "state", "entity_id": "weather.home", "state": "rainy"}
                        ],
                        "sequence": [
                            {
                                "service": "light.turn_on",
                                "target": {"entity_id": "light.koiosdigital_backlight"},
                                "data": {
                                    "rgbw_color": [0, 100, 255, 0],  # Blue for rainy
                                    "effect": "breathe",
                                },
                            }
                        ],
                    },
                    {
                        "conditions": [
                            {"condition": "state", "entity_id": "weather.home", "state": "cloudy"}
                        ],
                        "sequence": [
                            {
                                "service": "light.turn_on",
                                "target": {"entity_id": "light.koiosdigital_backlight"},
                                "data": {
                                    "rgbw_color": [128, 128, 128, 50],  # Gray for cloudy
                                    "effect": "solid",
                                },
                            }
                        ],
                    },
                ]
            }
        ],
    },
]
