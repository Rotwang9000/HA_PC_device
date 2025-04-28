import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
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
    
    # Check if Home Assistant has already marked this entry as being in setup progress
    # This can happen if HA's internal state was set before our guard check.
    if entry.state is ConfigEntryState.SETUP_IN_PROGRESS:
        _LOGGER.warning("Entry %s is already marked as SETUP_IN_PROGRESS by Home Assistant; aborting duplicate call", entry.entry_id)
        return False

    # Ensure we have a set tracking pending setups – doing this *before* the guard
    pending: set[str] = hass.data[DOMAIN].setdefault("pending_setups", set())

    # Guard against a concurrent setup already in progress for this entry.
    if entry.entry_id in pending:
        _LOGGER.warning("Entry %s is already mid-setup; aborting duplicate call", entry.entry_id)
        return False

    # Mark entry as being set up now
    pending.add(entry.entry_id)
    
    try:
        # Ensure the integration is loaded asynchronously
        integration = await async_get_integration(hass, DOMAIN)
        _LOGGER.debug(f"Integration {DOMAIN} loaded: {integration}")

        # Forward the setup to the pc platform
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        # Store entry data after successful setup
        hass.data[DOMAIN][entry.entry_id] = entry.data
        
        # Remove from pending setups
        pending.remove(entry.entry_id)
        
        return True
    except Exception as e:
        _LOGGER.error(f"Failed to setup entry {entry.entry_id}: {str(e)}")
        _LOGGER.error(f"Current entry state: {entry.state}")
        _LOGGER.error("To fix this issue, please remove this integration through the UI and add it again.")
        
        # Remove from pending setups if there
        if "pending_setups" in hass.data[DOMAIN]:
            pending = hass.data[DOMAIN]["pending_setups"]
            if entry.entry_id in pending:
                pending.remove(entry.entry_id)
                _LOGGER.debug("Removed %s from pending setups after error", entry.entry_id)
        
        # Clear our data for this entry
        hass.data[DOMAIN].pop(entry.entry_id, None)
        return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug(f"Unloading entry {entry.entry_id}")
    try:
        # Remove from pending setups if it's there
        if "pending_setups" in hass.data[DOMAIN]:
            pending = hass.data[DOMAIN]["pending_setups"]
            if entry.entry_id in pending:
                pending.remove(entry.entry_id)
                _LOGGER.debug("Removed %s from pending setups", entry.entry_id)
            
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
