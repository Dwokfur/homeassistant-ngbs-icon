import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .ngbs_icon_api import NGBSiConClient


class NgbsIconConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            username = user_input["username"]
            password = user_input["password"]
            icon_id = user_input["icon_id"]

            session = async_get_clientsession(self.hass)
            client = NGBSiConClient(session, username, password, icon_id)
            ok = await client.async_login()
            if not ok:
                errors["base"] = "auth_failed"
            else:
                await self.async_set_unique_id(icon_id)
                self._abort_if_unique_id_configured()
                data = {
                    "username": username,
                    "password": password,
                    "icon_id": icon_id,
                    "scan_interval": user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL),
                }
                return self.async_create_entry(title="NGBS iCON", data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                    vol.Required("icon_id"): str,
                    vol.Optional("scan_interval", default=DEFAULT_SCAN_INTERVAL): int,
                }
            ),
            errors=errors,
        )
