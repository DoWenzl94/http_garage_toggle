from __future__ import annotations
import logging
import re
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

DOMAIN = "http_garage_toggle"
_LOGGER = logging.getLogger(__name__)

STATUS_REGEX = re.compile(r"Door Status:\s*([A-Za-z]+)", re.IGNORECASE)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one configured garage door."""
    session = async_get_clientsession(hass)

    base_url: str = entry.data["base_url"].rstrip("/")
    status_path: str = entry.data.get("status_path", "/")
    interval = int(entry.data.get("scan_interval", 35))

    # optional BasicAuth
    auth = None
    if entry.data.get("username") and entry.data.get("password"):
        from aiohttp import BasicAuth

        auth = BasicAuth(entry.data["username"], entry.data["password"])

    async def _async_fetch_status() -> str:
        import aiohttp

        try:
            async with session.get(
                f"{base_url}{status_path}",
                auth=auth,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                text = await resp.text()
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Status request failed: {err}") from err

        m = STATUS_REGEX.search(text or "")
        if not m:
            raise UpdateFailed("Could not parse door status from response")
        return m.group(1).upper()

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_coordinator_{entry.entry_id}",
        update_method=_async_fetch_status,
        update_interval=timedelta(seconds=interval),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "session": session,
        "base_url": base_url,
        "toggle_path": entry.data.get("toggle_path", "/?switch=1"),
        "auth": auth,
    }

    # Forward to the cover platform
    await hass.config_entries.async_forward_entry_setups(entry, ["cover"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["cover"])
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
