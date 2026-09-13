# Error Case 724f44f97dc7: FastCtx MCP Direct Invocation and Safe Error Handling

## Trigger

Use this case before FastCtx `replace`, when diagnosing FastCtx availability or invocation boundaries, when a result is `Partial`, or when a path, encoding, glob, regex, replacement, or write-guard diagnostic is returned.

**Bootstrap boundary:** Load the Error Summary `AGENTS.md` and `docs/ERROR-INDEX.md` first with a targeted ordinary PowerShell/.NET or `rg` read. After that bootstrap, an ordinary direct top-level FastCtx `read`, `grep`, or `glob` call does not require this detailed case to be preloaded. Do not try `tools.mcp__fastctx__*` from a generic JavaScript wrapper.

## Confirmed failure

In the verified Codex desktop environment with FastCtx 0.2.4:

- Calling `tools.mcp__fastctx__grep(...)` from the generic JavaScript tool orchestrator failed with `TypeError: tools.mcp__fastctx__grep is not a function`. The FastCtx tools were registered as direct MCP tools outside that wrapper.
- Direct top-level FastCtx MCP calls succeeded, and `fastctx status` reported a successful MCP handshake with four matching tool-contract hashes.
- A missing file and `offset=0` returned actionable `read` diagnostics. A mixed batch read preserved valid-file output and returned exact continuation parameters that omitted the failed file.
- Malformed Rust regex and lookaround syntax returned parse diagnostics. FastCtx uses Rust regex syntax and does not support lookaround or backreferences.
- `replace` rejected an invalid regex, a replacement that referenced an undefined capture group, and a write whose match count exceeded `max_replacements`. Each rejection stated that nothing was written.
- A no-match search or replacement completed normally and was not an error.
- Successful results ended in `Complete` or `Partial`; validation and path-error diagnostics did not necessarily include either marker.

Post-failure searches confirmed that guarded replacement tests preserved all three original markers and wrote zero copies of the proposed replacement text.

## Verified method

1. For routine direct reads and searches, do not run availability diagnostics first. When diagnosing availability, use `fastctx status` and treat successful config parsing, applied state, installed binary, MCP handshake, and guidance checks as separate evidence.
2. Invoke FastCtx through the direct top-level MCP tool boundary. Do not assume direct MCP tools are callable as `tools.mcp__fastctx__*` inside a generic JavaScript orchestrator. Use only an outer parallel-call mechanism that explicitly supports direct MCP tools.
3. Pass absolute paths. For several text files, prefer one batch `read` request.
3a. Batch `read` requests with `files` must omit top-level `limit`, `offset`, `encoding`, `pages`, `pdf_mode`, and `view`; use per-file options or separate reads. Treat any mixed top-level/per-file shape as invalid before sending it.
4. On `Partial`, copy the exact continuation parameters from the result. Do not reconstruct offsets or re-add failed batch entries. Stop when the task has enough data or the result reports `Complete`.
5. Treat a path, parameter, encoding, glob, or regex diagnostic without `Complete` or `Partial` as a failed call. Correct the reported input before retrying.
6. Use Rust-compatible regex. For literal replacement text, set `literal=true` so regex metacharacters are not interpreted.
7. Before a real batch replacement, constrain `path` and `glob`, run `dry_run=true`, inspect the exact match count, and set `max_replacements` to an intentional upper bound.
8. After replacement, re-read or search the affected files. Verify the expected new count, the removed old count, and representative surrounding content instead of trusting the completion line alone.
9. Use FastCtx `replace` for mechanical substitutions. Keep semantic rewrites and generated content on `apply_patch` as required by the local guidance.
10. Before `glob` or `grep`, require a known accessible subtree. Reject project-root recursive wildcards and paths that intentionally include `runtime_data`, `work`, temp, cache, or fixture directories; establish unknown scope with targeted PowerShell or `rg` first.

If direct MCP invocation also fails, run `fastctx status` and report the handshake, applied-state, binary, and server diagnostics before reinstalling or changing configuration. A generic-wrapper `TypeError` alone does not prove that the FastCtx server is unhealthy.

Choosing targeted PowerShell or `rg` without first making a failing FastCtx call is a normal fallback, not a tool failure. Do not report a startup-order violation merely because the bootstrap files were read without FastCtx or because the optional FastCtx path was skipped.

## Verification criteria

- `fastctx status` reports successful configuration parsing, applied state, installed binary, and MCP handshake.
- Direct `read`, `grep`, `glob`, and `replace` calls return the documented result shapes.
- Every `Partial` result is continued only with its exact returned parameters when more data is needed.
- Invalid paths, offsets, glob syntax, regex syntax, capture references, and replacement caps produce actionable diagnostics.
- Dry-run replacement leaves files unchanged.
- Rejected replacement leaves files unchanged, confirmed by a follow-up read or search.
- Successful replacement changes only the intended matches and passes a follow-up content/count check.

Concurrent-modification rejection, ambiguous legacy encodings, images, PDFs, hex view, and extreme-size output require separate targeted verification when those boundaries are relevant.
