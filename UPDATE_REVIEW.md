# ESC Opportunity Finder — Backend Finalization Review

## Incremental scraper

The existing scraper architecture is preserved.

It continues to:

- fetch the current ESC opportunity listing;
- compare current IDs against persistent checkpoint state;
- process new opportunity IDs;
- retry failed opportunities;
- recheck stale opportunities;
- persist checkpoint progress;
- publish the current opportunity cache;
- publish the expired archive.

No cache reset or scraper rewrite is performed.

## Schedule

The GitHub Actions update workflow runs approximately every 30 minutes:

`17,47 * * * *`

The existing concurrency protection and bounded scraper behavior
remain unchanged.

## Last updated

The UI reads the existing scraper-generated `generated_at` timestamp
from `web/opportunities.json`.

Search actions do not change this timestamp.

## Protected state

The update does not modify:

- data/checkpoint.json
- data/expired.json
- data/opportunities.json
- web/opportunities.json
- data/full_detail_repair_checkpoint.json
