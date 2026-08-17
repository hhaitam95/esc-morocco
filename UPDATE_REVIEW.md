# ESC Opportunity Finder — Phase 2 Production Review

## Objective

Simplify the backend architecture so there is one scraper workflow and one canonical opportunity dataset.

## Baseline

- Canonical opportunities before migration: **1111**
- Expired opportunities: **30**
- generated_at: `2026-08-17T10:21:03.741260`

## Architecture after migration

- `.github/workflows/update.yml` = only scraper/update workflow
- `.github/workflows/deploy.yml` = only Pages deployment workflow
- `data/opportunities.json` = canonical opportunity dataset
- `data/expired.json` = canonical expired dataset
- `data/checkpoint.json` = scraper progress
- `web/data-provider.js` = frontend data access

## Changes

- `.github/workflows/update.yml`
- `.github/workflows/deploy.yml`
- `web/data-provider.js`

## Removed

- `.github/workflows/scrape.yml`
- `web/opportunities.json`
- `web/expired.json`

## Safety

- `data/opportunities.json` was not rebuilt.
- `data/checkpoint.json` was not rebuilt.
- `data/expired.json` was preserved.
- `data/full_detail_repair_checkpoint.json` was preserved.
- No scraper execution was performed.
- No Git history rewrite was performed.
