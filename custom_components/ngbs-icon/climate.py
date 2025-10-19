import logging
from datetime import timedelta

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode,
    HVACAction,
    ClimateEntityFeature,
)
from homeassistant.const import TEMP_CELSIUS, ATTR_TEMPERATURE
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)
from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    PRESET_ECO,
    PRESET_COMFORT,
    PRESET_NONE,
    CE_MANUAL,
    CE_AUTO,
    CE_ECO,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    client = hass.data[DOMAIN]["client"]
    scan_interval = hass.data[DOMAIN].get("scan_interval", DEFAULT_SCAN_INTERVAL)

    async def async_get_data():
        return await client.async_get_devices()

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN} device data",
        update_method=async_get_data,
        update_interval=timedelta(seconds=scan_interval),
    )
    await coordinator.async_refresh()
    entities = [NGBSiConThermostat(client, coordinator, d) for d in coordinator.data]
    async_add_entities(entities)


class NGBSiConThermostat(CoordinatorEntity, ClimateEntity):
    def __init__(self, client, coordinator, device):
        super().__init__(coordinator)
        self._client = client
        self._device_id = device["ID"]
        self._attr_name = device["title"]
        self._attr_unique_id = device["ID"]
        self._attr_temperature_unit = TEMP_CELSIUS
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
        )
        self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO]
        self._attr_preset_modes = [PRESET_NONE, PRESET_COMFORT, PRESET_ECO]

    def _get_device_data(self):
        """Helper to get current device data from coordinator."""
        for d in self.coordinator.data:
            if d["ID"] == self._device_id:
                return d
        return None

    @property
    def current_temperature(self):
        device = self._get_device_data()
        return device.get("room_temp") if device else None

    @property
    def target_temperature(self):
        device = self._get_device_data()
        return device.get("target_temp") if device else None

    @property
    def current_humidity(self):
        """Return the current humidity from RH property."""
        device = self._get_device_data()
        if device:
            rh = device.get("RH")
            if rh is not None:
                # Ensure it's an int in 0-100 range
                return int(rh) if 0 <= rh <= 100 else None
        return None

    @property
    def hvac_mode(self):
        """Return target HVAC mode based on CE and is_winter flags."""
        device = self._get_device_data()
        if not device:
            return HVACMode.AUTO

        ce = device.get("CE", 0)
        is_winter = device.get("is_winter", True)

        # If CE is auto mode, return auto
        if ce == CE_AUTO:
            return HVACMode.AUTO

        # Otherwise, determine heat or cool based on is_winter
        return HVACMode.HEAT if is_winter else HVACMode.COOL

    @property
    def hvac_action(self):
        """Return current HVAC action based on OUT relay state."""
        device = self._get_device_data()
        if not device:
            return HVACAction.IDLE

        out = device.get("OUT", 0)
        is_winter = device.get("is_winter", True)

        # If OUT is 0, relay is idle
        if out == 0:
            return HVACAction.IDLE

        # OUT is 1, determine heating or cooling based on is_winter
        return HVACAction.HEATING if is_winter else HVACAction.COOLING

    @property
    def preset_mode(self):
        """Return current preset mode based on CE property."""
        device = self._get_device_data()
        if not device:
            return PRESET_NONE

        ce = device.get("CE", 0)
        if ce == CE_ECO:
            return PRESET_ECO
        elif ce == CE_MANUAL:
            return PRESET_COMFORT
        # CE_AUTO is a mode, not a preset
        return PRESET_NONE

    async def async_set_temperature(self, **kwargs):
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is not None:
            await self._client.async_set_thermostat_attr(
                self._device_id, "target_temp", temp
            )
            await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set HVAC mode."""
        if hvac_mode == HVACMode.AUTO:
            # Set to auto mode (CE = 1)
            await self._client.async_set_thermostat_attr(self._device_id, "CE", CE_AUTO)
        else:  # HVACMode.HEAT or HVACMode.COOL
            # Set to manual mode (CE = 0)
            # Note: Heat/Cool is determined by is_winter flag which is global
            await self._client.async_set_thermostat_attr(
                self._device_id, "CE", CE_MANUAL
            )
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str):
        """Set preset mode (Eco, Comfort, None)."""
        if preset_mode == PRESET_ECO:
            await self._client.async_set_thermostat_attr(self._device_id, "CE", CE_ECO)
        elif preset_mode == PRESET_COMFORT:
            await self._client.async_set_thermostat_attr(
                self._device_id, "CE", CE_MANUAL
            )
        else:  # PRESET_NONE (should not happen with current preset_modes)
            await self._client.async_set_thermostat_attr(
                self._device_id, "CE", CE_MANUAL
            )
        await self.coordinator.async_request_refresh()
