# Error Case 0a8f92c4de0d: Explicit UTF-8 for Non-ASCII Text

## Trigger

Use this case when writing or editing non-ASCII text on Windows and any command, API, script, or existing file may depend on GBK, CP936, OEM, locale defaults, or an undeclared encoding.

## Confirmed failure

Windows PowerShell, Python, system locale, console output, and file APIs can use different default encodings. Text written as GBK/CP936 and later read as UTF-8 becomes garbled or fails strict decoding. Changing the console code page with `chcp 65001` does not prove that a file was written as UTF-8.

Observed evidence from the verified case:

- System default encoding was `gb2312` while Python standard output used `gbk`.
- GBK bytes decoded as UTF-8 produced replacement characters or a decoding error.
- Explicit UTF-8 without BOM preserved the tested non-ASCII content exactly.

## Verified method

1. Determine the existing file encoding before modifying an existing file.
2. Preserve UTF-8 when the existing file is UTF-8.
3. For new source, configuration, Markdown, JSON, YAML, script, and ordinary text files, use an API with explicit UTF-8 encoding.
4. Do not rely on `Default`, OEM, GBK, CP936, locale defaults, or console code-page changes unless an external legacy boundary explicitly requires them.
5. After writing, decode the file strictly as UTF-8 and inspect the expected content, replacement characters, BOM policy, and relevant diff.
6. If the format has a parser or compiler, run it after the encoding check.

If this method is not viable because of a confirmed legacy-system requirement, report the boundary and proposed explicit transcoding method to the user before changing approach.

## Verification criteria

- Strict UTF-8 decoding succeeds.
- Expected non-ASCII text is preserved exactly.
- No Unicode replacement character is present.
- BOM matches the project requirement.
- Structured or source files pass their parser, compiler, or syntax check when applicable.
