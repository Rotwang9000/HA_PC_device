"""Config flow for Computer integration."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from .const import (
    DOMAIN, CONF_DEVICE_NAME,
    CONF_POWER_ON_ACTION, CONF_POWER_OFF_ACTION,
    POWER_ON_POWER, POWER_ON_WAKE,
    POWER_OFF_POWER, POWER_OFF_HIBERNATE, POWER_OFF_SLEEP
)

_LOGGER = logging.getLogger(__name__)

class ComputerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Computer integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                # Set unique ID based on device name for better identification
                await self.async_set_unique_id(user_input[CONF_DEVICE_NAME].lower())
                
                # Check if already configured with this unique ID
                self._abort_if_unique_id_configured()
                
                # Create the config entry
                return self.async_create_entry(
                    title=user_input[CONF_DEVICE_NAME],
                    data=user_input
                )
            except Exception as e:
                _LOGGER.exception("Error creating config entry: %s", e)
                errors["base"] = "unknown"

        # Show the configuration form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_NAME): str,
                vol.Required(CONF_POWER_ON_ACTION, default=POWER_ON_POWER): vol.In([
                    POWER_ON_POWER, 
                    POWER_ON_WAKE
                ]),
                vol.Required(CONF_POWER_OFF_ACTION, default=POWER_OFF_POWER): vol.In([
                    POWER_OFF_POWER, 
                    POWER_OFF_HIBERNATE, 
                    POWER_OFF_SLEEP
                ])
            }),
            errors=errors
        ) 