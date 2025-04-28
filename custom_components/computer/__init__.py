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
	SETUP_IN_PROGRESS state conflicts.
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
	
	# Register our platform manually rather than using async_forward_entry_setups
	# Use the dedicated setup function for the computer platform
	from .computer import async_setup_entry as setup_computer
	
	try:
		# Import EntityComponent to properly register entities
		from homeassistant.helpers.entity_component import EntityComponent
		
		# Create a simple entity component for our domain
		component = EntityComponent(_LOGGER, DOMAIN, hass)
		
		# Create the entity directly
		from .computer import ComputerDevice, ComputerVolumeEntity, ComputerMuteEntity, ComputerLockButton, ComputerEnforceLockSwitch
		entity = ComputerDevice(hass, entry.entry_id, entry.data)
		volume_entity = ComputerVolumeEntity(hass, entry.entry_id, entry.data, entity)
		mute_entity = ComputerMuteEntity(hass, entry.entry_id, entry.data, entity)
		lock_button = ComputerLockButton(hass, entry.entry_id, entry.data, entity)
		enforce_lock_entity = ComputerEnforceLockSwitch(hass, entry.entry_id, entry.data, entity)
		
		# Add entity to Home Assistant through the component
		await component.async_add_entities([entity, volume_entity, mute_entity, lock_button, enforce_lock_entity])
		
		# Store the entity for MQTT control
		hass.data.setdefault(DOMAIN, {})
		if "entities" not in hass.data[DOMAIN]:
			hass.data[DOMAIN]["entities"] = {}
		hass.data[DOMAIN]["entities"][entry.entry_id] = {
			"main": entity,
			"volume": volume_entity, 
			"mute": mute_entity,
			"lock": lock_button,
			"enforce_lock": enforce_lock_entity
		}

		# Create the dict for entry.entry_id if it doesn't exist
		if entry.entry_id not in hass.data[DOMAIN]:
			hass.data[DOMAIN][entry.entry_id] = {}
		# Copy entry data into the dict
		for key, value in entry.data.items():
			hass.data[DOMAIN][entry.entry_id][key] = value
		
		# Set up MQTT subscriptions
		device_name = entry.data["device_name"]
		from .computer import MQTT_BASE_TOPIC
		
		# Define MQTT topics
		set_topic = f"{MQTT_BASE_TOPIC}/Computer.{device_name}/set"
		lock_topic = f"{MQTT_BASE_TOPIC}/Computer.{device_name}/lock"
		mute_topic = f"{MQTT_BASE_TOPIC}/Computer.{device_name}/mute"
		setvolume_topic = f"{MQTT_BASE_TOPIC}/Computer.{device_name}/setvolume"
		
		# Handle MQTT messages
		async def message_received(msg):
			try:
				payload = msg.payload.decode("utf-8") if isinstance(msg.payload, bytes) else str(msg.payload)
				if msg.topic == set_topic:
					if payload.upper() == "ON":
						await entity.async_turn_on()
					elif payload.upper() == "OFF":
						await entity.async_turn_off()
				elif msg.topic == lock_topic:
					await entity.async_toggle_enforce_lock()
					await enforce_lock_entity.async_update_state()
				elif msg.topic == mute_topic:
					await entity.async_toggle_mute()
					await mute_entity.async_update_state()
				elif msg.topic == setvolume_topic:
					try:
						volume = float(payload)
						await entity.async_set_volume_level(volume)
						await volume_entity.async_update_state()
					except ValueError:
						pass
			except Exception as e:
				_LOGGER.error("Error handling MQTT message: %s", e)
		
		# Subscribe to MQTT topics
		from homeassistant.components import mqtt
		unsubscribes = []
		for topic in [set_topic, lock_topic, mute_topic, setvolume_topic]:
			unsub = await mqtt.async_subscribe(hass, topic, message_received)
			unsubscribes.append(unsub)
		
		# Store unsubscribe callbacks
		hass.data[DOMAIN][entry.entry_id]["unsubscribes"] = unsubscribes
		
		_LOGGER.debug("Successfully initiated direct setup for Computer entry %s", entry.entry_id)
	except Exception as e:
		_LOGGER.error("Error setting up Computer entry %s: %s", entry.entry_id, str(e))
		return False
	
	# Return success immediately, the platform setup runs in background
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