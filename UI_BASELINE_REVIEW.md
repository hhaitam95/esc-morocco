# UI Baseline

The frontend is intentionally isolated from backend data loading.

## UI features currently enabled

- Language switching
- English / French / Arabic translations
- Participant Country selector
- Participant Country translated names
- Participant Country search UI
- Active opportunity status card
- Search
- Country filter
- Type filter
- Sorting
- Refresh button
- Recently expired section
- NEW opportunity badges
- Light / dark theme
- Responsive mobile layout
- Mobile language dropdown positioning

## Backend

Backend loading is disabled in the frontend.

The future backend is isolated behind:

`web/data-provider.js`

Existing backend files, scraper files, data files and checkpoints are
intentionally preserved.

## Next step

Implement the backend independently, then connect it through
`web/data-provider.js`.
