import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN


class NgbsIconConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NGBS iCON."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Set unique_id to prevent duplicate entries
            await self.async_set_unique_id(user_input["icon_id"])
            self._abort_if_unique_id_configured()

            # Validate credentials by attempting login
            from .ngbs_icon_api import NGBSiConClient

            session = async_get_clientsession(self.hass)
            client = NGBSiConClient(
                session,
                user_input["username"],
                user_input["password"],
                user_input["icon_id"],
            )

            # Attempt login to validate credentials
            login_success = await client.async_login()

            if not login_success:
                errors["base"] = "auth_failed"
            else:
                # Try to fetch devices to validate icon_id
                devices = await client.async_get_devices()
                if not devices:
                    errors["base"] = "cannot_connect"
                else:
                    # Success - create entry
                    # Move scan_interval to options
                    scan_interval = user_input.pop("scan_interval", 300)
                    return self.async_create_entry(
                        title=f"NGBS iCON {user_input['icon_id']}",
                        data=user_input,
                        options={"scan_interval": scan_interval},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                    vol.Required("icon_id"): str,
                    vol.Optional("scan_interval", default=300): int,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return NgbsIconOptionsFlowHandler(config_entry)


class NgbsIconOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for NGBS iCON."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "scan_interval",
                        default=self.config_entry.options.get("scan_interval", 300),
                    ): int,
                }
            ),
        )
