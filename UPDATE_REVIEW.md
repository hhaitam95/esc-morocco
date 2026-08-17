# ESC Opportunity Finder — Production Review

## Country Filter Fix

The main `#country-filter` was changed from labels such as:

`🌍 DE`

to human-readable labels such as:

`🇩🇪 Germany`

The underlying option value remains the ISO country code, for example `DE`.

The implementation does not depend on `Intl.DisplayNames` or the existing country metadata implementation.

## Validated Countries

- 🇩🇪 Germany
- 🇮🇹 Italy
- 🇱🇹 Lithuania
- 🇵🇹 Portugal
- 🇷🇴 Romania
- 🇸🇰 Slovakia
- 🇹🇷 Türkiye

## Dataset Safety

- Current opportunities: 657
- Opportunity 53577 integrity validated.
- Backend/cache files were not modified.
- Local repair checkpoint was preserved.

## Working Tree

- ` M update.py`
- ` M web/app.js`
- `?? data/full_detail_repair_checkpoint.json`

## Canonical Remote

https://github.com/hhaitam95/esc-opportunity-finder.git
