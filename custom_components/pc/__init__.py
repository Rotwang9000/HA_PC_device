import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.loader import async_get_integration
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["pc"]  # Use the custom pc platform instead of media_player

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the PC component."""
    hass.data.setdefault(DOMAIN, {})

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

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PC device from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Guard against duplicate concurrent setups for the same entry
    # Home Assistant may trigger async_setup_entry again while a previous
    # attempt is still running which would raise a ConfigEntryState error.
    if entry.entry_id in hass.data.get(DOMAIN, {}).get("pending_setups", []):
        _LOGGER.warning(
            "Entry %s is already in the process of being set up – skipping duplicate call",
            entry.entry_id,
        )
        return False
    
    # Mark entry as being set up
    if "pending_setups" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["pending_setups"] = []
    hass.data[DOMAIN]["pending_setups"].append(entry.entry_id)
    
    try:
        # Ensure the integration is loaded asynchronously
        integration = await async_get_integration(hass, DOMAIN)
        _LOGGER.debug(f"Integration {DOMAIN} loaded: {integration}")

        # Forward the setup to the pc platform
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        # Store entry data after successful setup
        hass.data[DOMAIN][entry.entry_id] = entry.data
        
        # Remove from pending setups
        hass.data[DOMAIN]["pending_setups"].remove(entry.entry_id)
        
        return True
    except Exception as e:
        _LOGGER.error(f"Failed to setup entry {entry.entry_id}: {str(e)}")
        _LOGGER.error(f"Current entry state: {entry.state}")
        _LOGGER.error("To fix this issue, please remove this integration through the UI and add it again.")
        
        # Remove from pending setups
        if "pending_setups" in hass.data[DOMAIN] and entry.entry_id in hass.data[DOMAIN]["pending_setups"]:
            hass.data[DOMAIN]["pending_setups"].remove(entry.entry_id)
        
        # Clear our data for this entry
        hass.data[DOMAIN].pop(entry.entry_id, None)
        return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug(f"Unloading entry {entry.entry_id}")
    try:
        # Remove from pending setups if it's there
        if "pending_setups" in hass.data[DOMAIN] and entry.entry_id in hass.data[DOMAIN]["pending_setups"]:
            hass.data[DOMAIN]["pending_setups"].remove(entry.entry_id)
            _LOGGER.debug(f"Removed {entry.entry_id} from pending setups")
            
        # Unload the platform
        unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        _LOGGER.debug(f"Platform unload result: {unloaded}")
        
        # Clean up data in hass.data
        if DOMAIN in hass.data:
            if entry.entry_id in hass.data[DOMAIN]:
                hass.data[DOMAIN].pop(entry.entry_id, None)
                _LOGGER.debug(f"Removed entry data for {entry.entry_id}")
            
            # Also clean up from entities dict if it exists
            if "entities" in hass.data[DOMAIN] and entry.entry_id in hass.data[DOMAIN]["entities"]:
                hass.data[DOMAIN]["entities"].pop(entry.entry_id, None)
                _LOGGER.debug(f"Removed entity for {entry.entry_id} from entities dict")
        
        return unloaded
    except Exception as e:
        _LOGGER.error(f"Error unloading entry {entry.entry_id}: {str(e)}")
        return False
