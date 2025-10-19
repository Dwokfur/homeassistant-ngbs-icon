import logging

import async_timeout
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)
BASE_URL = "https://enzoldhazam.hu"


class NGBSiConClient:
    def __init__(self, session, username, password, icon_id):
        self._session = session
        self._username = username
        self._password = password
        self._icon_id = icon_id
        self._logged_in = False

    async def async_login(self) -> bool:
        try:
            async with async_timeout.timeout(15):
                async with self._session.get(BASE_URL) as resp:
                    text = await resp.text()
                soup = BeautifulSoup(text, "html.parser")
                token_tag = soup.find("input", {"name": "token"})
                if not token_tag:
                    _LOGGER.error("Login token not found on landing page")
                    self._logged_in = False
                    return False
                token = token_tag.get("value")

                payload = {
                    "username": self._username,
                    "password": self._password,
                    "token": token,
                    "x-email": "",
                }
                async with self._session.post(BASE_URL, data=payload) as login_resp:
                    login_text = await login_resp.text()
                    if "Bejelentkezés" in login_text:
                        _LOGGER.error("Login failed: credentials rejected")
                        self._logged_in = False
                        return False
                    self._logged_in = True
                    _LOGGER.debug("Logged in to NGBS iCON cloud")
                    return True
        except Exception as err:
            _LOGGER.error("Login error: %s", err)
            self._logged_in = False
            return False

    async def _ensure_login(self):
        if not self._logged_in:
            ok = await self.async_login()
            if not ok:
                raise RuntimeError("Authentication failed")

    async def async_get_devices(self):
        try:
            await self._ensure_login()
            async with async_timeout.timeout(15):
                async with self._session.get(f"{BASE_URL}/Ax?action=iconList") as resp:
                    if resp.status == 401:
                        self._logged_in = False
                        await self._ensure_login()
                        return await self.async_get_devices()
                    data = await resp.json()
        except Exception as err:
            _LOGGER.error("Device fetch error: %s", err)
            return []

        try:
            icon = data["ICONS"][self._icon_id]
            devices = icon["DP"]
            con_value = icon.get("CON_VALUE", 0)
            is_winter = con_value == 0  # 0 = heating (winter), 1 = cooling (summer)

            for device in devices:
                device["is_winter"] = is_winter
                device.setdefault("OUT", 0)
                device.setdefault("RH", None)
                device.setdefault("CE", 0)
                device.setdefault("TEMP", None)
                device.setdefault("REQ", None)

            return devices
        except Exception as err:
            _LOGGER.error("Unexpected device payload format: %s", err)
            return []

    async def async_set_thermostat_attr(self, device_id, attr, value) -> bool:
        try:
            await self._ensure_login()
            payload = {
                "action": "setThermostat",
                "icon": self._icon_id,
                "thermostat": device_id,
                "attr": attr,
                "value": value,
            }
            async with async_timeout.timeout(15):
                async with self._session.post(f"{BASE_URL}/Ax", data=payload) as resp:
                    if resp.status == 401:
                        self._logged_in = False
                        await self._ensure_login()
                        return await self.async_set_thermostat_attr(device_id, attr, value)
                    return resp.status == 200
        except Exception as err:
            _LOGGER.error("Set attribute error: %s", err)
            return False
