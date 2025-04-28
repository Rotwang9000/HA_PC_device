"""The Computer integration."""
import logging
import asyncio
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.loader import async_get_integration
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Use the computer platform (not media_player)
PLATFORMS = ["computer"] 

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
	"""Set up the Computer component."""
	hass.data.setdefault(DOMAIN, {})

	# Register custom services
	async def handle_turn_on(call):
		entity_id = call.data.get("entity_id")
		entity = hass.states.get(entity_id)
		if entity:
			await hass.services.async_call(
				"computer",
				"turn_on", 
				{"entity_id": entity_id},
				blocking=True
			)
		else:
			_LOGGER.error("Entity %s not found for turn_on service", entity_id)

	async def handle_turn_off(call):
		entity_id = call.data.get("entity_id")
		entity = hass.states.get(entity_id)
		if entity:
			await hass.services.async_call(
				"computer",
				"turn_off", 
				{"entity_id": entity_id},
				blocking=True
			)
		else:
			_LOGGER.error("Entity %s not found for turn_off service", entity_id)

	async def handle_set_volume_level(call):
		entity_id = call.data.get("entity_id")
		volume_level = call.data.get("volume_level")
		entity = hass.states.get(entity_id)
		if entity:
			await hass.services.async_call(
				"computer",
				"set_volume_level", 
				{"entity_id": entity_id, "volume_level": volume_level},
				blocking=True
			)
		else:
			_LOGGER.error("Entity %s not found for set_volume_level service", entity_id)

	async def handle_toggle_mute(call):
		entity_id = call.data.get("entity_id")
		entity = hass.states.get(entity_id)
		if entity:
			await hass.services.async_call(
				"computer",
				"toggle_mute", 
				{"entity_id": entity_id},
				blocking=True
			)
		else:
			_LOGGER.error("Entity %s not found for toggle_mute service", entity_id)

	async def handle_toggle_enforce_lock(call):
		entity_id = call.data.get("entity_id")
		entity = hass.states.get(entity_id)
		if entity:
			await hass.services.async_call(
				"computer",
				"toggle_enforce_lock", 
				{"entity_id": entity_id},
				blocking=True
			)
		else:
			_LOGGER.error("Entity %s not found for toggle_enforce_lock service", entity_id)

	# Register services
	hass.services.async_register(DOMAIN, "turn_on", handle_turn_on)
	hass.services.async_register(DOMAIN, "turn_off", handle_turn_off)
	hass.services.async_register(DOMAIN, "set_volume_level", handle_set_volume_level)
	hass.services.async_register(DOMAIN, "toggle_mute", handle_toggle_mute)
	hass.services.async_register(DOMAIN, "toggle_enforce_lock", handle_toggle_enforce_lock)

	return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
	"""Set up Computer from a config entry."""
	_LOGGER.debug("Setting up Computer config entry %s", entry.entry_id)
	
	# Initialize data structure
	hass.data.setdefault(DOMAIN, {})
	
	# Create/get setup lock
	if "setup_lock" not in hass.data[DOMAIN]:
		hass.data[DOMAIN]["setup_lock"] = asyncio.Lock()
	setup_lock = hass.data[DOMAIN]["setup_lock"]
	
	# Use lock to prevent concurrent setups
	async with setup_lock:
		try:
			# Forward the entry to the platform
			await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
			hass.data[DOMAIN][entry.entry_id] = entry.data
			_LOGGER.debug("Successfully set up Computer entry %s", entry.entry_id)
			return True
		except Exception as e:
			_LOGGER.error("Failed to set up Computer entry %s: %s", entry.entry_id, str(e))
			return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
	"""Unload a config entry."""
	_LOGGER.debug("Unloading Computer entry %s", entry.entry_id)
	
	# Use lock to prevent unloading while setting up
	if "setup_lock" in hass.data[DOMAIN]:
		setup_lock = hass.data[DOMAIN]["setup_lock"]
		async with setup_lock:
			# Unload platforms
			unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
			
			# Clean up data
			if unload_ok and entry.entry_id in hass.data[DOMAIN]:
				hass.data[DOMAIN].pop(entry.entry_id)
				
				# Clean up entity data if it exists
				if "entities" in hass.data[DOMAIN] and entry.entry_id in hass.data[DOMAIN]["entities"]:
					hass.data[DOMAIN]["entities"].pop(entry.entry_id)
					
			_LOGGER.debug("Unload success for Computer entry %s: %s", entry.entry_id, unload_ok)
			return unload_ok
	else:
		# If no lock exists, we can just unload directly
		unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
		if unload_ok and entry.entry_id in hass.data.get(DOMAIN, {}):
			hass.data[DOMAIN].pop(entry.entry_id)
		return unload_ok 