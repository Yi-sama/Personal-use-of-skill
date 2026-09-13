# Verification States

## Check states

`spec_check`: `pass`, `fail`, `unknown`, or `blocked`.

`runtime_check`: `pass`, `fail`, `partial`, `not_run`, `blocked`, or `not_applicable`.

`human_check`: `pass`, `fail`, `pending`, or `not_applicable`.

## Overall states

- `verified`: applicable specification and runtime checks pass, the scoped diff is understood, and human validation passes or does not apply.
- `partially_verified`: useful evidence exists but a required check is pending, partial, blocked, or not run.
- `failed`: a relevant check fails.
- `blocked`: required evidence cannot be obtained without external action.
- `unverified`: no meaningful verification evidence exists.

Never promote a partial or unverified result to verified merely because the code looks plausible.