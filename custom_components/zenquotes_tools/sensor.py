from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    data_coordinator, translation_coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ZenQuotesToolsMainSensor(data_coordinator, entry),
            ZenQuotesToolsRandomQuoteSensor(data_coordinator, entry),
            ZenQuotesToolsRandomOnThisDaySensor(data_coordinator, entry),
            ZenQuotesTranslationStatusSensor(translation_coordinator, entry),
        ]
    )


class ZenQuotesToolsBaseSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.entry = entry


class ZenQuotesToolsMainSensor(ZenQuotesToolsBaseSensor):
    _attr_name = "ZenQuotes Tools"
    _attr_unique_id = "zenquotes_tools_main"

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        return data.get("generated_at")

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        return {k: v for k, v in data.items() if not k.startswith("_")}


class ZenQuotesToolsRandomQuoteSensor(ZenQuotesToolsBaseSensor):
    _attr_name = "ZenQuotes Random Quote"
    _attr_unique_id = "zenquotes_tools_random_quote"

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        return data.get("randomized_at") or data.get("generated_at")

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        return {
            "text": data.get("random_quote"),
            "text_translated": data.get("random_quote_translated"),
            "attribution": data.get("attribution"),
        }


class ZenQuotesToolsRandomOnThisDaySensor(ZenQuotesToolsBaseSensor):
    _attr_name = "ZenQuotes Random On This Day"
    _attr_unique_id = "zenquotes_tools_random_on_this_day"

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        return data.get("randomized_at") or data.get("generated_at")

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        return {
            "text": data.get("random_on_this_day"),
            "text_translated": data.get("random_on_this_day_translated"),
            "attribution": data.get("attribution"),
        }


class ZenQuotesTranslationStatusSensor(ZenQuotesToolsBaseSensor):
    """Shows translation status: idle / translating / done / error."""

    _attr_name = "ZenQuotes Translation Status"
    _attr_unique_id = "zenquotes_tools_translation_status"

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        return data.get("status", "idle")

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        return {
            "last_attempt": data.get("last_attempt"),
            "last_success": data.get("last_success"),
            "error_message": data.get("error_message"),
            "language": data.get("language"),
        }

    @property
    def icon(self):
        status = self.native_value
        return {
            "idle": "mdi:translate-off",
            "translating": "mdi:translate",
            "done": "mdi:check-circle",
            "error": "mdi:alert-circle",
        }.get(status, "mdi:translate")