# Shared Windows global Agent

This is the reviewed shared global `AGENTS.md` for the Windows computers using this repository.

Keep machine-specific exceptions in `AGENTS.override.md` and do not commit secrets, credentials, local cache paths, or one-off machine state. The shared file assumes the Error Summary skill and its current FastCtx rules are available; if a computer lacks FastCtx, follow the documented fallback instead of inventing a different tool boundary.
