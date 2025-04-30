# Computer Control MQTT Troubleshooting Guide

## Issue: Controls visible but not functioning

When your Computer Control entities are visible in Home Assistant but not functioning when clicked, the issue is typically related to the MQTT communication between Home Assistant and the HASS.Agent on your PC.

## Required Components

1. **Home Assistant** with the Computer Control integration installed
2. **MQTT Broker** (like Mosquitto) running and configured in Home Assistant
3. **HASS.Agent** installed on your PC with MQTT properly configured

## Step 1: Verify MQTT is properly set up in Home Assistant

1. In Home Assistant, go to **Settings** > **Devices & Services** > **Integrations**
2. Check if MQTT is listed and showing as "Connected"
3. If not, add the MQTT integration and configure it with your broker details
   - You can use the built-in Mosquitto addon if using Home Assistant OS

## Step 2: Install and Configure HASS.Agent on your PC

1. Download HASS.Agent from [https://github.com/LAB02-Research/HASS.Agent](https://github.com/LAB02-Research/HASS.Agent)
2. Install it on your PC (FelixLaptop)
3. During setup or in Settings:
   - Enter your Home Assistant URL
   - Configure the MQTT connection with:
     - Your MQTT broker address (the IP of your Home Assistant instance)
     - MQTT port (usually 1883)
     - MQTT username and password (if configured)
   - Test the connection to ensure it's working

## Step 3: Verify MQTT Topic Compatibility

The updated Computer Control integration now supports two MQTT topic formats:

### Original Computer Control Format
- Set Command: `homeassistant/Computer/Computer.felixlaptop/set`
- Set Volume: `homeassistant/Computer/Computer.felixlaptop/setvolume`
- Mute: `homeassistant/Computer/Computer.felixlaptop/mute`
- Lock: `homeassistant/Computer/Computer.felixlaptop/lock`

### HASS.Agent Format (Now Supported)
- Lock command: `homeassistant/button/FelixLaptop/FelixLaptop_lock/command`
- Mute command: `homeassistant/button/FelixLaptop/FelixLaptop_mute/command`
- Set volume command: `homeassistant/button/FelixLaptop/FelixLaptop_setvolume/command`
- Active window state: `homeassistant/sensor/FelixLaptop/FelixLaptop_activewindow/state`
- Session state: `homeassistant/sensor/FelixLaptop/FelixLaptop_sessionstate/state`
- Current volume state: `homeassistant/sensor/FelixLaptop/FelixLaptop_currentvolume/state`

## Step 4: Check Case Sensitivity

MQTT topics are case sensitive. Make sure the case matches exactly:
- If HASS.Agent uses `FelixLaptop` (capital F and L), the integration now supports this exact format
- Make sure device name in Home Assistant matches the case used in HASS.Agent

## Step 5: Associate MQTT Entities with Computer Device

The latest update automatically associates HASS.Agent MQTT entities with the Computer device in Home Assistant. After updating:

1. Restart Home Assistant
2. Go to **Settings** > **Devices & Services** > **Devices**
3. Find your Computer device (e.g., "Computer FelixLaptop")
4. Verify that all HASS.Agent entities are now associated with this device
5. If not, you can manually move them in the entity registry

## Testing

To test if MQTT is working correctly:
1. Use MQTT Explorer to publish a test message to `homeassistant/button/FelixLaptop/FelixLaptop_mute/command` with any payload
2. Check if your PC responds
3. If not, verify HASS.Agent is subscribed to this topic

## Debugging

If you're still having issues:
1. Check Home Assistant logs for MQTT-related errors: **Settings** > **System** > **Logs**
2. Look for "computer" or "mqtt" related messages
3. Check HASS.Agent logs on your PC for connection issues

The Computer Control integration now supports both topic formats for maximum compatibility. 