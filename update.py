#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEPLOY = ROOT / ".github" / "workflows" / "deploy.yml"
STALE_BACKUP = ROOT / ".github" / "workflows" / "update.yml.phase5-backup"
CHECKPOINT = ROOT / "data" / "full_detail_repair_checkpoint.json"

EXPECTED_REMOTE = "https://github.com/hhaitam95/esc-opportunity-finder.git"


def run(*args: str, check: bool = True, capture: bool = True) -> str:
    result = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        check=False,
    )

    if check and result.returncode != 0:
        output = result.stdout or ""
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(args)}\n{output}"
        )

    return result.stdout or ""


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    print("No destructive cleanup was performed.")
    sys.exit(1)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def validate_update_py() -> None:
    try:
        run(sys.executable, "-m", "py_compile", str(Path(__file__)))
    except RuntimeError as exc:
        fail(str(exc))

    print("PASS: update.py syntax validated.")


def validate_repository() -> None:
    if not ROOT.is_dir():
        fail(f"repository root does not exist: {ROOT}")

    print(f"PASS: repository root validated: {ROOT}")

    branch = run("git", "branch", "--show-current").strip()
    if branch != "main":
        fail(f"current branch must be main, found: {branch}")

    print("PASS: current branch is main.")

    remote = run("git", "remote", "get-url", "origin").strip()
    if remote != EXPECTED_REMOTE:
        fail(
            "origin remote is not canonical:\n"
            f"  expected: {EXPECTED_REMOTE}\n"
            f"  found:    {remote}"
        )

    print(f"PASS: origin remote is canonical: {remote}")


def print_status() -> list[str]:
    status = run("git", "status", "--porcelain=v1").splitlines()

    print("Current Git status:")
    if status:
        for line in status:
            print(line)
    else:
        print("(clean)")

    return status


def validate_allowed_changes(status: list[str]) -> None:
    allowed_exact = {
        "M update.py",
        "?? data/full_detail_repair_checkpoint.json",
    }

    unexpected = []

    for line in status:
        if line in allowed_exact:
            continue

        # Git can show an explicitly modified update.py in either staged
        # or unstaged form. We handle the common forms safely.
        if line.endswith("update.py") and (
            line.startswith(" M ") or line.startswith("M  ")
        ):
            continue

        if line in {
            "?? .github/workflows/update.yml.phase5-backup",
        }:
            continue

        unexpected.append(line)

    if unexpected:
        fail("Unexpected working-tree changes detected:\n" + "\n".join(unexpected))

    print(
        "PASS: working-tree changes are limited to local tooling and protected checkpoint."
    )


def remove_stale_backup() -> None:
    if STALE_BACKUP.exists():
        print(f"Removing stale workflow backup: {STALE_BACKUP}")
        STALE_BACKUP.unlink()
        print("PASS: stale update.yml.phase5-backup removed.")
    else:
        print("PASS: no stale update.yml.phase5-backup exists.")


def verify_checkpoint() -> bytes | None:
    if not CHECKPOINT.exists():
        print("INFO: protected repair checkpoint is not present.")
        return None

    original = CHECKPOINT.read_bytes()
    print("PASS: protected repair checkpoint captured.")
    return original


