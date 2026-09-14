# Case 003: FastCtx recursive inspection crosses a permission boundary

CASE-HASH: 5bd54090a30f

## Problem

A broad FastCtx traversal can reach historical runtime, work, or temporary-test directories that the inspection service cannot read. A permission-denied response can prevent that broad inspection from returning the intended project evidence.

## Verified boundary

The reproduction creates one readable file and one subdirectory denied to the current user. The local filesystem negative control confirms that the readable file remains accessible while reading the restricted file fails. FastCtx must then be checked against that fixture manually because the MCP call itself is outside the PowerShell process that creates it.

Run the fixture lifecycle:

```powershell
& '.\work\fastctx-case-003\test-fastctx-permission-boundary.ps1' -Mode Prepare
& '.\work\fastctx-case-003\test-fastctx-permission-boundary.ps1' -Mode Verify
& '.\work\fastctx-case-003\test-fastctx-permission-boundary.ps1' -Mode Cleanup
```

The test writes UTF-8 JSON to `work/fastctx-case-003/result.json` and reports `FASTCTX_PERMISSION_FIXTURE=PASS` only when the accessible file is readable and the restricted file is rejected. Cleanup restores the ACL before deleting the fixture.

## Cause

This is an inspection-boundary failure, not evidence that the application being inspected is broken. The precise reason that a specific directory is unavailable is environment-dependent: ACLs, another security principal, a mounted runtime directory, or a service sandbox can all produce it.

## Required method

1. Do not change permissions, delete the directory, or treat the inaccessible path as project failure merely to make a broad search succeed.
2. Narrow the operation to known relevant files or a known accessible subtree.
3. For direct reads, pass the exact file path. For text search, scope the path and glob to the relevant source files.
4. Report the denied path and the reduced evidence scope.
5. Do not claim that the inaccessible directory was searched successfully.

## Verification standard

- The negative control rejects the restricted file and accepts the readable file.
- An actual FastCtx traversal or read against the prepared fixture records whether it reports denial, skips the path, or returns a partial result.
- A direct FastCtx read of the readable file succeeds after the broad traversal fails or is partial.
- The fixture is cleaned up and no denied ACL remains under the project directory.
