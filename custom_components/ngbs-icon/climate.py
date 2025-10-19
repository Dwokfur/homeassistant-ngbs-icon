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
    CE_AUTO_RUN,
    CE_OFF,
    CE_ECO,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    client = hass.data[DOMAIN]["client"]

    async def async_get_data():
        return await client.async_get_devices()

    scan_interval = hass.data[DOMAIN].get("scan_interval", DEFAULT_SCAN_INTERVAL)

    coordinator = DataUpdateCoordinator(
        hass,
        logger=_LOGGER,
        name=f"{DOMAIN} device data",
        update_method=async_get_data,
        update_interval=timedelta(seconds=scan_interval),
    )
    await coordinator.async_refresh()
    devices = coordinator.data or []
    entities = [NGBSiConThermostat(client, coordinator, d) for d in devices]
    async_add_entities(entities)


class NGBSiConThermostat(CoordinatorEntity, ClimateEntity):
    def __init__(self, client, coordinator, device):
        super().__init__(coordinator)
        self._client = client
        self._device_id = str(device["ID"])
        self._attr_name = device.get("title", f"NGBS iCON {self._device_id}")
        self._attr_unique_id = self._device_id
        self._attr_temperature_unit = TEMP_CELSIUS
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
        )
        # Per Homebridge plugin, only OFF and AUTO are target modes
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.AUTO]
        self._attr_preset_modes = [PRESET_NONE, PRESET_COMFORT, PRESET_ECO]

    def _dev(self):
        # Helper to fetch the latest device dict
        if not self.coordinator.data:
            return None
        for d in self.coordinator.data:
            if str(d.get("ID")) == self._device_id:
                return d
        return None

    @property
    def current_temperature(self):
        d = self._dev()
        if not d:
            return None
        return d.get("TEMP")

    @property
    def target_temperature(self):
        d = self._dev()
        if not d:
            return None
        return d.get("REQ")

    @property
    def current_humidity(self):
        d = self._dev()
        if not d:
            return None
        rh = d.get("RH")
        if rh is None:
            return None
        try:
            rhf = float(rh)
        except (TypeError, ValueError):
            return None
        return max(0, min(100, rhf))

    @property
    def hvac_mode(self):
        """Target mode derived from CE (do not conflate with relay OUT)."""
        d = self._dev()
        if not d:
            return HVACMode.OFF
        ce = d.get("CE")
        if ce == CE_OFF:
            return HVACMode.OFF
        # All non-off CE values (0 run/auto, 2 eco) map to AUTO as target mode
        return HVACMode.AUTO

    @property
    def hvac_action(self):
        """Current action derived from relay OUT and season."""
        d = self._dev()
        if not d:
            return None
        mode = self.hvac_mode
        out = int(d.get("OUT", 0))
        is_winter = bool(d.get("is_winter", True))

        if mode == HVACMode.OFF:
            return HVACAction.OFF
        if out == 1:
            return HVACAction.HEATING if is_winter else HVACAction.COOLING
        return HVACAction.IDLE

    @property
    def preset_mode(self):
        """Map CE to presets: eco (2), comfort (0), none (1 or unknown)."""
        d = self._dev()
        if not d:
            return PRESET_NONE
        ce = d.get("CE")
        if ce == CE_ECO:
            return PRESET_ECO
        if ce == CE_AUTO_RUN:
            return PRESET_COMFORT
        return PRESET_NONE

    async def async_set_temperature(self, **kwargs):
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        nearest_half = round(float(temp) / 0.5) * 0.5
        # Ensure device is running before setting target
        await self._client.async_set_thermostat_attr(self._device_id, "CE", CE_AUTO_RUN)
        await self._client.async_set_thermostat_attr(self._device_id, "REQ", f"{nearest_half}")
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set target mode via CE; do not toggle OUT directly."""
        if hvac_mode == HVACMode.OFF:
            await self._client.async_set_thermostat_attr(self._device_id, "CE", CE_OFF)
        elif hvac_mode == HVACMode.AUTO:
            await self._client.async_set_thermostat_attr(self._device_id, "CE", CE_AUTO_RUN)
        else:
            _LOGGER.debug("Unsupported hvac_mode requested: %s", hvac_mode)
            return
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str):
        """Set CE based on preset: eco (2), comfort (0), none -> default to 0."""
        if preset_mode == PRESET_ECO:
            ce = CE_ECO
        elif preset_mode == PRESET_COMFORT:
            ce = CE_AUTO_RUN
        else:
            ce = CE_AUTO_RUN
        await self._client.async_set_thermostat_attr(self._device_id, "CE", ce)
        await self.coordinator.async_request_refresh()
