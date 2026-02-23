"""Coordinator for ZenQuotes Tools."""
from __future__ import annotations

import logging
import random
import re
import html as html_lib
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ZEN_QUOTES_BATCH_URL = "https://zenquotes.io/api/quotes"
ON_THIS_DAY_URL_FMT = "https://today.zenquotes.io/api/{month}/{day}"

STORE_VERSION = 1
STORE_KEY = f"{DOMAIN}.cache"


def _bullet_markdown(items: list[str]) -> str:
    return "\n".join([f"- {i}" for i in items])


class ZenQuotesToolsCoordinator(DataUpdateCoordinator):
    """Handles fetching quotes and on-this-day data. Translation is separate."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.hass = hass
        self.store = Store(hass, STORE_VERSION, f"{STORE_KEY}.{entry.entry_id}")
        self._unsub_midnight = None
        self.translation_coordinator: ZenQuotesTranslationCoordinator | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,
        )

    def _opts(self) -> dict:
        return dict(self.entry.options)

    async def async_initialize(self) -> None:
        cached = await self.store.async_load()
        if cached:
            self.data = cached

        self._unsub_midnight = async_track_time_change(
            self.hass, self._handle_midnight, hour=0, minute=0, second=0
        )

        if not self._is_cache_for_today():
            await self.async_request_refresh()
        else:
            await self.async_randomize("both", save=False)
            # Cache exists for today — trigger translation if enabled but missing
            self.hass.async_create_task(self._async_maybe_translate_on_startup())

    async def _async_maybe_translate_on_startup(self) -> None:
        """Trigger translation at startup if enabled but translations are missing."""
        opts = self._opts()
        if not bool(opts.get("translation_enabled", False)):
            return
        if not self.translation_coordinator:
            return
        data = self.data or {}
        # Only translate if we have content but no translations yet
        has_content = bool(data.get("quotes") or data.get("on_this_day_all"))
        missing_translation = not data.get("quotes_translated") and not data.get("on_this_day_translated")
        if has_content and missing_translation:
            _LOGGER.debug("ZenQuotes: triggering translation on startup (cache present, translations missing)")
            await self.translation_coordinator.async_translate()

    def async_shutdown(self) -> None:
        if self._unsub_midnight:
            self._unsub_midnight()
            self._unsub_midnight = None

    async def _handle_midnight(self, now: datetime) -> None:
        await self.async_request_refresh()

    def _is_cache_for_today(self) -> bool:
        if not self.data or not isinstance(self.data, dict):
            return False
        last_update = self.data.get("last_update_local_date")
        today = dt_util.now().date().isoformat()
        return last_update == today

    async def _async_update_data(self) -> dict:
        opts = self._opts()
        quotes_enabled = bool(opts.get("quotes_enabled", True))
        quotes_count = int(opts.get("quotes_count", 10))
        on_enabled = bool(opts.get("on_this_day_enabled", True))
        on_count = int(opts.get("on_this_day_count", 10))

        session = async_get_clientsession(self.hass)

        data: dict = {
            "generated_at": dt_util.now().isoformat(),
            "last_update_local_date": dt_util.now().date().isoformat(),
            "quotes": [],
            "quotes_markdown": "",
            "on_this_day_all": [],
            "on_this_day_markdown": "",
            "random_quote": None,
            "random_on_this_day": None,
            # Translations reset on each fetch — translation coordinator fills them in
            "quotes_translated": None,
            "quotes_translated_markdown": None,
            "on_this_day_translated": None,
            "on_this_day_translated_markdown": None,
            "random_quote_translated": None,
            "random_on_this_day_translated": None,
            "attribution": "Data by ZenQuotes (zenquotes.io) and OnThisDay (today.zenquotes.io)",
        }

        try:
            # --- Quotes ---
            if quotes_enabled:
                resp = await session.get(ZEN_QUOTES_BATCH_URL, timeout=30)
                resp.raise_for_status()
                payload = await resp.json()

                all_quotes = []
                for item in payload or []:
                    q = str(item.get("q", "")).strip()
                    a = str(item.get("a", "")).strip()
                    if not q:
                        continue
                    all_quotes.append((q, a))

                if not all_quotes:
                    raise UpdateFailed("ZenQuotes returned no quotes")

                pick = random.sample(all_quotes, k=min(quotes_count, len(all_quotes)))
                quotes_out = [f"\"{q}\" - {a}" if a else f"\"{q}\"" for (q, a) in pick]
                data["quotes"] = quotes_out
                data["quotes_markdown"] = _bullet_markdown(quotes_out)
                data["_quotes_raw"] = [{"q": q, "a": a} for (q, a) in pick]

            # --- On This Day ---
            if on_enabled:
                now = dt_util.now()
                url = ON_THIS_DAY_URL_FMT.format(month=now.month, day=now.day)

                resp = await session.get(url, timeout=30)
                resp.raise_for_status()
                payload = await resp.json()

                merged: list[str] = []
                groups = (payload or {}).get("data", {}) or {}

                for cat in ("Events", "Births", "Deaths"):
                    for it in groups.get(cat, []) or []:
                        t = str(it.get("text", "")).strip()
                        if not t:
                            continue
                        t = html_lib.unescape(t)
                        merged.append(t)

                if not merged:
                    raise UpdateFailed("OnThisDay returned no items")

                pick_on = random.sample(merged, k=min(on_count, len(merged)))
                data["on_this_day_all"] = pick_on
                data["on_this_day_markdown"] = _bullet_markdown(pick_on)

            # --- Random picks ---
            await self._ensure_random(data, save=False)

            # --- Persist (without private keys) ---
            persist = {k: v for k, v in data.items() if not k.startswith("_")}
            await self.store.async_save(persist)

            # --- Trigger translation in background if enabled ---
            translation_enabled = bool(opts.get("translation_enabled", False))
            _LOGGER.debug(
                "ZenQuotes post-fetch: translation_enabled=%s coordinator=%s opts=%s",
                translation_enabled,
                self.translation_coordinator is not None,
                opts,
            )
            if translation_enabled and self.translation_coordinator:
                _LOGGER.debug("ZenQuotes: scheduling translation task")
                self.hass.async_create_task(
                    self.translation_coordinator.async_translate(data)
                )
            else:
                _LOGGER.debug(
                    "ZenQuotes: translation skipped (enabled=%s coordinator=%s)",
                    translation_enabled,
                    self.translation_coordinator is not None,
                )

            return persist

        except UpdateFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Failed to fetch ZenQuotes data: {err}") from err

    async def _ensure_random(self, data: dict, save: bool) -> None:
        quotes = data.get("quotes") or []
        on_items = data.get("on_this_day_all") or []

        if quotes and not data.get("random_quote"):
            data["random_quote"] = random.choice(quotes)
        if on_items and not data.get("random_on_this_day"):
            data["random_on_this_day"] = random.choice(on_items)

        if save:
            persist = {k: v for k, v in data.items() if not k.startswith("_")}
            await self.store.async_save(persist)

    async def async_randomize(self, target: str = "both", save: bool = True) -> None:
        if not isinstance(self.data, dict):
            return

        new_data = dict(self.data)

        if target in ("quotes", "both"):
            quotes = new_data.get("quotes") or []
            if quotes:
                new_data["random_quote"] = random.choice(quotes)
                if new_data.get("quotes_translated"):
                    try:
                        idx = quotes.index(new_data["random_quote"])
                        new_data["random_quote_translated"] = new_data["quotes_translated"][idx]
                    except Exception:
                        new_data["random_quote_translated"] = None

        if target in ("on_this_day", "both"):
            on_items = new_data.get("on_this_day_all") or []
            if on_items:
                new_data["random_on_this_day"] = random.choice(on_items)
                if new_data.get("on_this_day_translated"):
                    try:
                        idx = on_items.index(new_data["random_on_this_day"])
                        new_data["random_on_this_day_translated"] = new_data["on_this_day_translated"][idx]
                    except Exception:
                        new_data["random_on_this_day_translated"] = None

        new_data["randomized_at"] = dt_util.now().isoformat()

        if save:
            await self.store.async_save(new_data)

        self.async_set_updated_data(new_data)


# ---------------------------------------------------------------------------
# Translation coordinator — fully independent, manages its own state
# ---------------------------------------------------------------------------

class ZenQuotesTranslationCoordinator(DataUpdateCoordinator):
    """Manages translation state and execution independently of data fetching."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        data_coordinator: ZenQuotesToolsCoordinator,
    ) -> None:
        self.entry = entry
        self.data_coordinator = data_coordinator
        self.store = Store(hass, STORE_VERSION, f"{STORE_KEY}.translation.{entry.entry_id}")

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_translation",
            update_interval=None,
        )

        self._state: dict = {
            "status": "idle",
            "last_attempt": None,
            "last_success": None,
            "error_message": None,
            "language": None,
        }

    async def async_initialize(self) -> None:
        cached = await self.store.async_load()
        if cached:
            self._state = cached
        self.async_set_updated_data(dict(self._state))

    def _opts(self) -> dict:
        return dict(self.entry.options)

    async def _async_update_data(self) -> dict:
        return self._state

    async def async_translate(self, source_data: dict | None = None) -> None:
        """Run translation task. Call with source_data from refresh, or None to use cached data."""
        opts = self._opts()
        language = str(opts.get("translation_language", "hr"))
        ai_task_entity_id = opts.get("translation_ai_task_entity") or None

        self._state = {
            "status": "translating",
            "last_attempt": dt_util.now().isoformat(),
            "last_success": self._state.get("last_success"),
            "error_message": None,
            "language": language,
        }
        self.async_set_updated_data(dict(self._state))

        try:
            if source_data is None:
                source_data = self.data_coordinator.data or {}

            await self._do_translate(source_data, language, ai_task_entity_id)

            self._state.update({
                "status": "done",
                "last_success": dt_util.now().isoformat(),
                "error_message": None,
            })
        except Exception as err:
            _LOGGER.error("ZenQuotes translation failed: %s", err)
            self._state.update({
                "status": "error",
                "error_message": str(err),
            })
        finally:
            await self.store.async_save(dict(self._state))
            self.async_set_updated_data(dict(self._state))

    async def _do_translate(self, source_data: dict, language: str, ai_task_entity_id: str | None) -> None:
        # Different AI providers expose different service names
        has_generate_data = self.hass.services.has_service("ai_task", "generate_data")
        has_generate_text = self.hass.services.has_service("ai_task", "generate_text")
        if not has_generate_data and not has_generate_text:
            raise RuntimeError("No ai_task service available. Check your AI integration.")
        # Prefer generate_data (Gemini, most providers), fall back to generate_text
        ai_service = "generate_data" if has_generate_data else "generate_text"

        # Rebuild quote raw data if needed (e.g. loaded from cache without _quotes_raw)
        quotes_raw = source_data.get("_quotes_raw") or []
        if not quotes_raw:
            for q_str in source_data.get("quotes") or []:
                if '" - ' in q_str:
                    parts = q_str.split('" - ', 1)
                    quotes_raw.append({"q": parts[0].lstrip('"'), "a": parts[1]})
                else:
                    quotes_raw.append({"q": q_str.strip('"'), "a": ""})

        quote_texts = [str(x.get("q", "")).strip() for x in quotes_raw if str(x.get("q", "")).strip()]
        quote_authors = [str(x.get("a", "")).strip() for x in quotes_raw if str(x.get("q", "")).strip()]
        on_texts = [str(x).strip() for x in (source_data.get("on_this_day_all") or []) if str(x).strip()]

        if not quote_texts and not on_texts:
            _LOGGER.warning("ZenQuotes: nothing to translate")
            return

        # Build a clear numbered prompt that any LLM can handle
        sections: list[str] = []
        if quote_texts:
            lines = "\n".join(f"{i+1}. {t}" for i, t in enumerate(quote_texts))
            sections.append(f"QUOTES:\n{lines}")
        if on_texts:
            lines = "\n".join(f"{i+1}. {t}" for i, t in enumerate(on_texts))
            sections.append(f"ON THIS DAY:\n{lines}")

        prompt = (
            f"Translate the following items into the language with code '{language}'.\n"
            "Rules:\n"
            "- Return ONLY the translations, numbered exactly as shown, preserving section headers.\n"
            "- Keep years, numbers, proper names, and place names unchanged.\n"
            "- Do not add any commentary or extra text.\n\n"
            + "\n\n".join(sections)
        )

        _LOGGER.debug("ZenQuotes translation prompt:\n%s", prompt)

        service_data: dict = {
            "task_name": f"{DOMAIN}_translate",
            "instructions": prompt,
        }
        if ai_task_entity_id:
            service_data["entity_id"] = ai_task_entity_id

        resp = await self.hass.services.async_call(
            "ai_task",
            ai_service,
            service_data,
            blocking=True,
            return_response=True,
        )

        _LOGGER.debug("ZenQuotes AI Task response: type=%s  value=%s", type(resp), resp)

        raw_text = self._extract_text(resp)
        if not raw_text:
            raise RuntimeError(f"AI Task returned empty response. Full response: {resp!r}")

        _LOGGER.debug("ZenQuotes extracted translation text:\n%s", raw_text)

        parsed_quotes, parsed_on = self._parse_response(raw_text, len(quote_texts), len(on_texts))

        _LOGGER.debug("Parsed quotes (%d): %s", len(parsed_quotes), parsed_quotes)
        _LOGGER.debug("Parsed on_this_day (%d): %s", len(parsed_on), parsed_on)

        # Merge translations into current coordinator data
        current = dict(self.data_coordinator.data or {})

        if parsed_quotes:
            if len(parsed_quotes) == len(quote_texts):
                combined = []
                for t, a in zip(parsed_quotes, quote_authors):
                    t = t.strip()
                    combined.append(f"\"{t}\" - {a}" if a else f"\"{t}\"")
                current["quotes_translated"] = combined
                current["quotes_translated_markdown"] = _bullet_markdown(combined)
            else:
                _LOGGER.warning(
                    "Quote count mismatch: expected %d, got %d. Quotes: %s",
                    len(quote_texts), len(parsed_quotes), parsed_quotes,
                )

        if parsed_on:
            if len(parsed_on) == len(on_texts):
                current["on_this_day_translated"] = parsed_on
                current["on_this_day_translated_markdown"] = _bullet_markdown(parsed_on)
            else:
                _LOGGER.warning(
                    "OnThisDay count mismatch: expected %d, got %d. Items: %s",
                    len(on_texts), len(parsed_on), parsed_on,
                )

        # Update random translated references
        rq = current.get("random_quote")
        if rq and current.get("quotes") and current.get("quotes_translated"):
            try:
                idx = current["quotes"].index(rq)
                current["random_quote_translated"] = current["quotes_translated"][idx]
            except Exception:
                current["random_quote_translated"] = None

        ro = current.get("random_on_this_day")
        if ro and current.get("on_this_day_all") and current.get("on_this_day_translated"):
            try:
                idx = current["on_this_day_all"].index(ro)
                current["random_on_this_day_translated"] = current["on_this_day_translated"][idx]
            except Exception:
                current["random_on_this_day_translated"] = None

        # Save and push update to sensors
        await self.data_coordinator.store.async_save(current)
        self.data_coordinator.async_set_updated_data(current)

    def _extract_text(self, resp: object) -> str:
        """Extract plain text string from various AI Task response shapes."""
        if isinstance(resp, str):
            return resp.strip()
        if isinstance(resp, dict):
            # Try flat keys first
            for key in ("text", "response", "result", "content", "output", "generated_text", "answer"):
                val = resp.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
            # Nested under "data"
            data = resp.get("data")
            if isinstance(data, str) and data.strip():
                return data.strip()
            if isinstance(data, dict):
                for key in ("text", "response", "result", "content"):
                    val = data.get(key)
                    if isinstance(val, str) and val.strip():
                        return val.strip()
        _LOGGER.warning("Could not extract text from AI response: %s", repr(resp))
        return ""

    def _parse_response(self, text: str, n_quotes: int, n_on: int) -> tuple[list[str], list[str]]:
        """Parse numbered response back into two lists matching original counts."""
        lines = text.strip().splitlines()
        quotes_out: list[str] = []
        on_out: list[str] = []

        in_quotes = n_quotes > 0
        in_on = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            upper = stripped.upper()

            # Detect section headers (not numbered lines)
            if not re.match(r"^\d+\.", stripped):
                if "QUOTES" in upper:
                    in_quotes = True
                    in_on = False
                    continue
                if "ON THIS DAY" in upper or "ON_THIS_DAY" in upper:
                    in_quotes = False
                    in_on = True
                    continue

            # Numbered line
            m = re.match(r"^\d+\.\s*(.+)$", stripped)
            if not m:
                continue
            content = m.group(1).strip()

            if in_quotes and len(quotes_out) < n_quotes:
                quotes_out.append(content)
                # Auto-switch to on_this_day after filling quotes
                if len(quotes_out) == n_quotes and n_on > 0:
                    in_quotes = False
                    in_on = True
            elif in_on and len(on_out) < n_on:
                on_out.append(content)

        return quotes_out, on_out