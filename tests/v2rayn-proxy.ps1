#requires -Version 7.0
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$helper = Join-Path $repo '.agents\skills\v2rayn-proxy\scripts\Invoke-V2rayNProxy.ps1'
$tokens = $null
$errors = $null
[void][System.Management.Automation.Language.Parser]::ParseFile($helper, [ref]$tokens, [ref]$errors)
if ($errors.Count) { throw ($errors.Message -join "`n") }
. $helper

$state = [pscustomobject]@{
    ready = $true
    expected_node = 'fixture'
    http_proxy = 'http://127.0.0.1:32123'
    socks_proxy = 'socks5h://127.0.0.1:32123'
}
$before = @{}
foreach ($key in @('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY')) {
    $before[$key] = [Environment]::GetEnvironmentVariable($key)
}
$python = (Get-Command python.exe -CommandType Application | Select-Object -First 1).Source
$source = @'
import os,sys
assert os.environ['HTTP_PROXY'] == 'http://127.0.0.1:32123'
assert os.environ['HTTPS_PROXY'] == 'http://127.0.0.1:32123'
assert os.environ['ALL_PROXY'] == 'socks5h://127.0.0.1:32123'
assert 'localhost' in os.environ['NO_PROXY']
assert sys.argv[1:] == ['argument with spaces', 'literal;&not-a-shell']
sys.exit(17)
'@
$code = Invoke-ProxyCommand $state $python @('-B','-c',$source,'argument with spaces','literal;&not-a-shell')
if ($code -ne 17) { throw "Child exit code was not preserved: $code" }
foreach ($key in $before.Keys) {
    if ([Environment]::GetEnvironmentVariable($key) -cne $before[$key]) {
        throw "Parent environment was modified: $key"
    }
}
$state.ready = $false
$caught = $false
try { [void](Invoke-ProxyCommand $state $python @('-c','raise Exception("must not run")')) }
catch { $caught = $_.Exception.Message -like 'Proxy not ready*' }
if (-not $caught) { throw 'An unverified proxy was not rejected.' }
$state.ready = $true

# Mock curl at the function boundary; these checks never connect to the network.
$script:status = '403'
$script:curlExit = 0
function curl.exe {
    $script:curlArgs = @($args)
    $global:LASTEXITCODE = $script:curlExit
    $script:status
}
$result = Test-ProxyTarget $state 'https://example.invalid/'
if (-not $result.transport_ok -or $result.http_ok -or $result.http_status -ne 403) {
    throw 'HTTP rejection was confused with transport failure.'
}
if ($script:curlArgs -notcontains $state.http_proxy -or $script:curlArgs -notcontains '--noproxy') {
    throw 'The explicit proxy or bypass override was missing.'
}
$script:curlExit = 7
$caught = $false
try { [void](Test-ProxyTarget $state 'https://example.invalid/') }
catch { $caught = $_.Exception.Message -like '*curl exit code 7*' }
if (-not $caught) { throw 'Transport failure was not propagated.' }
$caught = $false
try { [void](Test-ProxyTarget $state 'file:///C:/secret') }
catch { $caught = $_.Exception.Message -like '*absolute HTTP(S)*' }
if (-not $caught) { throw 'Non-HTTP URLs were not rejected.' }
'V2RAYN_PROXY_OFFLINE_CHECK=PASS (child environment/arguments/exit, HTTP rejection, transport failure)'
