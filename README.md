# PC Device Integration for Home Assistant

This custom integration allows you to manage PC devices in Home Assistant, treating them as first-class entities similar to lights or media players. It supports turning the PC on/off, setting volume, muting, locking, and integrates with Microsoft Family Safety for hard lockouts.

It creates a composite device from https://github.com/LAB02-Research/HASS.Agent sensors and buttons.
Optionally it can also lockout using https://github.com/pantherale0/ha-familysafety instead of power on/off.

## Features
- Creates a `pc` domain with entities like `pc.emmalaptop` and `pc.fredspc`.
- Supports standard services: `turn_on`, `turn_off`.
- Custom services: `pc.set_volume`, `pc.mute`, `pc.lock`.
- Exposes attributes: `volume_level`, `activewindow`, `sessionstate`.
- Optional integration with Microsoft Family Safety for hard lockouts instead of power off.
- Configurable via the Home Assistant Integrations page.

## Installation

### Via HACS
1. Ensure you have [HACS](https://hacs.xyz/) installed in Home Assistant.
2. Click the button below to add the repository to HACS:

   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Rotwang9000&repository=HA_PC_device&category=integration)

3. In HACS, search for "PC Device" and install the integration.
4. Restart Home Assistant.

### Manual Installation
1. Copy the `pc` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant.

## Setup

### Prerequisites
This integration requires the following Home Assistant entities for Family Safety integration (if enabled):

#### For `emmaLaptop` (Family Safety name: `emma`):
- `switch.emma_block_windows`: Switch to block Windows access.
- `switch.emma_block_xbox`: Switch to block Xbox access.
- `sensor.emma_available_balance`: (Optional) Sensor for available screen time balance.
- `sensor.emma_used_screen_time`: (Optional) Sensor for used screen time.

#### For `FredPC` (Family Safety name: `Neural`):
- `switch.fred_block_windows`: Switch to block Windows access.
- `switch.fred_block_xbox`: Switch to block Xbox access.
- `sensor.fred_available_balance`: (Optional) Sensor for available screen time balance.
- `sensor.fred_used_screen_time`: (Optional) Sensor for used screen time.

These entities are typically provided by the [Microsoft Family Safety](https://www.home-assistant.io/integrations/microsoft_family_safety) integration. Ensure it is set up and the Family Safety names match the ones you configure in this integration.

### Adding a PC Device
1. Go to **Settings > Devices & Services > Integrations** in Home Assistant.
2. Click **+ Add Integration** and search for "PC Device".
3. Configure the PC device:
- **Device Name**: The name of the PC (e.g., `emmaLaptop`, `FredPC`). This will create an entity like `pc.emmalaptop`.
- **Family Safety Name**: (Optional) The Family Safety name (e.g., `emma`, `Neural`). This is used to construct the Family Safety switch entity IDs (e.g., `switch.emma_block_windows`).
- **Use Family Safety Lock**: (Optional) If enabled, turning off the PC will activate the Family Safety block switches instead of a power-off action. Turning on will deactivate them.
4. Submit the configuration.
5. Repeat for additional PCs (e.g., `emmaLaptop` and `FredPC`).

## Usage
- **Entities:** After setup, you’ll have entities like `pc.emmalaptop` and `pc.fredpc`.
- **State:** The entity state is `on` or `off`.
- **Attributes:**
  - `volume_level`: The volume level (0.0 to 1.0).
  - `activewindow`: The currently active window (e.g., "Notepad").
  - `sessionstate`: The session state (e.g., "unlocked", "locked").
- **Services:**
  - `pc.set_volume`: Set the volume (e.g., `{"entity_id": "pc.emmalaptop", "volume_level": 0.5}`).
  - `pc.mute`: Mute or unmute the PC.
  - `pc.lock`: Lock the PC.
  - `switch.turn_on` / `switch.turn_off`: Turn the PC on or off.

## MQTT Topics
The integration uses the following MQTT topics for communication:
- **Set Command:** `homeassistant/PC/PC.<DeviceName>/set` (e.g., `homeassistant/PC/PC.emmaLaptop/set`)
  - Payload: `ON` or `OFF`
- **Set Volume:** `homeassistant/PC/PC.<DeviceName>/setvolume` (e.g., `homeassistant/PC/PC.emmaLaptop/setvolume`)
  - Payload: Volume level (0 to 100, scaled to 0.0-1.0 internally)
- **Mute:** `homeassistant/PC/PC.<DeviceName>/mute` (e.g., `homeassistant/PC/PC.emmaLaptop/mute`)
  - Payload: Any (triggers mute action)
- **Lock:** `homeassistant/PC/PC.<DeviceName>/lock` (e.g., `homeassistant/PC/PC.emmaLaptop/lock`)
  - Payload: Any (triggers lock action)
- **State Update:** `homeassistant/PC/PC.<DeviceName>/update` (e.g., `homeassistant/PC/PC.emmaLaptop/update`)
  - Payload: JSON with `entity_id`, `state`, `volume_level`, `activewindow`, `sessionstate`

## Example Configuration
For `emmaLaptop` and `FredPC`:
1. Add `emmaLaptop`:
- Device Name: `emmaLaptop`
- Family Safety Name: `emma`
- Use Family Safety Lock: `True`
2. Add `FredPC`:
- Device Name: `FredPC`
- Family Safety Name: `Neural`
- Use Family Safety Lock: `True`

This will create `pc.emmalaptop` and `pc.fredpc` entities, and turning them off will activate the corresponding Family Safety block switches (e.g., `switch.emma_block_windows`, `switch.fred_block_xbox`).

## Node-RED Integration
This integration works seamlessly with Node-RED flows that use MQTT to control devices. Ensure your Node-RED flow:
- Subscribes to the `update` topic to receive state updates.
- Publishes to the `set`, `setvolume`, `mute`, and `lock` topics to control the PC.
- Uses the `pc` domain for service calls (e.g., `pc.set_volume`, `pc.mute`, `pc.lock`).

## Contributing
Feel free to submit issues or pull requests to improve this integration!

## License
MIT License
