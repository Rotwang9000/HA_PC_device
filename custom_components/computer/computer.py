"""Platform for Computer integration."""
import logging
import json
import asyncio
from homeassistant.helpers.entity import Entity
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.components import mqtt
from homeassistant.exceptions import HomeAssistantError
from homeassistant.components.number import NumberEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.button import ButtonEntity
from .const import (
	DOMAIN,
	CONF_DEVICE_NAME,
	CONF_POWER_ON_ACTION, CONF_POWER_OFF_ACTION,
	POWER_ON_POWER, POWER_ON_WAKE,
	POWER_OFF_POWER, POWER_OFF_HIBERNATE, POWER_OFF_SLEEP,
	ATTR_VOLUME_LEVEL, ATTR_ACTIVE_WINDOW, ATTR_SESSION_STATE
)

_LOGGER = logging.getLogger(__name__)

# Constants for MQTT topics
MQTT_BASE_TOPIC = "homeassistant/Computer"

async def async_setup_entry(hass, config_entry, async_add_entities):
	"""Set up the Computer device from a config entry."""
	_LOGGER.debug("Starting setup for config entry: %s", config_entry.entry_id)
	
	device_name = config_entry.data[CONF_DEVICE_NAME]
	_LOGGER.debug("Device name: %s", device_name)
	
	try:
		# Create main entity
		entity = ComputerDevice(hass, config_entry.entry_id, config_entry.data)

		# Create additional entities
		volume_entity = ComputerVolumeEntity(hass, config_entry.entry_id, config_entry.data, entity)
		mute_entity = ComputerMuteEntity(hass, config_entry.entry_id, config_entry.data, entity)
		lock_button = ComputerLockButton(hass, config_entry.entry_id, config_entry.data, entity)
		enforce_lock_entity = ComputerEnforceLockSwitch(hass, config_entry.entry_id, config_entry.data, entity)
		
		# Store entity for later access (before registration)
		hass.data.setdefault(DOMAIN, {})
		if "entities" not in hass.data[DOMAIN]:
			hass.data[DOMAIN]["entities"] = {}
		hass.data[DOMAIN]["entities"][config_entry.entry_id] = {
			"main": entity,
			"volume": volume_entity,
			"mute": mute_entity,
			"lock": lock_button,
			"enforce_lock": enforce_lock_entity
		}
		
		# If async_add_entities is None, we need to register using entity component
		if async_add_entities is None:
			_LOGGER.debug("Using EntityComponent for entity registration as async_add_entities is None")
			from homeassistant.helpers.entity_component import EntityComponent
			component = EntityComponent(_LOGGER, DOMAIN, hass)
			await component.async_add_entities([entity])
			
			# Register sub-entities with their respective domains
			from homeassistant.helpers.entity_component import EntityComponent
			volume_component = EntityComponent(_LOGGER, "number", hass)
			mute_component = EntityComponent(_LOGGER, "switch", hass)
			lock_component = EntityComponent(_LOGGER, "button", hass)
			enforce_lock_component = EntityComponent(_LOGGER, "switch", hass)
			
			await volume_component.async_add_entities([volume_entity])
			await mute_component.async_add_entities([mute_entity])
			await lock_component.async_add_entities([lock_button])
			await enforce_lock_component.async_add_entities([enforce_lock_entity])
		else:
			_LOGGER.debug("Using standard async_add_entities for entity registration")
			# Standard setup flow
			async_add_entities([entity, volume_entity, mute_entity, lock_button, enforce_lock_entity])
		
		_LOGGER.debug("Added entities for Computer %s to Home Assistant", device_name)
	except Exception as e:
		_LOGGER.error("Failed to create Computer entities: %s", e)
		raise

	# Register device in registry
	device_registry = dr.async_get(hass)
	device_registry.async_get_or_create(
		config_entry_id=config_entry.entry_id,
		identifiers={(DOMAIN, device_name.lower())},
		name=f"Computer {device_name}",
		manufacturer="Home Assistant",
		model="Computer"
	)

	# Verify MQTT is available
	if not await mqtt.async_wait_for_mqtt_client(hass):
		_LOGGER.error("MQTT integration is not available or broker is not connected")
		raise HomeAssistantError("MQTT integration is not available")

	# Define MQTT topics
	set_topic = f"{MQTT_BASE_TOPIC}/Computer.{device_name}/set"
	lock_topic = f"{MQTT_BASE_TOPIC}/Computer.{device_name}/lock"
	mute_topic = f"{MQTT_BASE_TOPIC}/Computer.{device_name}/mute"
	setvolume_topic = f"{MQTT_BASE_TOPIC}/Computer.{device_name}/setvolume"

	# Define MQTT message handler
	async def message_received(msg):
		"""Handle incoming MQTT messages."""
		try:
			payload = msg.payload.decode("utf-8") if isinstance(msg.payload, bytes) else str(msg.payload)
			_LOGGER.debug("Received MQTT message on %s: %s", msg.topic, payload)
		except (AttributeError, UnicodeDecodeError) as e:
			_LOGGER.error("Failed to decode MQTT payload for %s: %s", msg.topic, e)
			return

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
			except ValueError as e:
				_LOGGER.error("Invalid volume value received: %s, error: %s", payload, e)

	# Subscribe to MQTT topics with timeout
	try:
		unsubscribe_set = await asyncio.wait_for(
			mqtt.async_subscribe(hass, set_topic, message_received),
			timeout=10
		)
		unsubscribe_lock = await asyncio.wait_for(
			mqtt.async_subscribe(hass, lock_topic, message_received),
			timeout=10
		)
		unsubscribe_mute = await asyncio.wait_for(
			mqtt.async_subscribe(hass, mute_topic, message_received),
			timeout=10
		)
		unsubscribe_setvolume = await asyncio.wait_for(
			mqtt.async_subscribe(hass, setvolume_topic, message_received),
			timeout=10
		)
		_LOGGER.debug("Subscribed to MQTT topics: %s, %s, %s, %s", 
			set_topic, lock_topic, mute_topic, setvolume_topic)
	except asyncio.TimeoutError as e:
		_LOGGER.error("Timeout while subscribing to MQTT topics: %s", e)
		raise HomeAssistantError("Failed to subscribe to MQTT topics due to timeout")

	# Store unsubscribe callbacks
	hass.data.setdefault(DOMAIN, {})
	if config_entry.entry_id not in hass.data[DOMAIN]:
		hass.data[DOMAIN][config_entry.entry_id] = {}
	
	hass.data[DOMAIN][config_entry.entry_id]["unsubscribes"] = [
		unsubscribe_set,
		unsubscribe_lock,
		unsubscribe_mute,
		unsubscribe_setvolume
	]
	
	_LOGGER.debug("Finished setup for config entry: %s", config_entry.entry_id)
	return True

