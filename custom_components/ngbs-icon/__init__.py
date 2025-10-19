from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, PLATFORMS


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up NGBS iCON from a config entry."""
    from .ngbs_icon_api import NGBSiConClient

    username = config_entry.data["username"]
    password = config_entry.data["password"]
    icon_id = config_entry.data["icon_id"]
    scan_interval = config_entry.options.get("scan_interval", 300)

    # Use Home Assistant's shared aiohttp session
    session = async_get_clientsession(hass)
    client = NGBSiConClient(session, username, password, icon_id)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["client"] = client
    hass.data[DOMAIN]["scan_interval"] = scan_interval

    # Forward entry setup to climate platform
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    if unload_ok:
        # Clean up stored data
        hass.data[DOMAIN].pop("client", None)
        hass.data[DOMAIN].pop("scan_interval", None)

    return unload_ok
