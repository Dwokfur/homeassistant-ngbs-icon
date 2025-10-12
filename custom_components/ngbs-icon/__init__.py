import asyncio
import aiohttp
from homeassistant.core import HomeAssistant
from .const import DOMAIN, SESSION_REFRESH_INTERVAL

async def async_setup_entry(hass: HomeAssistant, config_entry):
    from .ngbs_icon_api import NGBSiConClient

    username = config_entry.data["username"]
    password = config_entry.data["password"]
    icon_id = config_entry.data["icon_id"]
    scan_interval = config_entry.options.get("scan_interval", 300)
    session = aiohttp.ClientSession()
    client = NGBSiConClient(session, username, password, icon_id)
    hass.data.setdefault(DOMAIN, {})["client"] = client
    hass.data[DOMAIN]["scan_interval"] = scan_interval

    # Start periodic session refresh
    async def periodic_refresh():
        while True:
            await client.async_login()
            await asyncio.sleep(SESSION_REFRESH_INTERVAL)
    hass.async_create_task(periodic_refresh())

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, "climate")
    )
    return True
