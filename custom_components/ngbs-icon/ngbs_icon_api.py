import asyncio
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

    async def async_login(self):
        """Log in to the NGBS iCON cloud service."""
        try:
            async with async_timeout.timeout(15):
                # Get login page and extract token
                async with self._session.get(BASE_URL) as resp:
                    if resp.status != 200:
                        _LOGGER.error(
                            "Failed to load login page: status %s", resp.status
                        )
                        self._logged_in = False
                        return False

                    text = await resp.text()
                    soup = BeautifulSoup(text, "html.parser")
                    token_tag = soup.find("input", {"name": "token"})
                    if not token_tag:
                        _LOGGER.error("Token input not found on login page")
                        self._logged_in = False
                        return False

                    token = token_tag.get("value")

                    # Post login credentials
                    payload = {
                        "username": self._username,
                        "password": self._password,
                        "token": token,
                        "x-email": "",
                    }

                    async with self._session.post(BASE_URL, data=payload) as login_resp:
                        if login_resp.status != 200:
                            _LOGGER.error(
                                "Login request failed: status %s", login_resp.status
                            )
                            self._logged_in = False
                            return False

                        login_text = await login_resp.text()
                        # Check if login failed (login page still shows "Bejelentkezés")
                        if "Bejelentkezés" in login_text:
                            _LOGGER.error("Login failed: Invalid credentials")
                            self._logged_in = False
                            return False

                        self._logged_in = True
                        _LOGGER.info("Successfully logged in to NGBS iCON cloud")
                        return True
        except asyncio.TimeoutError:
            _LOGGER.error("Login timeout")
            self._logged_in = False
            return False
        except Exception as err:
            _LOGGER.error("Login error: %s", err)
            self._logged_in = False
            return False

    async def async_get_devices(self):
        """Fetch device data from the NGBS iCON cloud service."""
        if not self._logged_in:
            if not await self.async_login():
                _LOGGER.error("Cannot fetch devices: login failed")
                return []

        try:
            async with async_timeout.timeout(10):
                async with self._session.get(f"{BASE_URL}/Ax?action=iconList") as resp:
                    if resp.status != 200:
                        _LOGGER.error("Failed to fetch devices: status %s", resp.status)
                        # Try re-login on auth failure
                        if resp.status == 401 or resp.status == 403:
                            self._logged_in = False
                            if await self.async_login():
                                return await self.async_get_devices()
                        return []

                    data = await resp.json()

                    if "ICONS" not in data or self._icon_id not in data["ICONS"]:
                        _LOGGER.error("iCON ID %s not found in response", self._icon_id)
                        return []

                    devices = data["ICONS"][self._icon_id].get("DP", [])
                    # Extract is_winter flag from CON_VALUE (global setting)
                    con_value = data["ICONS"][self._icon_id].get("CON_VALUE", 0)
                    is_winter = (
                        con_value == 0
                    )  # 0 = heating (winter), 1 = cooling (summer)

                    # Enhance each device with additional properties
                    for device in devices:
                        device["is_winter"] = is_winter
                        # Ensure OUT, RH, and CE properties are included with defaults
                        device.setdefault("OUT", 0)
                        device.setdefault("RH", None)
                        device.setdefault("CE", 0)

                    return devices
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout fetching devices")
            return []
        except Exception as err:
            _LOGGER.error("Device fetch error: %s", err)
            return []

    async def async_set_thermostat_attr(self, device_id, attr, value):
        """Set a thermostat attribute."""
        if not self._logged_in:
            if not await self.async_login():
                _LOGGER.error("Cannot set attribute: login failed")
                return False

        try:
            payload = {
                "action": "setThermostat",
                "icon": self._icon_id,
                "thermostat": device_id,
                "attr": attr,
                "value": value,
            }
            async with async_timeout.timeout(10):
                async with self._session.post(f"{BASE_URL}/Ax", data=payload) as resp:
                    if resp.status == 200:
                        return True

                    _LOGGER.error(
                        "Failed to set attribute %s: status %s", attr, resp.status
                    )
                    # Try re-login on auth failure
                    if resp.status == 401 or resp.status == 403:
                        self._logged_in = False
                        if await self.async_login():
                            return await self.async_set_thermostat_attr(
                                device_id, attr, value
                            )
                    return False
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout setting attribute %s", attr)
            return False
        except Exception as err:
            _LOGGER.error("Set attribute error: %s", err)
            return False
