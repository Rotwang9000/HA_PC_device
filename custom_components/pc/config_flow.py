import voluptuous as vol
from homeassistant import config_entries
from .const import (
    DOMAIN, CONF_DEVICE_NAME, CONF_FS_NAME,
    CONF_POWER_ON_ACTION, CONF_POWER_OFF_ACTION,
    CONF_ENFORCE_LOCK,
    POWER_ON_ACTIONS, POWER_OFF_ACTIONS
)

# Remove Family Safety options from actions
POWER_ON_ACTIONS.remove("fs_unlock")
POWER_OFF_ACTIONS.remove("fs_lock")

class PCConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PC Device."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_DEVICE_NAME): str,
                        vol.Optional(CONF_FS_NAME): str,
                        vol.Required(CONF_POWER_ON_ACTION, default=POWER_ON_POWER): vol.In(POWER_ON_ACTIONS),
                        vol.Required(CONF_POWER_OFF_ACTION, default=POWER_OFF_POWER): vol.In(POWER_OFF_ACTIONS),
                        vol.Optional(CONF_ENFORCE_LOCK, default=False): bool,
                    }
                ),
            )

        # Validate the input
        device_name = user_input[CONF_DEVICE_NAME]
        fs_name = user_input.get(CONF_FS_NAME, "")
        power_on_action = user_input[CONF_POWER_ON_ACTION]
        power_off_action = user_input[CONF_POWER_OFF_ACTION]
        enforce_lock = user_input.get(CONF_ENFORCE_LOCK, False)

        # Ensure unique device name
        await self.async_set_unique_id(device_name.lower())
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"PC {device_name}",
            data={
                CONF_DEVICE_NAME: device_name,
                CONF_FS_NAME: fs_name,
                CONF_POWER_ON_ACTION: power_on_action,
                CONF_POWER_OFF_ACTION: power_off_action,
                CONF_ENFORCE_LOCK: enforce_lock,
            },
        )
