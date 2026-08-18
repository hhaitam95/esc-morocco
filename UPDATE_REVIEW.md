# Phase 5 — Simplified ESC Update Architecture

## Architecture

1. `update.yml` runs every 30 minutes.
2. `update.yml` runs `scraper/scraper.py`.
3. The scraper saves the canonical JSON data under `data/`.
4. `update.yml` commits and pushes changed data to `main`.
5. That push triggers `deploy.yml`.
6. `deploy.yml` deploys the existing `web/` directory to GitHub Pages.

## Important boundary

`update.yml` does not build or deploy the website.

`deploy.yml` is responsible for GitHub Pages deployment.

## Validation

- update.yml: validated
- deploy.yml: validated
- scraper.py: validated
- canonical JSON: validated
- protected repair checkpoint: preserved

## Current Git status

```text
 M .github/workflows/update.yml
 M UPDATE_REVIEW.md
 M update.py
?? .github/workflows/update.yml.phase5-backup
?? data/full_detail_repair_checkpoint.json
```
