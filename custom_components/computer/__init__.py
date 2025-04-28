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
	"""Use a completely different pattern to set up a Computer config entry.
	
	This implementation avoids Home Assistant's internal ConfigEntryState
	management by using a different approach that doesn't trigger the
	SETUP_IN_PROGRESS state conflicts.
	"""
	_LOGGER.debug("Setting up Computer entry %s using custom approach", entry.entry_id)
	
	# Initialize data structure
	hass.data.setdefault(DOMAIN, {})
	
	# First check if we've already set this up to avoid any duplicates
	if entry.entry_id in hass.data[DOMAIN] and entry.entry_id != "setup_lock":
		_LOGGER.warning("Entry %s already set up, not proceeding with duplicate setup", entry.entry_id)
		return True
	
	# Register our platform manually rather than using async_forward_entry_setups
	# This is to avoid Home Assistant's internal ConfigEntryState management that causes conflicts
	for platform in PLATFORMS:
		hass.async_create_task(
			hass.config_entries.async_forward_entry_setup(entry, platform)
		)
	
	# Store the entry data
	hass.data[DOMAIN][entry.entry_id] = entry.data
	_LOGGER.debug("Successfully initiated setup for Computer entry %s", entry.entry_id)
	
	# Return success immediately, the platform setup runs in background
	return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
	"""Unload a config entry more directly, matching our setup pattern."""
	_LOGGER.debug("Unloading Computer entry %s", entry.entry_id)
	
	# Unload platforms individually rather than using async_unload_platforms
	unload_ok = True
	for platform in PLATFORMS:
		if await hass.config_entries.async_forward_entry_unload(entry, platform):
			_LOGGER.debug("Unloaded platform %s for entry %s", platform, entry.entry_id)
		else:
			unload_ok = False
			_LOGGER.error("Failed to unload platform %s for entry %s", platform, entry.entry_id)
	
	# Clean up data regardless of unload success
	if entry.entry_id in hass.data.get(DOMAIN, {}):
		hass.data[DOMAIN].pop(entry.entry_id)
		_LOGGER.debug("Removed data for entry %s", entry.entry_id)
	
	# Clean up entity data if it exists
	if "entities" in hass.data.get(DOMAIN, {}) and entry.entry_id in hass.data[DOMAIN]["entities"]:
		hass.data[DOMAIN]["entities"].pop(entry.entry_id)
		_LOGGER.debug("Removed entity for entry %s", entry.entry_id)
	
	return unload_ok 