import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from .const import DOMAIN, SERVICE_SET_VOLUME, SERVICE_MUTE, SERVICE_LOCK, SERVICE_ENFORCE_LOCK

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SWITCH]

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the PC component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PC device from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Forward the setup to the switch platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register custom services
    async def handle_set_volume(call):
        entity_id = call.data.get("entity_id")
        volume_level = call.data.get("volume_level")
        entity = hass.states.get(entity_id)
        if entity:
            await entity.async_set_volume(volume_level)

    async def handle_mute(call):
        entity_id = call.data.get("entity_id")
        entity = hass.states.get(entity_id)
        if entity:
            await entity.async_mute()

    async def handle_lock(call):
        entity_id = call.data.get("entity_id")
        entity = hass.states.get(entity_id)
        if entity:
            await entity.async_lock()

    async def handle_enforce_lock(call):
        entity_id = call.data.get("entity_id")
        enabled = call.data.get("enabled", False)
        entity = hass.states.get(entity_id)
        if entity:
            entity.set_enforce_lock(enabled)

    hass.services.async_register(DOMAIN, SERVICE_SET_VOLUME, handle_set_volume)
    hass.services.async_register(DOMAIN, SERVICE_MUTE, handle_mute)
    hass.services.async_register(DOMAIN, SERVICE_LOCK, handle_lock)
    hass.services.async_register(DOMAIN, SERVICE_ENFORCE_LOCK, handle_enforce_lock)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data[DOMAIN].pop(entry.entry_id)
    return True
