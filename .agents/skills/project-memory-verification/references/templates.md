# Copyable Templates

## Project-memory summary

```text
Project purpose:
Current objective:
Applicable AGENTS.md:
README/SPEC/LOG-INDEX status:
Matched known-error HASHes:
Relevant history:
Existing uncommitted changes:
Facts:
Inferences:
Unknowns:
Validation required:
```

## LOG entry

```markdown
## LOG-YYYY-MM-DD-NNN - Title

- Date:
- Objective/symptom:
- Scope/files:
- Change/investigation:
- Decision and reason:
- Baseline or reproduction:
- `spec_check`:
- `runtime_check`:
- `human_check`:
- Tool errors and resolutions:
- Overall status:
- Remaining risks/follow-ups:
- Git hash:
```

## LOG-INDEX row

```markdown
| ID | Date | Topic | Scope | Status | LOG location | Hash |
|---|---|---|---|---|---|---|
| LOG-YYYY-MM-DD-NNN | YYYY-MM-DD | Short topic | module/path | partially_verified | LOG.md:Lx | abc1234 |
```

## Verification report

```markdown
## Verification

- `spec_check`: pass/fail/unknown/blocked
- `runtime_check`: pass/fail/partial/not_run/blocked/not_applicable
- `human_check`: pass/fail/pending/not_applicable
- `overall`: verified/partially_verified/failed/blocked/unverified
- Tool errors:
  - Tool:
  - Operation:
  - Error:
  - Impact:
  - Resolution attempted:
  - Resolution result:
  - Verification:
  - Remaining action:
- Commands:
  - `exact command`
- Evidence:
  - observed result
- Manual checklist for the user:
  - [ ] concrete action and expected result
- Remaining risks:
```
