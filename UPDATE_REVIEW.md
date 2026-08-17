# ESC Opportunity Finder — Scraper to Pages Deployment Fix

## Root cause

The scraper workflow successfully updated the cache on main.

GitHub Pages previously depended on a normal push event, which was
not reliably triggered by the GitHub Actions cache commit.

## Fix

deploy.yml now listens for:

workflow_run:
  workflows:
    - "Update ESC Opportunities"
  types:
    - completed

and deploys only after a successful scraper workflow.

## Production flow

Update ESC Opportunities
    -> incremental scraper
    -> cache publication
    -> scraper workflow success
    -> deploy.yml workflow_run
    -> GitHub Pages
    -> live website

## Schedule

The scraper remains approximately every 30 minutes:

17,47 * * * *

## Safety

No protected cache/checkpoint file is modified.