class ComputerDevice(Entity):
	"""Representation of a Computer device."""

	def __init__(self, hass, entry_id, config):
		"""Initialize the Computer device."""
		self.hass = hass
		self._entry_id = entry_id
		self._device_name = config[CONF_DEVICE_NAME]
		self._power_on_action = config[CONF_POWER_ON_ACTION]
		self._power_off_action = config[CONF_POWER_OFF_ACTION]
		self._enforce_lock = False
		self._muted = False
		self._volume_level = 0.5
		self._attr_unique_id = f"computer_{self._device_name.lower()}_{entry_id}"
		self._attr_name = f"Computer {self._device_name}"
		self._attr_entity_category = None  # Primary entity, not a configuration entity
		self._state = STATE_ON
		self._attributes = {
			ATTR_VOLUME_LEVEL: self._volume_level,
			ATTR_ACTIVE_WINDOW: "Desktop",
			ATTR_SESSION_STATE: "unlocked",
			"enforce_lock": self._enforce_lock,
			"muted": self._muted
		}
		self._attr_device_info = {
			"identifiers": {(DOMAIN, self._device_name.lower())},
			"name": f"Computer {self._device_name}",
			"manufacturer": "Home Assistant",
			"model": "Computer"
		}
		# Make sure the entity_id follows the format domain.object_id
		self.entity_id = f"computer.{self._device_name.lower()}"

	async def async_added_to_hass(self):
		"""Run when entity is added to Home Assistant."""
		await super().async_added_to_hass()
		self._setup_state_tracking()
		_LOGGER.debug("State tracking set up for entity %s", self.entity_id)

	def _setup_state_tracking(self):
		"""Set up tracking for session state changes."""
		async_track_state_change_event(
			self.hass,
			[self.entity_id],
			self._handle_state_change
		)

	async def _handle_state_change(self, event):
		"""Handle state changes to enforce lock."""
		new_state = event.data.get("new_state")
		if new_state is None:
			return

		# Check if session state changed to unlocked while enforce_lock is active
		session_state = new_state.attributes.get(ATTR_SESSION_STATE, "unlocked")
		if self._enforce_lock and session_state == "unlocked":
			_LOGGER.info("Enforced lock active: Re-locking Computer %s", self._device_name)
			self._attributes[ATTR_SESSION_STATE] = "locked"
			await self._publish_state()
			self.async_write_ha_state()

	@property
	def state(self):
		"""Return the state of the Computer."""
		return self._state

	@property
	def extra_state_attributes(self):
		"""Return device specific state attributes."""
		self._attributes["enforce_lock"] = self._enforce_lock
		self._attributes["muted"] = self._muted
		self._attributes[ATTR_VOLUME_LEVEL] = self._volume_level
		return self._attributes

	async def async_turn_on(self, **kwargs):
		"""Turn the Computer on based on configured action."""
		if self._power_on_action == POWER_ON_POWER:
			_LOGGER.info("Powering on Computer %s", self._device_name)
			self._state = STATE_ON
			self._attributes[ATTR_SESSION_STATE] = "unlocked"
		elif self._power_on_action == POWER_ON_WAKE:
			_LOGGER.info("Sending wake command to Computer %s", self._device_name)
			self._state = STATE_ON
			self._attributes[ATTR_SESSION_STATE] = "unlocked"

		# Enforce lock if active
		if self._enforce_lock:
			_LOGGER.info("Enforced lock active: Locking Computer %s after turn on", self._device_name)
			self._attributes[ATTR_SESSION_STATE] = "locked"

		await self._publish_state()
		self.async_write_ha_state()

	async def async_turn_off(self, **kwargs):
		"""Turn the Computer off based on configured action."""
		if self._power_off_action == POWER_OFF_POWER:
			_LOGGER.info("Powering off Computer %s", self._device_name)
			self._state = STATE_OFF
			self._attributes[ATTR_SESSION_STATE] = "locked"
		elif self._power_off_action == POWER_OFF_HIBERNATE:
			_LOGGER.info("Hibernating Computer %s", self._device_name)
			self._state = STATE_OFF
			self._attributes[ATTR_SESSION_STATE] = "locked"
		elif self._power_off_action == POWER_OFF_SLEEP:
			_LOGGER.info("Sleeping Computer %s", self._device_name)
			self._state = STATE_OFF
			self._attributes[ATTR_SESSION_STATE] = "locked"

		await self._publish_state()
		self.async_write_ha_state()

	async def async_set_volume_level(self, volume):
		"""Set the volume level of the Computer."""
		self._volume_level = float(volume)
		self._attributes[ATTR_VOLUME_LEVEL] = self._volume_level
		await self._publish_state()
		self.async_write_ha_state()

	async def async_mute(self, mute):
		"""Mute or unmute the Computer."""
		self._muted = mute
		self._attributes["muted"] = self._muted
		_LOGGER.info("%s Computer %s", "Muting" if mute else "Unmuting", self._device_name)
		await self._publish_state()
		self.async_write_ha_state()

	async def async_toggle_mute(self):
		"""Toggle mute state."""
		await self.async_mute(not self._muted)

	async def async_toggle_enforce_lock(self):
		"""Toggle the enforced lock state."""
		self._enforce_lock = not self._enforce_lock
		self._attributes["enforce_lock"] = self._enforce_lock
		_LOGGER.info("Enforced lock for Computer %s set to %s", self._device_name, self._enforce_lock)
		if self._enforce_lock and self._attributes[ATTR_SESSION_STATE] == "unlocked":
			self._attributes[ATTR_SESSION_STATE] = "locked"
		await self._publish_state()
		self.async_write_ha_state()

	async def _publish_state(self):
		"""Publish the current state to the MQTT update topic."""
		state = self._state
		payload = {
			"entity_id": f"Computer.{self._device_name}",
			"state": state,
			ATTR_VOLUME_LEVEL: self._attributes[ATTR_VOLUME_LEVEL],
			ATTR_ACTIVE_WINDOW: self._attributes[ATTR_ACTIVE_WINDOW],
			ATTR_SESSION_STATE: self._attributes[ATTR_SESSION_STATE]
		}
		topic = f"{MQTT_BASE_TOPIC}/Computer.{self._device_name}/update"
		try:
			payload_str = json.dumps(payload)
			await mqtt.async_publish(self.hass, topic, payload_str)
		except (TypeError, ValueError) as e:
			_LOGGER.error("Failed to serialize state to JSON for %s: %s", topic, e)

