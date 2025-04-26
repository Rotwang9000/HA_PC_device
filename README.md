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

   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rotwang9000&repository=HA_PC_device&category=integration)

3. In HACS, search for "PC Device" and install the integration.
4. Restart Home Assistant.

### Manual Installation
1. Copy the `pc` folder to your Home Assistant `custom_components` directory:
