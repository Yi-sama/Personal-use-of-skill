#!/usr/bin/env python3
"""Create and update project journal files."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path


PROGRESS_TEMPLATE = """# {today} Progress

## Completed

- 

## Verification

- 

## Follow-ups

- 
"""

PROJECT_NOTES_TEMPLATE = """# Project Notes

## Current Status

- Objective:
- Current state:
- Next step:
- Blockers:

## Environment

- 

## Commands

- 

## Important Data

- 

## Decisions

- 

## Durable Debug Findings

- 
"""

DEBUG_TEMPLATE = """# {today} Debug Log

## Issues

- 

## Attempts

- 

## Resolution

- 

## Durable Findings To Promote

- 
"""


def append_entry(path: Path, heading: str, text: str) -> None:
    timestamp = datetime.now().strftime("%H:%M")
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"\n## {heading} {timestamp}\n\n- {text.strip()}\n")


def ensure_file(path: Path, template: str) -> None:
    if not path.exists():
        path.write_text(template, encoding="utf-8", newline="\n")


def prune_debug_logs(debug_dir: Path, today: date, keep_days: int) -> list[Path]:
    cutoff = today - timedelta(days=keep_days - 1)
    removed: list[Path] = []

    for path in debug_dir.glob("*-debug.md"):
        stem = path.name.removesuffix("-debug.md")
        try:
            file_date = date.fromisoformat(stem)
        except ValueError:
            continue
        if file_date < cutoff:
            path.unlink()
            removed.append(path)

    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Maintain project progress journal files.")
    parser.add_argument("--project-root", default=".", help="Project root to update.")
    parser.add_argument("--date", default=None, help="Date to use in YYYY-MM-DD format. Defaults to today.")
    parser.add_argument("--keep-debug-days", type=int, default=5, help="Number of days of debug logs to keep.")
    parser.add_argument("--progress", default=None, help="Append one completed progress entry.")
    parser.add_argument("--debug", default=None, help="Append one debug entry.")
    parser.add_argument("--note", default=None, help="Append one durable project note.")
    args = parser.parse_args()

    today = date.fromisoformat(args.date) if args.date else date.today()
    today_text = today.isoformat()
    project_root = Path(args.project_root).resolve()
    docs_dir = project_root / "docs"
    progress_dir = docs_dir / "progress"
    debug_dir = docs_dir / "debug"

    progress_dir.mkdir(parents=True, exist_ok=True)
    debug_dir.mkdir(parents=True, exist_ok=True)

    progress_file = progress_dir / f"{today_text}.md"
    notes_file = docs_dir / "project-notes.md"
    debug_file = debug_dir / f"{today_text}-debug.md"

    ensure_file(progress_file, PROGRESS_TEMPLATE.format(today=today_text))
    ensure_file(notes_file, PROJECT_NOTES_TEMPLATE)
    ensure_file(debug_file, DEBUG_TEMPLATE.format(today=today_text))

    if args.progress:
        append_entry(progress_file, "Completed Entry", args.progress)
    if args.debug:
        append_entry(debug_file, "Debug Entry", args.debug)
    if args.note:
        append_entry(notes_file, "Journal Note", args.note)

    removed = prune_debug_logs(debug_dir, today, args.keep_debug_days)

    print(f"progress={progress_file}")
    print(f"notes={notes_file}")
    print(f"debug={debug_file}")
    if removed:
        print("removed_debug=" + ",".join(str(path) for path in removed))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