class ComputerVolumeEntity(NumberEntity):
	"""Volume control entity for Computer."""
	
	def __init__(self, hass, entry_id, config, parent_entity):
		"""Initialize volume entity."""
		self.hass = hass
		self._entry_id = entry_id
		self._device_name = config[CONF_DEVICE_NAME]
		self.parent = parent_entity
		self._attr_unique_id = f"computer_{self._device_name.lower()}_volume_{entry_id}"
		self._attr_name = f"{self.parent._attr_name} Volume"
		self._attr_native_min_value = 0.0
		self._attr_native_max_value = 1.0
		self._attr_native_step = 0.01
		self._attr_device_info = self.parent._attr_device_info
		self._attr_icon = "mdi:volume-high"
		self._attr_device_class = "volume"  # Custom device class for volume
		self._attr_entity_category = None  # This is a primary control, not configuration
		
		# Explicitly set the entity_id with the correct domain (number)
		# Format: domain.object_id
		# For sub-entities, they should use their specific domain (like number, not computer)
		self.entity_id = f"number.{self._device_name.lower()}_volume"
		
	@property
	def native_value(self):
		"""Return current volume level."""
		return self.parent._volume_level
		
	async def async_set_native_value(self, value):
		"""Set new volume level."""
		await self.parent.async_set_volume_level(value)
		
	async def async_update_state(self):
		"""Update the entity state."""
		self.async_write_ha_state()

