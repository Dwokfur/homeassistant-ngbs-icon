import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

class NgbsIconConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # TODO: Optionally test login here for validation
            return self.async_create_entry(title="NGBS iCON", data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("username"): str,
                vol.Required("password"): str,
                vol.Required("icon_id"): str,
                vol.Optional("scan_interval", default=30): int,
            }),
            errors=errors,
        )