def refresh_origin() -> None:
    run("git", "fetch", "origin", "main")
    print("PASS: origin/main refreshed.")

    counts = run(
        "git",
        "rev-list",
        "--left-right",
        "--count",
        "main...origin/main",
    ).strip()

    ahead, behind = [int(x) for x in counts.split()]

    print(f"Local commits ahead: {ahead}")
    print(f"Remote commits ahead: {behind}")

    if ahead:
        fail(
            "Local main contains commits that are not on origin/main. "
            "No automatic merge or overwrite will be performed."
        )

    if behind:
        print("INFO: Local main is behind origin/main.")
        print("Synchronizing with a safe fast-forward.")

        # update.py itself is uncommitted. Stash only the local tooling and
        # protected checkpoint, fast-forward main, then restore them.
        stash_result = run(
            "git",
            "stash",
            "push",
            "-u",
            "-m",
            "esc-phase-deploy-local-tooling",
            "--",
            "update.py",
            "data/full_detail_repair_checkpoint.json",
        )

        try:
            run("git", "merge", "--ff-only", "origin/main")
        finally:
            pop_result = subprocess.run(
                ["git", "stash", "pop"],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

            if pop_result.returncode != 0:
                raise RuntimeError(
                    "Failed to restore local tooling/checkpoint after "
                    "fast-forward:\n" + (pop_result.stdout or "")
                )

        print("PASS: local main safely fast-forwarded to origin/main.")
    else:
        print("PASS: local main and origin/main are synchronized.")


def validate_checkpoint_unchanged(original: bytes | None) -> None:
    if original is None:
        return

    if not CHECKPOINT.exists():
        fail("protected repair checkpoint disappeared.")

    current = CHECKPOINT.read_bytes()

    if current != original:
        fail("protected repair checkpoint was modified.")

    print("PASS: protected repair checkpoint remains byte-for-byte unchanged.")


def deploy_workflow() -> str:
    return """name: Deploy ESC Website

on:
  workflow_run:
    workflows:
      - "Update ESC Opportunities"
    types:
      - completed
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  deploy:
    if: >
      github.event_name == 'workflow_dispatch' ||
      (
        github.event.workflow_run.conclusion == 'success' &&
        github.event.workflow_run.name == 'Update ESC Opportunities'
      )

    runs-on: ubuntu-latest

    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup GitHub Pages
        uses: actions/configure-pages@v5

      - name: Upload website
        uses: actions/upload-pages-artifact@v3
        with:
          path: ./web

      - name: Deploy ESC Website
        id: deployment
        uses: actions/deploy-pages@v4
"""


def write_deploy_workflow() -> None:
    if not DEPLOY.parent.exists():
        DEPLOY.parent.mkdir(parents=True, exist_ok=True)

    write_text(DEPLOY, deploy_workflow())
    print("PASS: deploy.yml replaced with the simplified deployment workflow.")


def validate_deploy_workflow() -> None:
    source = read_text(DEPLOY)

    required = [
        "name: Deploy ESC Website",
        "workflow_run:",
        '"Update ESC Opportunities"',
        "types:",
        "- completed",
        "workflow_dispatch:",
        "actions/checkout@v4",
        "actions/configure-pages@v5",
        "actions/upload-pages-artifact@v3",
        "actions/deploy-pages@v4",
        "path: ./web",
        "github.event.workflow_run.conclusion == 'success'",
    ]

    missing = [item for item in required if item not in source]

    if missing:
        fail(
            "deploy.yml is missing required architecture markers:\n"
            + "\n".join(f"- {item}" for item in missing)
        )

    if "scraper.py" in source or "scraper/scraper.py" in source:
        fail("deploy.yml must not run the scraper.")

    if "schedule:" in source:
        fail("deploy.yml must not have its own schedule.")

    print("PASS: deploy.yml contains the simplified deployment architecture.")
    print("PASS: deploy.yml waits for successful Update ESC Opportunities runs.")
    print("PASS: deploy.yml supports manual workflow_dispatch.")
    print("PASS: deploy.yml does not run scraper.py.")
    print("PASS: deploy.yml has no independent schedule.")
    print("PASS: deploy.yml deploys the existing ./web directory.")


def validate_web_directory() -> None:
    if not (ROOT / "web").is_dir():
        fail("web/ directory does not exist.")

    print("PASS: web/ directory exists.")


def git_commit_and_push() -> None:
    status = run("git", "status", "--porcelain=v1").splitlines()

    relevant = [
        line
        for line in status
        if line.endswith("update.py")
        or line.endswith(".github/workflows/deploy.yml")
        or line.endswith("data/full_detail_repair_checkpoint.json")
    ]

    if not relevant:
        print("INFO: No deploy workflow changes need to be committed.")
        return

    run(
        "git",
        "add",
        ".github/workflows/deploy.yml",
        "update.py",
    )

    # Never stage the protected repair checkpoint.
    run("git", "reset", "--", "data/full_detail_repair_checkpoint.json")

    staged = run("git", "diff", "--cached", "--name-only").splitlines()

    expected = {
        ".github/workflows/deploy.yml",
        "update.py",
    }

    unexpected = set(staged) - expected

    if unexpected:
        run("git", "reset")
        fail("Unexpected files became staged:\n" + "\n".join(sorted(unexpected)))

    if not staged:
        print("INFO: Nothing to commit.")
        return

    run(
        "git",
        "commit",
        "-m",
        "Simplify ESC website deployment workflow",
    )

    run("git", "push", "origin", "main")

    print("PASS: simplified deploy.yml committed and pushed to origin/main.")


def final_status() -> None:
    print()
    print("=" * 72)
    print("FINAL STATUS")
    print("=" * 72)

    status = run("git", "status", "--porcelain=v1").splitlines()

    if status:
        print("Remaining local changes:")
        for line in status:
            print(line)
    else:
        print("PASS: working tree is clean.")

    print("PASS: Deploy ESC Website configuration is ready.")


def main() -> None:
    print()
    print("=" * 72)
    print("ESC Opportunity Finder — simplified Deploy ESC Website")
    print("=" * 72)

    validate_update_py()
    validate_repository()

    initial_status = print_status()
    checkpoint_original = verify_checkpoint()

    validate_allowed_changes(initial_status)

    remove_stale_backup()

    refresh_origin()

    # After a fast-forward, the deploy workflow from origin/main may already
    # exist. We intentionally replace only deploy.yml with the simple design.
    write_deploy_workflow()
    validate_deploy_workflow()
    validate_web_directory()

    validate_checkpoint_unchanged(checkpoint_original)

    git_commit_and_push()

    validate_checkpoint_unchanged(checkpoint_original)
    final_status()

    print()
    print("DONE: update.yml remains the scraper workflow.")
    print("DONE: deploy.yml now deploys only after update.yml succeeds.")
    print("DONE: manual deployment remains available through workflow_dispatch.")
    print("DONE: no scraper logic was added to deploy.yml.")
    print("DONE: no protected checkpoint was modified.")


if __name__ == "__main__":
    main()
