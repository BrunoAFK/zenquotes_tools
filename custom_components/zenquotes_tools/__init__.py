"""ZenQuotes Tools integration."""
from __future__ import annotations

import logging

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

SERVICE_REFRESH = "refresh"
SERVICE_RANDOMIZE = "randomize"
SERVICE_TRANSLATE = "translate"

SERVICE_SCHEMA_REFRESH = vol.Schema(
    {
        vol.Optional("entry_id"): cv.string,
    }
)

SERVICE_SCHEMA_RANDOMIZE = vol.Schema(
    {
        vol.Optional("entry_id"): cv.string,
        vol.Optional("target", default="both"): vol.In(["quotes", "on_this_day", "both"]),
    }
)

SERVICE_SCHEMA_TRANSLATE = vol.Schema(
    {
        vol.Optional("entry_id"): cv.string,
    }
)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up domain-level services."""

    def _get_entry_data(entry_id: str | None) -> tuple | None:
        """Return (data_coordinator, translation_coordinator) or None."""
        entries = hass.data.get(DOMAIN, {})
        if entry_id:
            entry_data = entries.get(entry_id)
        elif len(entries) == 1:
            entry_data = next(iter(entries.values()))
        else:
            return None
        if entry_data is None:
            return None
        return entry_data

    async def handle_refresh(call: ServiceCall) -> None:
        entry_data = _get_entry_data(call.data.get("entry_id"))
        if not entry_data:
            _LOGGER.warning("No ZenQuotes Tools entry found to refresh")
            return
        data_coordinator, _ = entry_data
        await data_coordinator.async_request_refresh()

    async def handle_randomize(call: ServiceCall) -> None:
        entry_data = _get_entry_data(call.data.get("entry_id"))
        if not entry_data:
            _LOGGER.warning("No ZenQuotes Tools entry found to randomize")
            return
        data_coordinator, _ = entry_data
        target = call.data.get("target", "both")
        await data_coordinator.async_randomize(target)

    async def handle_translate(call: ServiceCall) -> None:
        entry_data = _get_entry_data(call.data.get("entry_id"))
        if not entry_data:
            _LOGGER.warning("No ZenQuotes Tools entry found to translate")
            return
        _, translation_coordinator = entry_data
        if translation_coordinator is None:
            _LOGGER.warning("Translation coordinator not available")
            return
        # Run in background so service call returns immediately
        hass.async_create_task(translation_coordinator.async_translate())

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, handle_refresh, schema=SERVICE_SCHEMA_REFRESH)
    hass.services.async_register(DOMAIN, SERVICE_RANDOMIZE, handle_randomize, schema=SERVICE_SCHEMA_RANDOMIZE)
    hass.services.async_register(DOMAIN, SERVICE_TRANSLATE, handle_translate, schema=SERVICE_SCHEMA_TRANSLATE)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .coordinator import ZenQuotesToolsCoordinator, ZenQuotesTranslationCoordinator

    data_coordinator = ZenQuotesToolsCoordinator(hass, entry)
    translation_coordinator = ZenQuotesTranslationCoordinator(hass, entry, data_coordinator)


    hass.data.setdefault(DOMAIN, {})
    # Store as tuple: (data_coordinator, translation_coordinator)
    hass.data[DOMAIN][entry.entry_id] = (data_coordinator, translation_coordinator)

    # Cross-link so data coordinator can trigger translation after refresh
    data_coordinator.translation_coordinator = translation_coordinator

    # Initialize translation coordinator first (loads cached status)
    await translation_coordinator.async_initialize()

    # Then initialize data coordinator (may trigger translation via async_create_task)
    await data_coordinator.async_initialize()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    entry_data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if entry_data:
        data_coordinator, _ = entry_data
        data_coordinator.async_shutdown()

    if not hass.data.get(DOMAIN):
        hass.data.pop(DOMAIN, None)

    return unload_ok