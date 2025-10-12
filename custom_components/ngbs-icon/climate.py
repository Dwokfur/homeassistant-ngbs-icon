from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT, HVAC_MODE_COOL, SUPPORT_TARGET_TEMPERATURE
)
from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator, CoordinatorEntity
)
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

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
        self._attr_supported_features = SUPPORT_TARGET_TEMPERATURE

    @property
    def current_temperature(self):
        return self._device.get("room_temp")

    @property
    def target_temperature(self):
        return self._device.get("target_temp")

    async def async_set_temperature(self, **kwargs):
        temp = kwargs.get("temperature")
        await self._client.async_set_thermostat_attr(self._attr_unique_id, "target_temp", temp)
        await self.coordinator.async_request_refresh()