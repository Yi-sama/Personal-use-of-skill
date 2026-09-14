# Case 004: WMI/CIM cannot provide a process command line

CASE-HASH: ea543e17f995

## Problem

`Get-CimInstance -ClassName Win32_Process` can fail with `HRESULT 0x80041010` (invalid class). In that state, a process command-line lookup is unavailable through the WMI/CIM path even when the target PID exists.

## Verified environment result

On the current Windows host, querying `Win32_Process` fails with `HRESULT 0x80041010`. The same HRESULT is also produced by an intentionally nonexistent class. `Get-Process` still returns the current process identity and executable path, but it does not expose the complete command line.

Run:

```powershell
& '.\work\wmi-case-004\test-wmi-commandline-unavailable.ps1'
```

The test starts a disposable child PowerShell process, queries its WMI/CIM command line, verifies the invalid-class control, checks the `Get-Process` fallback identity, saves UTF-8 JSON, stops the child process, and reports `WMI_COMMANDLINE_TEST=PASS`.

## Cause and scope

`0x80041010` proves that the queried WMI class is unavailable to the current query path. It does not by itself identify the root cause. Possible causes include missing or unhealthy WMI provider registration, OS image changes, service state, or policy. Do not diagnose a target application from this error alone.

## Required method

1. Capture the full `FullyQualifiedErrorId`, including its HRESULT, rather than reporting only a null command-line value.
2. Fall back to `Get-Process -Id <pid>` for PID, process name, executable path, and start time.
3. Mark the full command line as unavailable when no verified provider returns it; do not fabricate it from the executable path.
4. For a process started by the current automation, retain the launch arguments at creation time instead of querying them later.
5. Do not repair WMI, modify services, or change system policy as part of an application-level investigation without separate authorization.

## Verification standard

- The invalid-class control returns `0x80041010`.
- The normal `Win32_Process` query is classified as available or unavailable from its actual result.
- The fallback returns the disposable child PID and a nonempty process name.
- The child process is stopped after the test.
- The JSON result preserves the error identifier and fallback fields for later inspection.
