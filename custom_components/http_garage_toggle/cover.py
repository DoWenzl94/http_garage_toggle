from __future__ import annotations
import logging
from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_call_later

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
        # Wir nehmen das gleiche Intervall als angenommene Fahrzeit
        motion_time=int(data["coordinator"].update_interval.total_seconds()),
    )
    async_add_entities([entity])


class HttpGarageCover(CoordinatorEntity, CoverEntity):
    _attr_device_class = "garage"
    # 1) STOP ist entfernt → Button erscheint nicht mehr
    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    def __init__(self, name, coordinator, session, base_url, toggle_path, auth, motion_time) -> None:
        super().__init__(coordinator)
        self._attr_name = name
        self._session = session
        self._base_url = base_url
        self._toggle_path = toggle_path
        self._auth = auth
        self._attr_unique_id = f"{base_url}_garage"

        # 2) Fallback-Logik / Bewegungsanzeige
        self._last_state: str | None = None  # "OPEN" oder "CLOSED"
        self._is_opening = False
        self._is_closing = False
        self._motion_time = motion_time
        self._motion_handle = None

    # ---------- Zustände für die UI ----------
    @property
    def is_closed(self) -> bool | None:
        status = (self.coordinator.data or "").upper()
        if status in ("OPEN", "CLOSED"):
            self._last_state = status  # letzten validen Status merken
            return status == "CLOSED"

        # Kein valider Live-Status → auf letzten bekannten Zustand zurückfallen
        if self._last_state in ("OPEN", "CLOSED"):
            return self._last_state == "CLOSED"
        return None

    @property
    def is_opening(self) -> bool:
        return self._is_opening

    @property
    def is_closing(self) -> bool:
        return self._is_closing

    # ---------- Helper ----------
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

        # Direkt danach Status neu laden
        await self.coordinator.async_request_refresh()

    def _start_motion(self, opening: bool) -> None:
        # Anzeige „öffnet…/schließt…“ für die angenommene Fahrzeit
        self._is_opening = opening
        self._is_closing = not opening
        self.async_write_ha_state()

        # ggf. alten Timer abbrechen
        if self._motion_handle:
            self._motion_handle()  # cancel

        def _finish_motion(_now):
            self._is_opening = False
            self._is_closing = False
            # Falls bis dahin noch kein echter Status vorliegt, plausiblen Endzustand setzen
            if (self.coordinator.data or "").upper() not in ("OPEN", "CLOSED"):
                self._last_state = "OPEN" if opening else "CLOSED"
            self.async_write_ha_state()

        self._motion_handle = async_call_later(self.hass, self._motion_time, _finish_motion)

    # ---------- Aktionen ----------
    async def async_open_cover(self, **kwargs) -> None:
        self._start_motion(opening=True)
        await self._send_toggle()

    async def async_close_cover(self, **kwargs) -> None:
        self._start_motion(opening=False)
        await self._send_toggle()
