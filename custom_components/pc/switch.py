"""Switch platform for PC Device integration."""
import logging
import json
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.components import mqtt
from .const import (
    DOMAIN, CONF_DEVICE_NAME,
    CONF_POWER_ON_ACTION, CONF_POWER_OFF_ACTION,
    POWER_ON_POWER, POWER_ON_WAKE,
    POWER_OFF_POWER, POWER_OFF_HIBERNATE, POWER_OFF_SLEEP,
    ATTR_VOLUME_LEVEL, ATTR_ACTIVE_WINDOW, ATTR_SESSION_STATE
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the PC device from a config entry."""
    _LOGGER.debug(f"Setting up PC device for config entry: {config_entry.entry_id}")
    device_name = config_entry.data[CONF_DEVICE_NAME]
    _LOGGER.debug(f"Device name: {device_name}")
    
    try:
        entity = PCDevice(hass, config_entry.entry_id, config_entry.data)
        _LOGGER.debug(f"Created PCDevice entity: {entity._attr_unique_id}")
        async_add_entities([entity])
        _LOGGER.debug(f"Added entity {entity._attr_unique_id} to Home Assistant")
    except Exception as e:
        _LOGGER.error(f"Failed to create PCDevice entity: {e}")
        raise

    # Register the device in the device registry
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, device_name.lower())},
        name=f"PC {device_name}",
        manufacturer="Home Assistant",
        model="PC"
    )
    _LOGGER.debug(f"Registered device in device registry: {device_entry.id}")

    # Subscribe to MQTT topics
    set_topic = f"homeassistant/PC/PC.{device_name}/set"
    update_topic = f"homeassistant/PC/PC.{device_name}/update"
    lock_topic = f"homeassistant/PC/PC.{device_name}/lock"

    async def message_received(msg):
        try:
            payload = msg.payload.decode("utf-8") if isinstance(msg.payload, bytes) else str(msg.payload)
        except (AttributeError, UnicodeDecodeError) as e:
            _LOGGER.error(f"Failed to decode MQTT payload for {msg.topic}: {e}")
            return

        if msg.topic == set_topic:
            if payload.upper() == "ON":
                await entity.async_turn_on()
            elif payload.upper() == "OFF":
                await entity.async_turn_off()
        elif msg.topic == lock_topic:
            await entity.async_toggle_enforce_lock()

    await mqtt.async_subscribe(hass, set_topic, message_received)
    await mqtt.async_subscribe(hass, lock_topic, message_received)
    _LOGGER.debug(f"Subscribed to MQTT topics: {set_topic}, {lock_topic}")

class PCDevice(SwitchEntity):
    """Representation of a PC device."""

    def __init__(self, hass, entry_id, config):
        """Initialize the PC device."""
        self.hass = hass
        self._entry_id = entry_id
        self._device_name = config[CONF_DEVICE_NAME]
        self._power_on_action = config[CONF_POWER_ON_ACTION]
        self._power_off_action = config[CONF_POWER_OFF_ACTION]
        self._enforce_lock = False  # Default to False, toggled via lock command
        self._attr_unique_id = f"pc_{self._device_name.lower()}"
        self._attr_name = f"PC {self._device_name}"
        self._state = STATE_ON
        self._attributes = {
            ATTR_VOLUME_LEVEL: 0.5,
            ATTR_ACTIVE_WINDOW: "Notepad",
            ATTR_SESSION_STATE: "unlocked"
        }
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._device_name.lower())},
            "name": f"PC {self._device_name}",
            "manufacturer": "Home Assistant",
            "model": "PC"
        }

        # Track state changes to enforce lock
        self._setup_state_tracking()

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

        # Check if sessionstate changed to unlocked while enforce_lock is active
        session_state = new_state.attributes.get(ATTR_SESSION_STATE, "unlocked")
        if self._enforce_lock and session_state == "unlocked":
            _LOGGER.info(f"Enforced lock active: Re-locking PC {self._device_name}")
            self._attributes[ATTR_SESSION_STATE] = "locked"
            await self._publish_state()
            self.async_write_ha_state()

    @property
    def is_on(self):
        return self._state == STATE_ON

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_turn_on(self, **kwargs):
        """Turn the PC on based on the configured action."""
        if self._power_on_action == POWER_ON_POWER:
            _LOGGER.info(f"Powering on PC {self._device_name}")
            self._state = STATE_ON
            self._attributes[ATTR_SESSION_STATE] = "unlocked"
        elif self._power_on_action == POWER_ON_WAKE:
            _LOGGER.info(f"Sending wake command to PC {self._device_name}")
            self._state = STATE_ON
            self._attributes[ATTR_SESSION_STATE] = "unlocked"

        # Enforce lock if active
        if self._enforce_lock:
            _LOGGER.info(f"Enforced lock active: Locking PC {self._device_name} after turn on")
            self._attributes[ATTR_SESSION_STATE] = "locked"

        await self._publish_state()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the PC off based on the configured action."""
        if self._power_off_action == POWER_OFF_POWER:
            _LOGGER.info(f"Powering off PC {self._device_name}")
            self._state = STATE_OFF
            self._attributes[ATTR_SESSION_STATE] = "locked"
        elif self._power_off_action == POWER_OFF_HIBERNATE:
            _LOGGER.info(f"Hibernating PC {self._device_name}")
            self._state = STATE_OFF
            self._attributes[ATTR_SESSION_STATE] = "locked"
        elif self._power_off_action == POWER_OFF_SLEEP:
            _LOGGER.info(f"Sleeping PC {self._device_name}")
            self._state = STATE_OFF
            self._attributes[ATTR_SESSION_STATE] = "locked"

        await self._publish_state()
        self.async_write_ha_state()

    async def async_set_volume(self, volume_level):
        """Set the volume of the PC."""
        self._attributes[ATTR_VOLUME_LEVEL] = float(volume_level)
        await self._publish_state()
        self.async_write_ha_state()

    async def async_mute(self):
        """Mute or unmute the PC."""
        _LOGGER.info(f"Muting PC {self._device_name}")
        await self._publish_state()
        self.async_write_ha_state()

    async def async_toggle_enforce_lock(self):
        """Toggle the enforced lock state."""
        self._enforce_lock = not self._enforce_lock
        _LOGGER.info(f"Enforced lock for PC {self._device_name} set to {self._enforce_lock}")
        if self._enforce_lock and self._attributes[ATTR_SESSION_STATE] == "unlocked":
            self._attributes[ATTR_SESSION_STATE] = "locked"
        await self._publish_state()
        self.async_write_ha_state()

    async def _publish_state(self):
        """Publish the current state to the MQTT update topic."""
        state = self._state
        payload = {
            "entity_id": f"PC.{self._device_name}",
            "state": state,
            ATTR_VOLUME_LEVEL: self._attributes[ATTR_VOLUME_LEVEL],
            ATTR_ACTIVE_WINDOW: self._attributes[ATTR_ACTIVE_WINDOW],
            ATTR_SESSION_STATE: self._attributes[ATTR_SESSION_STATE]
        }
        topic = f"homeassistant/PC/PC.{self._device_name}/update"
        try:
            payload_str = json.dumps(payload)
            await mqtt.async_publish(self.hass, topic, payload_str)
        except (TypeError, ValueError) as e:
            _LOGGER.error(f"Failed to serialize state to JSON for {topic}: {e}")
