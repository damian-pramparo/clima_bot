from enum import Enum


class WeatherEventType(str, Enum):
    FROST = "frost"
    RAIN = "rain"
    HAIL = "hail"
    STORM = "storm"
    HEAT_WAVE = "heat_wave"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    READ = "read"
