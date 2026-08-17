# ESC Opportunity Finder — Safe Frontend Production Push

## Scope

This update pushes only the validated frontend changes.

Protected backend/cache files are intentionally excluded.

## Protected files

- `data/checkpoint.json`
- `data/expired.json`
- `data/opportunities.json`
- `web/opportunities.json`
- `data/full_detail_repair_checkpoint.json`

## Validation

- Current production cache: 657 opportunities
- Opportunity 53577 present
- Opportunity 53577 activity start: 2026-09-28
- Opportunity 53577 activity end: 2026-11-01
- Opportunity 53577 application deadline: 2026-08-20
- Opportunity 53577 country: TR
- Opportunity 53577 town: TANDOGAN ANKARA
- Opportunity 53577 activity type: Individual volunteering
- `web/app.js` passes Node syntax validation
- Cached opportunity loading validated
- Refresh behavior validated
- Participant-search state validated
- Activity-date compatibility validated
- Deadline compatibility validated
- Logo compatibility validated
- Location compatibility validated
- Country flag mapping validated

## Push scope

Only these files may be staged by this script:

- `web/app.js`
- `UPDATE_REVIEW.md`

`update.py` itself is deliberately left unstaged.
