# Error Case 75e0ba56ceb6: Windows Multiline apply_patch Argument Boundary

## Trigger

Use this case when a multiline patch must cross Windows PowerShell 5.1, CMD/BAT, or an `apply_patch.bat` wrapper, especially when the patch contains non-ASCII text, double quotes, backslashes, or complex line breaks.

## Confirmed failure

In the verified environment, `apply_patch` was a batch wrapper forwarding arguments to the underlying `codex.exe`. Native Windows argument boundaries changed multiline patch content:

- Passing a multiline patch through `apply_patch.bat` returned exit code 1 and lost the expected patch ending.
- Calling the underlying executable directly from PowerShell returned exit code 0 but removed double quotes from target content.
- A UTF-8 no-BOM temporary patch file read by Python and passed through a `subprocess.run([...])` argument array preserved non-ASCII text, line breaks, and double quotes.

## Verified method

1. Prefer a directly available `apply_patch` tool API.
2. If the available PowerShell entry is an `apply_patch.bat` wrapper using native argument forwarding, do not send the multiline patch body through BAT or CMD.
3. Do not pass a complex multiline patch directly through the Windows PowerShell 5.1 native argument boundary.
4. When no direct tool API exists, write the patch transport file explicitly as UTF-8 without BOM.
5. Read the full patch in Python with `encoding="utf-8"`.
6. Call the underlying patch executor with `subprocess.run` and an argument array so the shell carries only ordinary paths, not the patch body.
7. Keep the temporary file as transport only; the target file must still be changed by the patch executor.
8. After success, re-read the target and verify the actual content rather than trusting only the exit code.

If the verified path fails, report the exact tool boundary, error, file impact, and proposed alternative to the user before trying another transport method.

## Verification criteria

- Patch executor reports success.
- Target file contains exact expected non-ASCII text, quotes, backslashes, and line breaks.
- Patch ending and target diff are intact.
- Relevant file parser or test passes when applicable.
