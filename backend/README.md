# ESC Opportunity Finder Backend

This directory contains the first cache-first backend foundation.

## Architecture

The scraper remains responsible for collecting and incrementally updating
the canonical opportunity dataset:

    data/opportunities.json

The backend does not scrape the ESC portal for every user search.

The current request flow is:

    User
      |
      v
    Search service
      |
      v
    Backend cache
      |
      v
    data/opportunities.json

The scheduled GitHub Actions scraper will keep the cache fresh.

## Files

### cache.py

Provides the cache abstraction.

Responsibilities:

- load the canonical opportunity cache
- validate the basic cache structure
- normalize participant country codes
- filter opportunities by participant country
- expose cache metadata

### search.py

Provides the current command-line search service.

Example:

    python -m backend.search MA

The command returns JSON.

### test_search.py

Contains backend/cache tests.

## Cache strategy

The canonical dataset remains:

    data/opportunities.json

The website copy remains:

    web/opportunities.json

The lightweight manifest is:

    data/cache_manifest.json

The manifest allows consumers to inspect basic cache metadata without
loading the entire opportunity dataset.

## Important design decision

Participant-country search currently operates entirely against the cache.

It does not make a live ESC request during a user search.

This gives us:

- fast searches
- predictable response times
- no ESC API dependency during a user request
- protection against request spikes
- simpler error handling
- a clear separation between ingestion and serving

## Future architecture

The next phases can add:

1. an HTTP service around the search layer
2. frontend Search-button integration
3. cache freshness comparison
4. detection of opportunities that appeared after the previous cache
5. live/new-opportunity reconciliation where appropriate

The frontend/backend serving path should never need to perform a full scrape.

## Reliability model

The scraper and search service are intentionally separated.

A temporary ESC API outage should not make the cached search unavailable.

A user search should continue returning the most recently successful cache.

The cache is therefore treated as a durable snapshot rather than a temporary
intermediate result.

## Phase-one scope

Phase one intentionally does not implement:

- HTTP serving
- frontend integration
- live user-triggered scraping
- cache-vs-live reconciliation
- hourly GitHub Actions configuration

Those are subsequent implementation phases.
