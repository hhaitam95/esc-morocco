# ESC Opportunity Finder — Language Switch Participant Country Fix

## Change

Fixed the frontend language-switch state handling.

When a Participant Country is selected and applied, switching between
English, French, and Arabic now preserves the selected country and the
already-filtered active opportunity results.

## Behavior

Before:

1. Select Participant Country.
2. Apply search.
3. Active table shows filtered opportunities.
4. Switch language.
5. Active table was cleared and showed an incorrect loading/error state.

After:

1. Select Participant Country.
2. Apply search.
3. Active table shows filtered opportunities.
4. Switch language.
5. The same filtered opportunities remain visible.
6. Labels, dates, country names, buttons, and other translated UI
   update to the selected language.
7. Recently Expired continues to refresh independently.

## Preserved

No changes to:

- Backend data
- Scraper
- Checkpoint
- GitHub Actions
- Participant Country list
- Participant Country filtering logic
- Recently Expired filtering
- Recently Expired ordering
- Recently Expired table markup
- Active table markup
- Logos
- Country flags
- View buttons

## Validation

- update.py syntax validated
- dataset validated
- opportunity 53577 validated
- web/app.js syntax validated
- Recently Expired renderer validated
- language-switch handler validated
- Participant Country state preservation validated
- protected backend/cache files preserved
