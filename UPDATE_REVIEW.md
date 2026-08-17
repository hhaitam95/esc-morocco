# ESC Opportunity Finder — Country Dropdown Flag Repair

## Scope

Frontend-only production update.

### Changes being pushed

- Restore correct country flags in the Participant Country dropdown.
- Restore correct country flags in the destination Country filter.
- Preserve the existing country names and translations.
- Continue using stable country-code values.
- Use the shared country-code flag resolver.
- Remove the generic globe fallback from the affected country dropdown renderers.

### Validation

- `web/app.js` passes Node syntax validation.
- `web/opportunities.json` remains unchanged.
- Opportunity `53577` remains intact.
- Backend/cache files are not included in the commit.
- `data/full_detail_repair_checkpoint.json` remains local and untouched.

## Files intentionally committed

- `web/app.js`
- `UPDATE_REVIEW.md`

## Files intentionally excluded

- `update.py`
- `data/full_detail_repair_checkpoint.json`
- `data/checkpoint.json`
- `data/expired.json`
- `data/opportunities.json`
- `web/opportunities.json`

## Production push

The commit is intended to be pushed to `origin/main`.

No network scraping is performed by this update.
