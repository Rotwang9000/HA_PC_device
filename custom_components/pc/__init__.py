import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.loader import async_get_integration
from .const import DOMAIN
import asyncio

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
    
    # Use a global lock to ensure only one setup runs at a time for this integration
    # This prevents any concurrent setup issues regardless of HA's internal state
    if "setup_lock" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["setup_lock"] = asyncio.Lock()
    
    setup_lock = hass.data[DOMAIN]["setup_lock"]
    if setup_lock.locked():
        _LOGGER.warning("Setup lock is held; another setup is in progress. Queuing setup for entry %s", entry.entry_id)
    
    async with setup_lock:
        _LOGGER.debug("Acquired setup lock for entry %s", entry.entry_id)
        # Double-check if this entry was already set up while we waited
        if entry.entry_id in hass.data[DOMAIN] and entry.entry_id != "setup_lock":
            _LOGGER.warning("Entry %s was set up while waiting for lock; skipping duplicate setup", entry.entry_id)
            return False

    try:
        # Ensure the integration is loaded asynchronously
        integration = await async_get_integration(hass, DOMAIN)
        _LOGGER.debug(f"Integration {DOMAIN} loaded: {integration}")

        # Forward the setup to the pc platform
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        # Store entry data after successful setup
        hass.data[DOMAIN][entry.entry_id] = entry.data
        
        return True
    except Exception as e:
        _LOGGER.error(f"Failed to setup entry {entry.entry_id}: {str(e)}")
        _LOGGER.error(f"Current entry state: {entry.state}")
        _LOGGER.error("To fix this issue, please remove this integration through the UI and add it again.")
        
        # Clear our data for this entry
        hass.data[DOMAIN].pop(entry.entry_id, None)
        return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug(f"Unloading entry {entry.entry_id}")
    try:
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
