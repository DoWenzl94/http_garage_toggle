from __future__ import annotations
import logging

from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    entity = HttpGarageCover(
        name=entry.title or "Garage Door",
        coordinator=data["coordinator"],
        session=data["session"],
        base_url=data["base_url"],
        toggle_path=data["toggle_path"],
        auth=data["auth"],
    )
    async_add_entities([entity])


class HttpGarageCover(CoordinatorEntity, CoverEntity):
    _attr_device_class = "garage"
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
    )

    def __init__(self, name, coordinator, session, base_url, toggle_path, auth) -> None:
        super().__init__(coordinator)
        self._attr_name = name
        self._session = session
        self._base_url = base_url
        self._toggle_path = toggle_path
        self._auth = auth
        self._attr_unique_id = f"{base_url}_garage"

    @property
    def is_closed(self) -> bool | None:
        status = (self.coordinator.data or "").upper()
        if status in ("OPEN", "CLOSED"):
            return status == "CLOSED"
        return None

    async def _send_toggle(self) -> None:
        import aiohttp

        try:
            async with self._session.get(
                f"{self._base_url}{self._toggle_path}",
                auth=self._auth,
                timeout=aiohttp.ClientTimeout(total=10),
            ):
                pass
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Toggle request failed: %s", err)
            raise
        # kurz danach Status neu laden
        await self.coordinator.async_request_refresh()

    async def async_open_cover(self, **kwargs) -> None:
        await self._send_toggle()

    async def async_close_cover(self, **kwargs) -> None:
        await self._send_toggle()

    async def async_stop_cover(self, **kwargs) -> None:
        await self._send_toggle()
