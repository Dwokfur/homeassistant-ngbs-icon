from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVACMode, ClimateEntityFeature
)
from homeassistant.const import TEMP_CELSIUS, ATTR_TEMPERATURE
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator, CoordinatorEntity
)
from .const import (
    DOMAIN, DEFAULT_SCAN_INTERVAL, 
    PRESET_ECO, PRESET_COMFORT, PRESET_NONE,
    CE_MANUAL, CE_AUTO, CE_ECO
)

async def async_setup_entry(hass, config_entry, async_add_entities):
    client = hass.data[DOMAIN]["client"]
    async def async_get_data():
        return await client.async_get_devices()
    coordinator = DataUpdateCoordinator(
        hass,
        logger=hass.logger,
        name=f"{DOMAIN} device data",
        update_method=async_get_data,
        update_interval=hass.data[DOMAIN].get("scan_interval", DEFAULT_SCAN_INTERVAL)
    )
    await coordinator.async_refresh()
    entities = [NGBSiConThermostat(client, coordinator, d) for d in coordinator.data]
    async_add_entities(entities)

class NGBSiConThermostat(CoordinatorEntity, ClimateEntity):
    def __init__(self, client, coordinator, device):
        super().__init__(coordinator)
        self._client = client
        self._device = device
        self._attr_name = device["title"]
        self._attr_unique_id = device["ID"]
        self._attr_temperature_unit = TEMP_CELSIUS
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE |
            ClimateEntityFeature.PRESET_MODE
        )
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO]
        self._attr_preset_modes = [PRESET_NONE, PRESET_COMFORT, PRESET_ECO]

    @property
    def current_temperature(self):
        for d in self.coordinator.data:
            if d["ID"] == self._attr_unique_id:
                return d.get("room_temp")
        return None

    @property
    def target_temperature(self):
        for d in self.coordinator.data:
            if d["ID"] == self._attr_unique_id:
                return d.get("target_temp")
        return None

    @property
    def current_humidity(self):
        """Return the current humidity from RH property."""
        for d in self.coordinator.data:
            if d["ID"] == self._attr_unique_id:
                return d.get("RH")
        return None

    @property
    def hvac_mode(self):
        """Return current HVAC mode based on OUT and is_winter flags."""
        for d in self.coordinator.data:
            if d["ID"] == self._attr_unique_id:
                out = d.get("OUT", 0)
                is_winter = d.get("is_winter", True)
                ce = d.get("CE", 0)
                
                # If OUT is 0, system is off
                if out == 0:
                    return HVACMode.OFF
                
                # If CE is auto mode, return auto
                if ce == CE_AUTO:
                    return HVACMode.AUTO
                
                # Otherwise, determine heat or cool based on is_winter
                return HVACMode.HEAT if is_winter else HVACMode.COOL
        return HVACMode.OFF

    @property
    def preset_mode(self):
        """Return current preset mode based on CE property."""
        for d in self.coordinator.data:
            if d["ID"] == self._attr_unique_id:
                ce = d.get("CE", 0)
                if ce == CE_ECO:
                    return PRESET_ECO
                elif ce == CE_AUTO:
                    return PRESET_COMFORT
                else:
                    return PRESET_NONE
        return PRESET_NONE

    async def async_set_temperature(self, **kwargs):
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is not None:
            await self._client.async_set_thermostat_attr(self._attr_unique_id, "target_temp", temp)
            await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            # Turn off the system by setting OUT to 0
            await self._client.async_set_thermostat_attr(self._attr_unique_id, "OUT", 0)
        elif hvac_mode == HVACMode.AUTO:
            # Set to auto mode (CE = 1) and turn on (OUT = 1)
            await self._client.async_set_thermostat_attr(self._attr_unique_id, "CE", CE_AUTO)
            await self._client.async_set_thermostat_attr(self._attr_unique_id, "OUT", 1)
        else:  # HVACMode.HEAT or HVACMode.COOL
            # Set to manual mode (CE = 0) and turn on (OUT = 1)
            # Note: Heat/Cool is determined by is_winter flag which is global
            await self._client.async_set_thermostat_attr(self._attr_unique_id, "CE", CE_MANUAL)
            await self._client.async_set_thermostat_attr(self._attr_unique_id, "OUT", 1)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str):
        """Set preset mode (Eco, Comfort, None)."""
        if preset_mode == PRESET_ECO:
            await self._client.async_set_thermostat_attr(self._attr_unique_id, "CE", CE_ECO)
            await self._client.async_set_thermostat_attr(self._attr_unique_id, "OUT", 1)
        elif preset_mode == PRESET_COMFORT:
            await self._client.async_set_thermostat_attr(self._attr_unique_id, "CE", CE_AUTO)
            await self._client.async_set_thermostat_attr(self._attr_unique_id, "OUT", 1)
        else:  # PRESET_NONE
            await self._client.async_set_thermostat_attr(self._attr_unique_id, "CE", CE_MANUAL)
            await self._client.async_set_thermostat_attr(self._attr_unique_id, "OUT", 1)
        await self.coordinator.async_request_refresh()