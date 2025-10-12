import aiohttp
import async_timeout
from bs4 import BeautifulSoup
import logging
import asyncio

from .const import SESSION_REFRESH_INTERVAL

_LOGGER = logging.getLogger(__name__)
BASE_URL = "https://enzoldhazam.hu"

class NGBSiConClient:
    def __init__(self, session, username, password, icon_id):
        self._session = session
        self._username = username
        self._password = password
        self._icon_id = icon_id
        self._phpsessid = None
        self._logged_in = False

    async def async_login(self):
        try:
            async with async_timeout.timeout(15):
                async with self._session.get(BASE_URL) as resp:
                    text = await resp.text()
                    soup = BeautifulSoup(text, "html.parser")
                    token_tag = soup.find("input", {"name": "token"})
                    if not token_tag:
                        _LOGGER.error("Token input not found on login page")
                        self._logged_in = False
                        return False
                    token = token_tag.get("value")
                    phpsessid = resp.cookies.get("PHPSESSID")
                    payload = {
                        "username": self._username,
                        "password": self._password,
                        "token": token,
                        "x-email": ""
                    }
                    headers = {"Cookie": f"PHPSESSID={phpsessid}"}
                    async with self._session.post(BASE_URL, data=payload, headers=headers) as login_resp:
                        login_text = await login_resp.text()
                        if "Bejelentkezés" in login_text:
                            _LOGGER.error("Login failed")
                            self._logged_in = False
                            return False
                        self._phpsessid = phpsessid
                        self._logged_in = True
                        _LOGGER.info("Successfully logged in to NGBS iCON cloud")
                        return True
        except Exception as err:
            _LOGGER.error(f"Login error: {err}")
            self._logged_in = False
            return False

    async def async_get_devices(self):
        if not self._logged_in:
            await self.async_login()
        try:
            headers = {"Cookie": f"PHPSESSID={self._phpsessid}"}
            async with async_timeout.timeout(10):
                async with self._session.get(f"{BASE_URL}/Ax?action=iconList", headers=headers) as resp:
                    data = await resp.json()
                    return data["ICONS"][self._icon_id]["DP"]
        except Exception as err:
            _LOGGER.error(f"Device fetch error: {err}")
            return []

    async def async_set_thermostat_attr(self, device_id, attr, value):
        if not self._logged_in:
            await self.async_login()
        try:
            headers = {"Cookie": f"PHPSESSID={self._phpsessid}"}
            payload = {
                "action": "setThermostat",
                "icon": self._icon_id,
                "thermostat": device_id,
                "attr": attr,
                "value": value
            }
            async with async_timeout.timeout(10):
                async with self._session.post(f"{BASE_URL}/Ax", data=payload, headers=headers) as resp:
                    return resp.status == 200
        except Exception as err:
            _LOGGER.error(f"Set attribute error: {err}")
            return False

    async def async_periodic_refresh(self):
        while True:
            await self.async_login()
            await asyncio.sleep(SESSION_REFRESH_INTERVAL)