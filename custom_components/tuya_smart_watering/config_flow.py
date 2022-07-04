"""Configuration via UI for the integration."""

from __future__ import annotations

import logging
from functools import cached_property
from typing import Any

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_ID, CONF_TOKEN, CONF_DEVICE, URL_API, CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def get_value(
    config_entry: config_entries | None, param: str, default: str | None = None
) -> Any:
    """Get current value for configuration parameter.

    :param config_entry: config_entries|None: config entry from Flow
    :param param: str: parameter name for getting value
    :param default: default value for parameter, defaults to None
    :returns: parameter value, or default value or None
    """
    if config_entry is not None:
        config_entry: config_entries
        return config_entry.options.get(param, config_entry.data.get(param, default))

    return default


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """First time set up flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_DEVICE])
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_ID): str,
            vol.Required(CONF_TOKEN): str,
            vol.Required(CONF_DEVICE): str,
            vol.Required(URL_API): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


class OptionsFlow(config_entries.OptionsFlow):
    """Changing options flow."""

    def __init__(self, config_entry: config_entries):
        """Initialize options flow."""
        self.config_entry = config_entry

    @cached_property
    def config(self) -> dict:
        """Return the configuration."""
        config = dict(self.config_entry.data)
        config.update(self.config_entry.options)
        return config

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_NAME, default=self.config.get(CONF_NAME)): str,
            vol.Required(CONF_ID, default=self.config.get(CONF_ID)): str,
            vol.Required(CONF_TOKEN, default=self.config.get(CONF_TOKEN)): str,
            vol.Required(CONF_DEVICE, default=self.config.get(CONF_DEVICE)): str,
            vol.Required(URL_API, default=self.config.get(URL_API)): str,
            vol.Required(CONF_USERNAME, default=self.config.get(CONF_USERNAME)): str,
            vol.Required(CONF_PASSWORD, default=self.config.get(CONF_PASSWORD)): str,
        })
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )
