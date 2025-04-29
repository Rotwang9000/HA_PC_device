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
			# Get the actual entity from our storage
			stored_entities = hass.data.get(DOMAIN, {}).get("entities", {})
			
			# Find the corresponding entity
			for entry_id, entities in stored_entities.items():
				if isinstance(entities, dict) and "main" in entities and entities["main"].entity_id == entity_id:
					await entities["main"].async_turn_on()
					return
			
			# If not found in the new structure, try the old structure
			for entry_id, entity_obj in stored_entities.items():
				if not isinstance(entity_obj, dict) and entity_obj.entity_id == entity_id:
					await entity_obj.async_turn_on()
					return
			
			_LOGGER.error("Entity %s not found in computer entities", entity_id)
		else:
			_LOGGER.error("Entity %s not found for turn_on service", entity_id)

	async def handle_turn_off(call):
		entity_id = call.data.get("entity_id")
		entity = hass.states.get(entity_id)
		if entity:
			# Get the actual entity from our storage
			stored_entities = hass.data.get(DOMAIN, {}).get("entities", {})
			
			# Find the corresponding entity
			for entry_id, entities in stored_entities.items():
				if isinstance(entities, dict) and "main" in entities and entities["main"].entity_id == entity_id:
					await entities["main"].async_turn_off()
					return
			
			# If not found in the new structure, try the old structure
			for entry_id, entity_obj in stored_entities.items():
				if not isinstance(entity_obj, dict) and entity_obj.entity_id == entity_id:
					await entity_obj.async_turn_off()
					return
			
			_LOGGER.error("Entity %s not found in computer entities", entity_id)
		else:
			_LOGGER.error("Entity %s not found for turn_off service", entity_id)

	async def handle_set_volume_level(call):
		entity_id = call.data.get("entity_id")
		volume_level = call.data.get("volume_level")
		entity = hass.states.get(entity_id)
		if entity:
			# Get the actual entity from our storage
			stored_entities = hass.data.get(DOMAIN, {}).get("entities", {})
			
			# Find the corresponding entity
			for entry_id, entities in stored_entities.items():
				if isinstance(entities, dict) and "main" in entities:
					if entities["main"].entity_id == entity_id:
						await entities["main"].async_set_volume_level(volume_level)
						if "volume" in entities:
							await entities["volume"].async_update_state()
						return
					elif "volume" in entities and entities["volume"].entity_id == entity_id:
						await entities["volume"].async_set_native_value(volume_level)
						return
			
			# If not found in the new structure, try the old structure
			for entry_id, entity_obj in stored_entities.items():
				if not isinstance(entity_obj, dict) and entity_obj.entity_id == entity_id:
					await entity_obj.async_set_volume_level(volume_level)
					return
			
			_LOGGER.error("Entity %s not found in computer entities", entity_id)
		else:
			_LOGGER.error("Entity %s not found for set_volume_level service", entity_id)

	async def handle_toggle_mute(call):
		entity_id = call.data.get("entity_id")
		entity = hass.states.get(entity_id)
		if entity:
			# Get the actual entity from our storage
			stored_entities = hass.data.get(DOMAIN, {}).get("entities", {})
			
			# Find the corresponding entity
			for entry_id, entities in stored_entities.items():
				if isinstance(entities, dict) and "main" in entities:
					if entities["main"].entity_id == entity_id:
						await entities["main"].async_toggle_mute()
						if "mute" in entities:
							await entities["mute"].async_update_state()
						return
					elif "mute" in entities and entities["mute"].entity_id == entity_id:
						current_state = entities["mute"].is_on
						if current_state:
							await entities["mute"].async_turn_off()
						else:
							await entities["mute"].async_turn_on()
						return
			
			# If not found in the new structure, try the old structure
			for entry_id, entity_obj in stored_entities.items():
				if not isinstance(entity_obj, dict) and entity_obj.entity_id == entity_id:
					await entity_obj.async_toggle_mute()
					return
			
			_LOGGER.error("Entity %s not found in computer entities", entity_id)
		else:
			_LOGGER.error("Entity %s not found for toggle_mute service", entity_id)

	async def handle_toggle_enforce_lock(call):
		entity_id = call.data.get("entity_id")
		entity = hass.states.get(entity_id)
		if entity:
			# Get the actual entity from our storage
			stored_entities = hass.data.get(DOMAIN, {}).get("entities", {})
			
			# Find the corresponding entity
			for entry_id, entities in stored_entities.items():
				if isinstance(entities, dict) and "main" in entities:
					if entities["main"].entity_id == entity_id:
						await entities["main"].async_toggle_enforce_lock()
						if "enforce_lock" in entities:
							await entities["enforce_lock"].async_update_state()
						if "lock" in entities:
							await entities["lock"].async_update_state()
						return
					elif "lock" in entities and entities["lock"].entity_id == entity_id:
						await entities["lock"].async_press()
						if "enforce_lock" in entities:
							await entities["enforce_lock"].async_update_state()
						return
					elif "enforce_lock" in entities and entities["enforce_lock"].entity_id == entity_id:
						current_state = entities["enforce_lock"].is_on
						if current_state:
							await entities["enforce_lock"].async_turn_off()
						else:
							await entities["enforce_lock"].async_turn_on()
						return
			
			# If not found in the new structure, try the old structure
			for entry_id, entity_obj in stored_entities.items():
				if not isinstance(entity_obj, dict) and entity_obj.entity_id == entity_id:
					await entity_obj.async_toggle_enforce_lock()
					return
			
			_LOGGER.error("Entity %s not found in computer entities", entity_id)
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
	SETUP_IN_PROGRESS state conflicts and ensures unique IDs for entities.
	"""
	_LOGGER.debug("Setting up Computer entry %s using custom approach", entry.entry_id)
	
	# Initialize data structure
	hass.data.setdefault(DOMAIN, {})
	
	# First check if we've already set this up to avoid any duplicates
	if entry.entry_id in hass.data[DOMAIN] and entry.entry_id != "setup_lock":
		_LOGGER.warning("Entry %s already set up, not proceeding with duplicate setup", entry.entry_id)
		return True
	
	# Check if the entry is already in LOADED state to avoid OperationNotAllowed error
	if entry.state is ConfigEntryState.LOADED:
		_LOGGER.warning("Entry %s is already in LOADED state, returning success without setup", entry.entry_id)
		return True
	
	# Register our domains
	hass.data.setdefault(DOMAIN, {})
	if entry.entry_id not in hass.data[DOMAIN]:
		hass.data[DOMAIN][entry.entry_id] = {}
	
	# Copy entry data into the dict
	for key, value in entry.data.items():
		hass.data[DOMAIN][entry.entry_id][key] = value
	
	# Forward setup to computer platform
	from .computer import async_setup_entry as setup_computer_platform
	await setup_computer_platform(hass, entry, async_add_entities=None)
	
	# Now set up all the required domains for sub-entities
	# These will create the correct platform entities
	from homeassistant.helpers.entity_platform import async_get_platforms
	from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
	from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN  
	from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
	
	_LOGGER.debug("Setting up platform entities for entry %s", entry.entry_id)
	
	# Manually set up the required platforms to ensure sub-entities are registered
	from homeassistant.setup import async_setup_component
	
	# First make sure all required components are set up
	if not hass.data.get(NUMBER_DOMAIN):
		_LOGGER.debug("Setting up number component")
		await async_setup_component(hass, NUMBER_DOMAIN, {})
	if not hass.data.get(SWITCH_DOMAIN):
		_LOGGER.debug("Setting up switch component")
		await async_setup_component(hass, SWITCH_DOMAIN, {})
	if not hass.data.get(BUTTON_DOMAIN):
		_LOGGER.debug("Setting up button component")
		await async_setup_component(hass, BUTTON_DOMAIN, {})
	
	# Register our sub-entities with Home Assistant
	# This is done by calling specific helper functions from computer.py
	from .computer import register_sub_entities
	_LOGGER.debug("Registering sub-entities for entry %s", entry.entry_id)
	try:
		success = await register_sub_entities(hass, entry)
		if success:
			_LOGGER.debug("Successfully registered all sub-entities for entry %s", entry.entry_id)
		else:
			_LOGGER.warning("Some sub-entities may not have been registered for entry %s", entry.entry_id)
	except Exception as e:
		_LOGGER.error("Error registering sub-entities: %s", e)
	
	_LOGGER.debug("Successfully completed setup for Computer entry %s", entry.entry_id)
	return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
	"""Unload a config entry more directly, matching our setup pattern."""
	_LOGGER.debug("Unloading Computer entry %s", entry.entry_id)
	
	# No need to try unloading through Home Assistant's system - we never registered
	# our platforms with it. We just need to clean up our own data.
	unload_ok = True
	
	# Clean up data regardless of unload success
	if entry.entry_id in hass.data.get(DOMAIN, {}):
		hass.data[DOMAIN].pop(entry.entry_id)
		_LOGGER.debug("Removed data for entry %s", entry.entry_id)
	
	# Clean up entity data if it exists
	if "entities" in hass.data.get(DOMAIN, {}):
		if entry.entry_id in hass.data[DOMAIN]["entities"]:
			if isinstance(hass.data[DOMAIN]["entities"][entry.entry_id], dict):
				# New structure with multiple entities
				hass.data[DOMAIN]["entities"].pop(entry.entry_id)
				_LOGGER.debug("Removed entities for entry %s (multi-entity structure)", entry.entry_id)
			else:
				# Old structure with single entity
				hass.data[DOMAIN]["entities"].pop(entry.entry_id)
				_LOGGER.debug("Removed entity for entry %s (single entity structure)", entry.entry_id)
	
	return unload_ok 