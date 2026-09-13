---
name: project-progress-journal
description: Maintain concise project records while doing software, automation, debugging, or multi-step project work. Use when Codex completes real project progress, fixes or investigates bugs, discovers durable project facts such as environment requirements, screen resolution, credentials/permission assumptions, important data locations, commands, constraints, or when the user asks to record progress, logs, debug notes, project memory, or daily status.
---

# Project Progress Journal

Use this skill to keep project memory useful across sessions. Record facts that help future Codex instances resume work, reproduce behavior, debug faster, or understand what was actually completed.

## Files

Create and maintain these files inside the active project:

- `docs/progress/YYYY-MM-DD.md`: daily completed progress.
- `docs/project-notes.md`: durable project memory, current status, important decisions, environment and data notes.
- `docs/debug/YYYY-MM-DD-debug.md`: short-lived debug and log notes.

Use the user's current local date for filenames. If the project has a documented docs location, follow that location while preserving the same file purposes.

## Quick Setup

Use `scripts/update_journal.py` to create the standard files and prune old debug logs:

```bash
python <skill-dir>/scripts/update_journal.py --project-root <project-root>
```

Useful options:

```bash
python <skill-dir>/scripts/update_journal.py --project-root <project-root> --progress "Finished login redirect fix; verified with npm test."
python <skill-dir>/scripts/update_journal.py --project-root <project-root> --debug "Playwright failed because the app was not running on localhost:3000."
python <skill-dir>/scripts/update_journal.py --project-root <project-root> --note "Automation requires 1920x1080 resolution for image matching."
```

You may edit the markdown files directly when the update needs structure or nuance.

## What To Record

### Daily Progress

Record only completed, concrete work in `docs/progress/YYYY-MM-DD.md`.

Include:

- completed tasks and user-visible outcomes;
- important files or modules changed;
- verification performed and results;
- remaining follow-ups only when they directly continue completed work.

Do not include:

- vague effort logs;
- plans that were not executed;
- failed experiments unless they produced a useful conclusion, which belongs in debug or project notes.

### Project Notes

Record durable project memory in `docs/project-notes.md`.

Maintain these sections when relevant:

- `Current Status`: current objective, where the project stands, next important step, blockers.
- `Environment`: OS, tool versions, required services, screen resolution, browser/profile assumptions, device state.
- `Commands`: reliable setup, run, test, build, deploy, or automation commands.
- `Important Data`: local paths, datasets, test accounts, config files, IDs, external system assumptions. Do not write secrets.
- `Decisions`: important choices and why they were made.
- `Durable Debug Findings`: conclusions extracted from debug logs that remain useful after raw logs expire.

Prefer durable facts over chatter. If a fact will matter for reproduction, automation reliability, debugging, or handoff, record it.

### Debug And Logs

Record debugging work in `docs/debug/YYYY-MM-DD-debug.md`.

Include:

- symptom or error;
- relevant command or log excerpt summary;
- suspected cause;
- attempted fixes and outcomes;
- final root cause and resolution when known;
- durable conclusion to promote into `docs/project-notes.md` before old logs are removed.

Keep raw debug logs for 5 days. Before removing old debug files, preserve any long-term conclusions in `docs/project-notes.md`.

## When To Update

Update the journal when:

- a real task is completed;
- a bug is investigated or fixed;
- an important environment, data, command, permission, or automation constraint is discovered;
- the project phase changes;
- the user says to record, summarize, update progress, write logs, or remember something.

Avoid updating after every minor message. Batch related entries into concise notes when possible.

## Completion Checklist

Before claiming a substantial project task is done, check:

- Today's progress file includes completed work and verification.
- `docs/project-notes.md` includes any durable project facts discovered during the task.
- Debug notes exist if an error, failed command, or investigation occurred.
- Debug logs older than 5 days have been pruned after durable findings were preserved.

Keep entries short, factual, and useful to a future agent.
