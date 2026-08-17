# ESC Opportunity Finder — Phase 1 Baseline

Baseline captured:

`2026-08-17T13:06:14.340943+00:00`

## Purpose

Phase 1 is validation-only. No scraper, cache, checkpoint,
frontend, or workflow functionality is intentionally changed.

## Repository

- Branch: `main`
- Remote: `https://github.com/hhaitam95/esc-opportunity-finder.git`
- Local commits ahead: `0`
- Remote commits ahead: `14`

## Current opportunity dataset

- `data/opportunities.json`: **745 opportunities**
- Unique opportunity IDs: **745**
- `generated_at`: `2026-08-17T02:08:59.215314`
- Opportunity `53577`: **present**

## Current expired dataset

- `data/expired.json`: **30 records**

## Current checkpoint

- `data/checkpoint.json` processed IDs:
  **1258**

## Duplicate opportunity JSON

### `web/opportunities.json`

- Exists: **True**
- Byte-identical to `data/opportunities.json`:
  **True**
- Same opportunity IDs:
  **True**

### `web/expired.json`

- Exists: **True**
- Byte-identical to `data/expired.json`:
  **True**
- Same expired opportunity IDs:
  **True**

## Workflow inventory

- `update.yml`: **True**
- `scrape.yml`: **True**
- `deploy.yml`: **True**
- `update.yml schedules`:
  **17,47 * * * ***

## Validated files

- `scraper/scraper.py`
- `web/app.js`
- `web/index.html`
- `.github/workflows/update.yml`
- `.github/workflows/scrape.yml` if present
- `.github/workflows/deploy.yml`

## Phase 1 result

Baseline successfully captured.

No functional application change was performed.
