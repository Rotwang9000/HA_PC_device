DOMAIN = "pc"

# Services
SERVICE_SET_VOLUME = "set_volume"
SERVICE_MUTE = "mute"
SERVICE_LOCK = "lock"

# Attributes
ATTR_VOLUME_LEVEL = "volume_level"
ATTR_ACTIVE_WINDOW = "activewindow"
ATTR_SESSION_STATE = "sessionstate"

# Configuration
CONF_DEVICE_NAME = "device_name"
CONF_POWER_ON_ACTION = "power_on_action"
CONF_POWER_OFF_ACTION = "power_off_action"

# Power On/Off Actions
POWER_ON_POWER = "power_on"
POWER_ON_WAKE = "wake"
POWER_ON_ACTIONS = [POWER_ON_POWER, POWER_ON_WAKE]

POWER_OFF_POWER = "power_off"
POWER_OFF_HIBERNATE = "hibernate"
POWER_OFF_SLEEP = "sleep"
POWER_OFF_ACTIONS = [POWER_OFF_POWER, POWER_OFF_HIBERNATE, POWER_OFF_SLEEP]
