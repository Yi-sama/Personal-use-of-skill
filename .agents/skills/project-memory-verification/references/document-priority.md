# Document Priority and Context Discovery

## Discovery

1. Locate repository root and target path.
2. Search for every `AGENTS.md` from root through target directory.
3. Read applicable rule files from broadest to narrowest scope.
4. Read `README.md`, `SPEC.md`, and `LOG-INDEX.md` when present.
5. Search `LOG.md` selectively by ID, date, hash, path, or topic.

## Precedence

- Current user instructions override project documentation.
- A deeper applicable `AGENTS.md` overrides a shallower one.
- `AGENTS.md` controls how work is performed.
- Current reproducible code and tests are strongest evidence of actual behavior.
- `SPEC.md` is authoritative for intended behavior and acceptance criteria.
- `README.md` is the current orientation document.
- `LOG.md` is historical evidence and may be superseded.
- AI inference is lowest-confidence evidence and must be labeled.

## Missing and conflicting files

- No `AGENTS.md`: continue with normal AI engineering workflow, explicitly report the file was not found, and do not call inferred conventions mandatory.
- Unreadable applicable rule: read-only analysis is allowed; state-changing work waits unless the missing rule cannot affect it.
- Conflicting rules: use scope precedence; if still unresolved, stop on affected files and ask the user.
- Missing memory files: report them. Do not create a full memory system unless requested or explicitly required.

## Conflict record

```text
MEMORY_CONFLICT
Topic:
Sources:
Observed conflict:
Current evidence:
Affected files:
Required decision:
```