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
		# Create entity
		entity = ComputerDevice(hass, config_entry.entry_id, config_entry.data)
		async_add_entities([entity])
		_LOGGER.debug("Added entity %s to Home Assistant", entity.entity_id)

		# Store entity for later access
		hass.data.setdefault(DOMAIN, {})
		if "entities" not in hass.data[DOMAIN]:
			hass.data[DOMAIN]["entities"] = {}
		hass.data[DOMAIN]["entities"][config_entry.entry_id] = entity
	except Exception as e:
		_LOGGER.error("Failed to create Computer entity: %s", e)
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
	if not await mqtt.async_wait_for_mqtt_client(hass, timeout=5):
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
		elif msg.topic == mute_topic:
			await entity.async_toggle_mute()
		elif msg.topic == setvolume_topic:
			try:
				volume = float(payload)
				await entity.async_set_volume_level(volume)
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
		self._attr_unique_id = f"computer_{self._device_name.lower()}"
		self._attr_name = f"Computer {self._device_name}"
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