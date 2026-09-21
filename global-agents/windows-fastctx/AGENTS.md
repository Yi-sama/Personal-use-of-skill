# Global Agent Rules

- Before the first local-file operation, read `$HOME\.agents\skills\project-memory-verification\references\error-index.md` with targeted PowerShell/.NET or `rg`. Match only cases triggered by the planned operation or an observed failure.
- For substantive project work, use `project-memory-verification`: read applicable `AGENTS.md`, inspect Git status and relevant diffs, and load only necessary project context. Preserve all unrelated user changes and keep edits scoped.

<!-- fastctx:begin -->
- FastCtx is optional and must be called only through direct top-level `mcp__fastctx__*` tools. Use known files or narrow accessible subtrees; otherwise fall back to targeted PowerShell or `rg`.
- Continue `Partial` output only with its exact parameters. Before `replace` or FastCtx diagnostics, read case `724f44f97dc7`; preview, cap, and verify replacements.
<!-- fastctx:end -->

- Handle small or known tasks directly. Delegate only bounded, independent work that reduces context load or provides useful review. Fresh agents use `fork_turns="none"`; they are read-only unless explicitly given a non-overlapping write scope. Wait for all delegated results and verify key evidence.
- Unless the user requests only planning or read-only analysis, complete authorized implementation and focused verification.
- For defects, establish the root cause. Do not call retries, suppression, ignored errors, or test-only changes a fix unless the user accepts a workaround.
- Verify observable behavior, not only exit codes. Report tool failures and separate facts, inferences, unknowns, automated checks, and pending human validation.
- Keep final responses concise: changes, verification, remaining risk, and required user action.
