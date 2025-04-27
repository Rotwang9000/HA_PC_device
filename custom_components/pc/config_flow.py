import voluptuous as vol
from homeassistant import config_entries
from .const import (
    DOMAIN, CONF_DEVICE_NAME,
    CONF_POWER_ON_ACTION, CONF_POWER_OFF_ACTION,
    POWER_ON_POWER, POWER_ON_ACTIONS,
    POWER_OFF_POWER, POWER_OFF_ACTIONS
)

class PCConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PC Device."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # Validate the device name (basic check for invalid characters)
            device_name = user_input[CONF_DEVICE_NAME]
            if not device_name or not device_name.isalnum():
                errors["base"] = "invalid_device_name"
            else:
                # Ensure unique device name
                await self.async_set_unique_id(device_name.lower())
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"PC {device_name}",
                    data={
                        CONF_DEVICE_NAME: device_name,
                        CONF_POWER_ON_ACTION: user_input[CONF_POWER_ON_ACTION],
                        CONF_POWER_OFF_ACTION: user_input[CONF_POWER_OFF_ACTION],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_NAME): str,
                    vol.Required(CONF_POWER_ON_ACTION, default=POWER_ON_POWER): vol.In(POWER_ON_ACTIONS),
                    vol.Required(CONF_POWER_OFF_ACTION, default=POWER_OFF_POWER): vol.In(POWER_OFF_ACTIONS),
                }
            ),
            errors=errors,
        )
