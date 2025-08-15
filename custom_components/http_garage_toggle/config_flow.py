from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries

from . import DOMAIN


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            title = user_input["base_url"]
            await self.async_set_unique_id(title)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=title, data=user_input)

        schema = vol.Schema(
            {
                vol.Required("base_url", default="http://192.168.1.xxx"): str,
                vol.Optional("toggle_path", default="/?switch=1"): str,
                vol.Optional("status_path", default="/"): str,
                vol.Optional("scan_interval", default=35): int,
                vol.Optional("username"): str,
                vol.Optional("password"): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
