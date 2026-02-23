# ZenQuotes Tools for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

`zenquotes_tools` fetches quote content and “on this day” items from ZenQuotes endpoints and exposes them as Home Assistant sensors.

## What this integration does
- Fetches quote batches from `zenquotes.io/api/quotes`
- Fetches daily “on this day” items from `today.zenquotes.io`
- Keeps daily local cache and auto-refreshes at midnight
- Supports random item rotation without new API calls
- Supports optional AI translation via `ai_task`

## Quick start
1. Install via HACS (Custom Repository) or copy manually to `custom_components/zenquotes_tools`.
2. Restart Home Assistant.
3. Add integration: `ZenQuotes Tools`.
4. Configure quote count, on-this-day count, and optional translation.

## Installation
### HACS (recommended)
1. Open HACS.
2. Go to `Integrations`.
3. Open `Custom repositories`.
4. Add this repository as category `Integration`.
5. Install `ZenQuotes Tools`.
6. Restart Home Assistant.

### Manual
1. Copy `custom_components/zenquotes_tools` into your HA `custom_components` directory.
2. Restart Home Assistant.

## Configuration
Use `Configure` on the integration entry to set:
- `quotes_enabled`
- `quotes_count` (1-50)
- `on_this_day_enabled`
- `on_this_day_count` (1-50)
- `translation_enabled`
- `translation_language`
- `translation_ai_task_entity` (optional)

Note:
- The integration is single-instance.

## Entities
- `sensor.zenquotes_tools`
  - main payload (quotes, on-this-day, markdown, translated fields)
- `sensor.zenquotes_random_quote`
  - current random quote
- `sensor.zenquotes_random_on_this_day`
  - current random on-this-day item
- `sensor.zenquotes_translation_status`
  - translation state (`idle|translating|done|error`)

## Services
- `zenquotes_tools.refresh`
  - fetch fresh data from APIs
- `zenquotes_tools.randomize`
  - rotate cached random selection (no API call)
  - `target`: `quotes` | `on_this_day` | `both`
- `zenquotes_tools.translate`
  - trigger AI translation manually

Optional field for all services:
- `entry_id`

## Troubleshooting
- If no data appears, run `zenquotes_tools.refresh` manually.
- If translation fails, verify `ai_task` service and entity selection.
- If API errors persist, check source endpoint availability.

## HACS updates
HACS shows updates when a newer release/tag is published and `manifest.json` version is higher.

Recommended release flow:
1. Bump `custom_components/zenquotes_tools/manifest.json` version.
2. Push to `main`.
3. Publish release/tag `vX.Y.Z`.

## Support
Please use GitHub Issues for bug reports and feature requests.

## Disclaimer

This integration retrieves publicly available data from ZenQuotes endpoints directly from the user's local Home Assistant instance.

This project:

- Is not affiliated with, endorsed by, or connected to `zenquotes.io` or `today.zenquotes.io`
- Does not host, store, cache, or redistribute third-party quote content outside the user's local Home Assistant instance
- Does not operate any proxy, API, or intermediate server
- Only provides a tool that allows end users to fetch data directly from original sources

All content remains the property of its respective copyright holder.

Users are responsible for ensuring that their use of this integration complies with the terms of use of referenced data sources and applicable copyright laws in their jurisdiction.

This integration is intended for personal, non-commercial use only.

If you are the owner of a referenced data source and have concerns about this project, please open an issue or contact the maintainer.
