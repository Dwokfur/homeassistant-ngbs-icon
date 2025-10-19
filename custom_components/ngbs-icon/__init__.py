import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .ngbs_icon_api import NGBSiConClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    username = config_entry.data["username"]
    password = config_entry.data["password"]
    icon_id = config_entry.data["icon_id"]

    scan_interval = config_entry.options.get(
        "scan_interval", config_entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL)
    )

    session = async_get_clientsession(hass)
    client = NGBSiConClient(session, username, password, icon_id)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["client"] = client
    hass.data[DOMAIN]["scan_interval"] = scan_interval

    await hass.config_entries.async_forward_entry_setups(config_entry, ["climate"])
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, ["climate"])
    if unload_ok:
        for key in ("client", "scan_interval"):
            hass.data.get(DOMAIN, {}).pop(key, None)
    return unload_ok
