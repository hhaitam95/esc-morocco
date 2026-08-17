# ESC Opportunity Finder — Workflow Syntax Repair

## Fixed

Repaired the GitHub Actions workflow syntax/staging-output issue.

The workflow now contains exactly:

`printf '%s\n' "$STAGED"`

with no trailing whitespace.

## Schedule

The incremental scraper remains scheduled approximately every 30 minutes:

`17,47 * * * *`

## Preserved

No changes were made to:

- scraper.py
- checkpoint.json
- expired.json
- opportunities.json
- web/opportunities.json
- scraper batch size
- scraper retry behavior
- scraper rate limits
- checkpoint state
- backend repair checkpoint

## Validation

- update.py syntax
- workflow text structure
- workflow YAML
- trailing whitespace
- protected backend/cache state
