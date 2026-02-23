# ZenQuotes Tools for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

`zenquotes_tools` dohvaća citate i "on this day" činjenice sa ZenQuotes izvora i izlaže ih kroz senzore u Home Assistantu.

## Što integracija radi
- Dohvaća batch citata (`zenquotes.io/api/quotes`)
- Dohvaća "on this day" stavke (`today.zenquotes.io`)
- Drži dnevni cache i automatski refresh na ponoć
- Omogućuje ručni random pick bez API poziva
- Opcionalno prevodi sadržaj preko `ai_task`

## Instalacija
### HACS (preporučeno)
1. Otvori HACS.
2. Idi na `Integrations`.
3. `Custom repositories` -> dodaj ovaj repo kao `Integration`.
4. Instaliraj `ZenQuotes Tools`.
5. Restartaj Home Assistant.

### Manual
1. Kopiraj `custom_components/zenquotes_tools` u HA `custom_components` direktorij.
2. Restartaj Home Assistant.

## Konfiguracija
1. `Settings` -> `Devices & Services` -> `Add Integration`.
2. Odaberi `ZenQuotes Tools`.
3. Kroz `Configure` podešavaš opcije:
   - `quotes_enabled`
   - `quotes_count` (1-50)
   - `on_this_day_enabled`
   - `on_this_day_count` (1-50)
   - `translation_enabled`
   - `translation_language`
   - `translation_ai_task_entity` (opcionalno)

Napomena:
- Integracija je `single instance`.

## Entiteti
- `sensor.zenquotes_tools`
  - glavni payload (liste citata i on-this-day podataka, markdown, translation polja)
- `sensor.zenquotes_random_quote`
  - trenutno random odabran citat
- `sensor.zenquotes_random_on_this_day`
  - trenutno random odabrana on-this-day stavka
- `sensor.zenquotes_translation_status`
  - status prijevoda (`idle|translating|done|error`)

## Servisi
- `zenquotes_tools.refresh`
  - osvježi podatke s API-ja
- `zenquotes_tools.randomize`
  - promijeni random odabir iz cachea (bez API poziva)
  - `target`: `quotes` | `on_this_day` | `both`
- `zenquotes_tools.translate`
  - ručno pokreni AI prijevod

Opcionalno za sve servise:
- `entry_id`

## Atributi i payload
Glavni senzor uključuje, između ostalog:
- `quotes`
- `quotes_markdown`
- `on_this_day_all`
- `on_this_day_markdown`
- `random_quote`
- `random_on_this_day`
- prevedene varijante (`*_translated`)
- `attribution`

## Ograničenja
- Podaci ovise o vanjskim API servisima.
- Ako `ai_task` servis nije dostupan, prijevod neće raditi.

## HACS update flow
HACS prikazuje update kada postoji novi release/tag i veći `manifest.json` `version`.

Preporučeni flow:
1. Povećaj `custom_components/zenquotes_tools/manifest.json` -> `version`.
2. Merge/push na `main`.
3. Objavi release/tag `vX.Y.Z`.

## Podrška
Bugove i feature requestove prijavi kroz GitHub Issues.

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
