from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from .const import DOMAIN, CONF_DEVICE_NAME, CONF_FS_NAME, CONF_USE_FS_LOCK

class PCConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PC Device."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=self.hass.data["voluptuous"].Schema(
                    {
                        self.hass.data["voluptuous"].Required(CONF_DEVICE_NAME): str,
                        self.hass.data["voluptuous"].Optional(CONF_FS_NAME): str,
                        self.hass.data["voluptuous"].Optional(CONF_USE_FS_LOCK, default=False): bool,
                    }
                ),
            )

        # Validate the input
        device_name = user_input[CONF_DEVICE_NAME]
        fs_name = user_input.get(CONF_FS_NAME, "")
        use_fs_lock = user_input.get(CONF_USE_FS_LOCK, False)

        # Ensure unique device name
        await self.async_set_unique_id(device_name.lower())
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"PC {device_name}",
            data={
                CONF_DEVICE_NAME: device_name,
                CONF_FS_NAME: fs_name,
                CONF_USE_FS_LOCK: use_fs_lock,
            },
        )
