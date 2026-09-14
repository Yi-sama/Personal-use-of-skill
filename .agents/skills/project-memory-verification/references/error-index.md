# Known Error Index

Read this compact index at the start of a non-trivial project task. Match the current environment, content, and planned tool calls against the triggers. Open only matching detailed cases by permanent HASH.

| HASH | Trigger | Verified direction | Detailed case |
|---|---|---|---|
| `0a8f92c4de0d` | Writing or editing non-ASCII text on Windows when file encoding is unknown or a default encoding may be used | Use explicit UTF-8 and verify the actual bytes/content after writing | `references/error-0a8f92c4de0d.md` |
| `75e0ba56ceb6` | Sending a multiline patch through Windows PowerShell 5.1, CMD/BAT, or an `apply_patch.bat` wrapper that forwards native arguments | Avoid the unsafe native argument boundary and use the verified UTF-8 transport from the case | `references/error-75e0ba56ceb6.md` |
| `5bd54090a30f` | A broad FastCtx traversal reaches a restricted runtime, work, temporary, cache, or fixture directory | Keep permissions unchanged, narrow the operation to known accessible files or subtrees, and report the excluded scope | `references/error-5bd54090a30f.md` |
| `ea543e17f995` | `Win32_Process` is unavailable through WMI/CIM and a process command line cannot be queried | Record the HRESULT, use `Get-Process` only for identity fields, and mark the full command line unavailable | `references/error-ea543e17f995.md` |
| `9c81d71b50e2` | An optional OpenCV check fails because the selected Python environment cannot import `cv2` | Confirm the project interpreter and skip unrelated revalidation without installing packages or switching environments | `references/error-9c81d71b50e2.md` |
| `724f44f97dc7` | Calling FastCtx MCP tools, continuing partial reads, handling Rust-regex diagnostics, or performing guarded batch replacement | Invoke FastCtx through its direct MCP boundary, follow exact continuation parameters, and preview and cap replacements before writing | `references/error-724f44f97dc7.md` |

HASH values are permanent semantic lookup keys, not file checksums. Never modify or reuse an assigned HASH.

If a case matches, follow its verified method. If that method fails, report the tool error and evidence to the user before trying a materially different approach. If no case matches, continue normally.

When adding a case:

1. Define a stable English canonical key for the failure mode.
2. Derive one short HASH, preferably the first 12 characters of SHA-256.
3. Add one compact index row and one detailed reference file.
4. Record problem, environment, reproduction, root cause, failed path, verified path, and verification criteria.
5. Require runnable or inspectable evidence for every conclusion.
