# ESC Opportunity Finder — Codex Instructions

## Project

This repository contains the ESC Opportunity Finder:

- Python scraper
- GitHub Actions automation
- JSON data/checkpoint storage
- GitHub Pages frontend

## Important rules

- Inspect the existing implementation before changing it.
- Preserve existing functionality unless the task explicitly changes it.
- Prefer small, targeted changes over rewriting entire files.
- Never overwrite `data/checkpoint.json` manually.
- Never delete or reset scraper progress.
- Do not change scraper rate limits, batch sizes, retry behavior, or workflow scheduling without explaining the impact.
- Do not commit or push unless explicitly requested by the user.
- Never use destructive git commands such as `git reset --hard`, `git checkout --`, or deleting checkpoint/data files unless explicitly instructed.

## Backend

The scraper must preserve:

- Fresh retrieval of the European Youth Portal opportunity list.
- Persistent checkpoint/resumable processing.
- New-opportunity detection.
- Rechecking of existing Morocco matches.
- Skipping previously processed non-Morocco opportunities.
- Archive/history handling.
- Rate-limit handling and safe checkpoint saves.
- GitHub Actions batch execution.
- JSON publishing to `web/`.

Current scraper behavior:

- Detail-page batch size is deliberately bounded.
- Detail requests are rate-limited with delays.
- HTTP 429 must cause safe resumable stopping rather than data loss.
- Existing Morocco matches are rechecked every run.
- Previously processed `not_morocco` opportunities should be skipped.

## Frontend

Preserve:

- EN / FR / AR translations.
- Arabic RTL layout.
- Country normalization (`EL` → Greece, `UK` → United Kingdom).
- Country flags.
- Activity-type icons.
- Topic icons.
- Deadline urgency display.
- Recently expired section.
- Browser-local NEW opportunity detection.
- Activity-duration display.
- GitHub Pages compatibility.
- Cache-busting for JS/CSS assets.

Frontend changes should not accidentally remove existing features.

## Testing

After Python changes:

```bash
python3 -m py_compile scraper/scraper.py
```

After JavaScript changes:

```bash
node --check web/app.js
```

For archive changes:

```bash
python3 scraper/test_archive.py
```

Before suggesting a commit, inspect:

```bash
git status
git diff
```

## Git

- Check `git status` before making changes.
- Check recent commits when necessary.
- Remember that GitHub Actions automatically commits `data/checkpoint.json` and generated JSON files.
- Never overwrite newer remote checkpoint progress with an older local checkpoint.
- If `origin/main` has moved, reconcile changes carefully before committing.
- Do not commit or push unless the user explicitly asks for it.

## Working style

When asked to implement a feature:

1. Inspect the relevant current files first.
2. Briefly explain the planned changes.
3. Make the smallest safe implementation.
4. Run the appropriate syntax checks/tests.
5. Review the resulting diff for unintended changes.
6. Tell the user exactly what changed.
7. Leave commit and push to the user unless explicitly requested.
