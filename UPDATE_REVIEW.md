# ESC Opportunity Finder — Production Review

## Live Country Filter Fix

Patched the actual `populateFilters()` function used to populate `#country-filter`.

The live renderer now:

- keeps ISO codes as option values;
- displays country flags;
- displays human-readable country names;
- uses `Intl.DisplayNames` as a fallback;
- removes the legacy `🌍 + ISO` rendering.

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