class ComputerMuteEntity(SwitchEntity):
	"""Mute control entity for Computer."""
	
	def __init__(self, hass, entry_id, config, parent_entity):
		"""Initialize mute entity."""
		self.hass = hass
		self._entry_id = entry_id
		self._device_name = config[CONF_DEVICE_NAME]
		self.parent = parent_entity
		self._attr_unique_id = f"computer_{self._device_name.lower()}_mute_{entry_id}"
		self._attr_name = f"{self.parent._attr_name} Mute"
		self._attr_device_info = self.parent._attr_device_info
		self._attr_icon = "mdi:volume-mute"
		self._attr_device_class = "switch"
		self._attr_entity_category = None  # This is a primary control, not configuration
		
		# Explicitly set the entity_id with the correct domain (switch)
		self.entity_id = f"switch.{self._device_name.lower()}_mute"
		
	@property
	def is_on(self):
		"""Return true if muted."""
		return self.parent._muted
		
	async def async_turn_on(self, **kwargs):
		"""Turn on mute."""
		await self.parent.async_mute(True)
		
	async def async_turn_off(self, **kwargs):
		"""Turn off mute."""
		await self.parent.async_mute(False)
		
	async def async_update_state(self):
		"""Update the entity state."""
		self.async_write_ha_state()

class ComputerLockButton(ButtonEntity):
	"""Lock control button for Computer."""
	
	def __init__(self, hass, entry_id, config, parent_entity):
		"""Initialize lock button entity."""
		self.hass = hass
		self._entry_id = entry_id
		self._device_name = config[CONF_DEVICE_NAME]
		self.parent = parent_entity
		self._attr_unique_id = f"computer_{self._device_name.lower()}_lock_{entry_id}"
		self._attr_name = f"{self.parent._attr_name} Lock"
		self._attr_device_info = self.parent._attr_device_info
		self._attr_icon = "mdi:lock"
		self._attr_device_class = "lock"
		self._attr_entity_category = None  # This is a primary control, not configuration
		
		# Explicitly set the entity_id with the correct domain (button)
		self.entity_id = f"button.{self._device_name.lower()}_lock"
		
	async def async_press(self):
		"""Handle button press."""
		await self.parent.async_toggle_enforce_lock()
		
	async def async_update_state(self):
		"""Update the entity state."""
		self.async_write_ha_state()

class ComputerEnforceLockSwitch(SwitchEntity):
	"""Enforce Lock control switch for Computer."""
	
	def __init__(self, hass, entry_id, config, parent_entity):
		"""Initialize enforce lock switch entity."""
		self.hass = hass
		self._entry_id = entry_id
		self._device_name = config[CONF_DEVICE_NAME]
		self.parent = parent_entity
		self._attr_unique_id = f"computer_{self._device_name.lower()}_enforce_lock_{entry_id}"
		self._attr_name = f"{self.parent._attr_name} Enforce Lock"
		self._attr_device_info = self.parent._attr_device_info
		self._attr_icon = "mdi:lock-check"
		self._attr_device_class = "switch"
		self._attr_entity_category = None  # This is a primary control, not configuration
		
		# Explicitly set the entity_id with the correct domain (switch)
		self.entity_id = f"switch.{self._device_name.lower()}_enforce_lock"
		
	@property
	def is_on(self):
		"""Return true if enforce lock is enabled."""
		return self.parent._enforce_lock
		
	async def async_turn_on(self, **kwargs):
		"""Turn on enforce lock."""
		if not self.parent._enforce_lock:
			await self.parent.async_toggle_enforce_lock()
		
	async def async_turn_off(self, **kwargs):
		"""Turn off enforce lock."""
		if self.parent._enforce_lock:
			await self.parent.async_toggle_enforce_lock()
		
	async def async_update_state(self):
		"""Update the entity state."""
		self.async_write_ha_state() 