# Home Assistant NGBS iCON Thermostat Integration

**Native Home Assistant integration for NGBS iCON cloud thermostats.**

## Features

- Direct cloud communication with [enzoldhazam.hu](https://enzoldhazam.hu)
- Async, error-handling, periodic session refresh
- Home Assistant config flow (UI setup)
- Exposes thermostats as `climate` entities

## Attribution

This integration is based on the initial [Homebridge NGBS iCON plugin](https://github.com/peterrakolcza/homebridge-ngbs-icon-thermostat) by [peterrakolcza](https://github.com/peterrakolcza).
Python code and Home Assistant adaptation created by [Copilot](https://github.com/features/copilot) for [Dwokfur](https://github.com/Dwokfur).

## License

This repository is licensed under the [Apache License 2.0](LICENSE).

## Installation

1. Copy `custom_components/ngbs_icon/` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add integration via UI: "NGBS iCON".

## Configuration

Via UI: Enter username, password, iCONid, and scan interval (seconds).

## License

Apache 2.0. See [LICENSE](LICENSE).