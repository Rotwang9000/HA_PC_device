import logging
import json
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_ON, STATE_OFF, SERVICE_TURN_ON, SERVICE_TURN_OFF
from homeassistant.helpers import device_registry as dr
from homeassistant.components import mqtt
from .const import (
    DOMAIN, CONF_DEVICE_NAME, CONF_FS_NAME, CONF_USE_FS_LOCK,
    ATTR_VOLUME_LEVEL, ATTR_ACTIVE_WINDOW, ATTR_SESSION_STATE,
    FS_BLOCK_WINDOWS, FS_BLOCK_XBOX
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the PC device from a config entry."""
    device_name = config_entry.data[CONF_DEVICE_NAME]
    entity = PCDevice(hass, config_entry.entry_id, config_entry.data)
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

    def __init__(self, hass, entry_id, config):
        """Initialize the PC device."""
        self.hass = hass
        self._entry_id = entry_id
        self._device_name = config[CONF_DEVICE_NAME]
        self._fs_name = config.get(CONF_FS_NAME, "")
        self._use_fs_lock = config.get(CONF_USE_FS_LOCK, False)
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

        # If using Family Safety lock, turn off the block switches
        if self._use_fs_lock and self._fs_name:
            for block_type in [FS_BLOCK_WINDOWS, FS_BLOCK_XBOX]:
                switch_entity = f"switch.{self._fs_name.lower()}_block_{block_type}"
                await self.hass.services.async_call(
                    "switch", SERVICE_TURN_OFF,
                    {"entity_id": switch_entity},
                    blocking=True
                )

        await self._publish_state()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the PC off."""
        if self._use_fs_lock and self._fs_name:
            # Use Family Safety lock instead of power off
            self._state = STATE_OFF
            self._attributes[ATTR_SESSION_STATE] = "locked"

            # Turn on the block switches
            for block_type in [FS_BLOCK_WINDOWS, FS_BLOCK_XBOX]:
                switch_entity = f"switch.{self._fs_name.lower()}_block_{block_type}"
                await self.hass.services.async_call(
                    "switch", SERVICE_TURN_ON,
                    {"entity_id": switch_entity},
                    blocking=True
                )
        else:
            # Default power off behavior
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
