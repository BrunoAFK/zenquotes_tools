from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    DEFAULT_QUOTES_ENABLED,
    DEFAULT_QUOTES_COUNT,
    DEFAULT_ON_THIS_DAY_ENABLED,
    DEFAULT_ON_THIS_DAY_COUNT,
    DEFAULT_TRANSLATION_ENABLED,
    DEFAULT_TRANSLATION_LANGUAGE,
    DEFAULT_TRANSLATION_AI_TASK_ENTITY,
)


class ZenQuotesToolsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(
            title="ZenQuotes Tools",
            data={},
            options={
                "quotes_enabled": DEFAULT_QUOTES_ENABLED,
                "quotes_count": DEFAULT_QUOTES_COUNT,
                "on_this_day_enabled": DEFAULT_ON_THIS_DAY_ENABLED,
                "on_this_day_count": DEFAULT_ON_THIS_DAY_COUNT,
                "translation_enabled": DEFAULT_TRANSLATION_ENABLED,
                "translation_language": DEFAULT_TRANSLATION_LANGUAGE,
                "translation_ai_task_entity": DEFAULT_TRANSLATION_AI_TASK_ENTITY,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ZenQuotesToolsOptionsFlowHandler()


class ZenQuotesToolsOptionsFlowHandler(config_entries.OptionsFlowWithReload):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        opt = self.config_entry.options

        schema = vol.Schema(
            {
                vol.Required("quotes_enabled", default=opt.get("quotes_enabled", DEFAULT_QUOTES_ENABLED)): bool,
                vol.Required("quotes_count", default=opt.get("quotes_count", DEFAULT_QUOTES_COUNT)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=50)
                ),
                vol.Required("on_this_day_enabled", default=opt.get("on_this_day_enabled", DEFAULT_ON_THIS_DAY_ENABLED)): bool,
                vol.Required("on_this_day_count", default=opt.get("on_this_day_count", DEFAULT_ON_THIS_DAY_COUNT)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=50)
                ),
                vol.Required("translation_enabled", default=opt.get("translation_enabled", DEFAULT_TRANSLATION_ENABLED)): bool,
                vol.Required(
                    "translation_language",
                    default=opt.get("translation_language", DEFAULT_TRANSLATION_LANGUAGE),
                ): selector.LanguageSelector(),
                vol.Optional(
                    "translation_ai_task_entity",
                    default=opt.get("translation_ai_task_entity", DEFAULT_TRANSLATION_AI_TASK_ENTITY),
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="ai_task")),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
