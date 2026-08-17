# ESC Opportunity Finder — Production Review

## Recently Expired

The Recently expired table now copies the active opportunity table style.

Final column order:

Opportunity | Location | Activity | Deadline | Type | Expired | View

The only additional column is `Expired`.

Recently expired records are restricted to the selected Participant Country using `eligible_countries`.

Rows retain logo, location/country rendering, activity, deadline, type, and View markup.

## Safety

- Current opportunities: 657
- Opportunity 53577 integrity validated.
- Protected backend/cache files remain untouched.
- Local repair checkpoint remains untouched.
- Archive data is read-only during this update.

## Working Tree

- ` M update.py`
- ` M web/app.js`
- ` M web/index.html`
- `?? data/full_detail_repair_checkpoint.json`

## Canonical Remote

https://github.com/hhaitam95/esc-opportunity-finder.git
