# ESC Opportunity Finder Backend

This directory contains the first cache-first backend foundation.

## Architecture

The scraper remains responsible for collecting and incrementally updating
the canonical opportunity dataset:

    data/opportunities.json

The backend does not scrape the ESC portal for every user search.

Instead, the request flow is:

    User
      |
      v
    Search API
      |
      v
    Backend cache
      |
      v
    data/opportunities.json

The scheduled GitHub Actions scraper keeps the cache fresh.

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

Provides a command-line search service for the current development phase.

Example:

    python -m backend.search MA

The command returns JSON.

### test_search.py

Contains basic backend/cache tests.

## Cache strategy

The canonical dataset remains:

    data/opportunities.json

The website copy remains:

    web/opportunities.json

The manifest is:

    data/cache_manifest.json

The manifest provides lightweight metadata without requiring consumers to
load the entire opportunity dataset.

## Important design decision

The participant-country search currently operates entirely against the cache.

It does not make live ESC API requests.

This gives us:

- fast searches
- predictable response times
- no ESC API dependency during a user request
- protection against request spikes
- simpler error handling
- a clear separation between ingestion and serving

The next phase can add an HTTP service around `backend.search`.

Only after that service is stable should the frontend Search action be connected
to it.

## Future refresh model

The scheduled scraper should remain the ingestion mechanism.

Its responsibility is to:

1. discover current ESC opportunities
2. compare them with the checkpoint/cache
3. fetch detail pages when necessary
4. update existing opportunities when their relevant data changes
5. remove or archive opportunities that are no longer active
6. publish the resulting canonical JSON

The frontend/backend serving path should never need to perform a full scrape.

## Reliability model

The scraper and the search service are intentionally separated.

A temporary ESC API outage should not make the cached search unavailable.

A user search should continue returning the most recently successful cache.

The cache should therefore be treated as a durable snapshot rather than a
temporary intermediate result.
