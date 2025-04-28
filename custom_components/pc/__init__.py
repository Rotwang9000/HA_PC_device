import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.loader import async_get_integration
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["pc"]  # Use the custom 'pc' domain as a platform

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the PC component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PC device from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Ensure the integration is loaded asynchronously
    integration = await async_get_integration(hass, DOMAIN)
    _LOGGER.debug(f"Integration {DOMAIN} loaded: {integration}")

    # Forward the setup to the pc platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register custom services
    async def handle_turn_on(call):
        entity_id = call.data.get("entity_id")
        entity = hass.states.get(entity_id)
        if entity:
            await entity.async_turn_on()
        else:
            _LOGGER.error(f"Entity {entity_id} not found for turn_on service")

    async def handle_turn_off(call):
        entity_id = call.data.get("entity_id")
        entity = hass.states.get(entity_id)
        if entity:
            await entity.async_turn_off()
        else:
            _LOGGER.error(f"Entity {entity_id} not found for turn_off service")

    async def handle_set_volume_level(call):
        entity_id = call.data.get("entity_id")
        volume_level = call.data.get("volume_level")
        entity = hass.states.get(entity_id)
        if entity:
            await entity.async_set_volume_level(volume_level)
        else:
            _LOGGER.error(f"Entity {entity_id} not found for set_volume_level service")

    async def handle_toggle_mute(call):
        entity_id = call.data.get("entity_id")
        entity = hass.states.get(entity_id)
        if entity:
            await entity.async_toggle_mute()
        else:
            _LOGGER.error(f"Entity {entity_id} not found for toggle_mute service")

    async def handle_toggle_enforce_lock(call):
        entity_id = call.data.get("entity_id")
        entity = hass.states.get(entity_id)
        if entity:
            await entity.async_toggle_enforce_lock()
        else:
            _LOGGER.error(f"Entity {entity_id} not found for toggle_enforce_lock service")

    hass.services.async_register(DOMAIN, "turn_on", handle_turn_on)
    hass.services.async_register(DOMAIN, "turn_off", handle_turn_off)
    hass.services.async_register(DOMAIN, "set_volume_level", handle_set_volume_level)
    hass.services.async_register(DOMAIN, "toggle_mute", handle_toggle_mute)
    hass.services.async_register(DOMAIN, "toggle_enforce_lock", handle_toggle_enforce_lock)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    await hass.config_entries
