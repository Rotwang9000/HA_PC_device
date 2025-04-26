import logging
import json
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.helpers import device_registry as dr
from homeassistant.components.mqtt import subscription
from homeassistant.components import mqtt
from .const import DOMAIN, CONF_DEVICE_NAME, ATTR_VOLUME_LEVEL, ATTR_ACTIVE_WINDOW, ATTR_SESSION_STATE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the PC device from a config entry."""
    device_name = config_entry.data[CONF_DEVICE_NAME]
    entity = PCDevice(hass, config_entry.entry_id, device_name)
    async_add_entities([entity])

    # Register the device in the device registry
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, device_name.lower())},
        name=f"PC {device_name}",
        manufacturer="Home Assistant",
        model="PC"
    )

    # Subscribe to MQTT topics
    set_topic = f"homeassistant/PC/PC.{device_name}/set"
    update_topic = f"homeassistant/PC/PC.{device_name}/update"

    async def message_received(msg):
        payload = msg.payload
        if msg.topic == set_topic:
            if payload == "ON":
                await entity.async_turn_on()
            elif payload == "OFF":
                await entity.async_turn_off()

    await mqtt.async_subscribe(hass, set_topic, message_received)

class PCDevice(SwitchEntity):
    """Representation of a PC device."""

    def __init__(self, hass, entry_id, device_name):
        """Initialize the PC device."""
        self.hass = hass
        self._entry_id = entry_id
        self._device_name = device_name
        self._attr_unique_id = f"pc_{device_name.lower()}"
        self._attr_name = f"PC {device_name}"
        self._state = STATE_ON
        self._attributes = {
            ATTR_VOLUME_LEVEL: 0.5,
            ATTR_ACTIVE_WINDOW: "Notepad",
            ATTR_SESSION_STATE: "unlocked"
        }
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_name.lower())},
            "name": f"PC {device_name}",
            "manufacturer": "Home Assistant",
            "model": "PC"
        }

    @property
    def is_on(self):
        return self._state == STATE_ON

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_turn_on(self, **kwargs):
        """Turn the PC on."""
        self._state = STATE_ON
        self._attributes[ATTR_SESSION_STATE] = "unlocked"
        await self._publish_state()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the PC off."""
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
        # For simplicity, we'll just log this action
        # In a real implementation, you might toggle a mute state
        _LOGGER.info(f"Muting PC {self._device_name}")
        await self._publish_state()
        self.async_write_ha_state()

    async def async_lock(self):
        """Lock the PC."""
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
        await mqtt.async_publish(self.hass, topic, json.dumps(payload))
