#requires -Version 7.0
[CmdletBinding()]
param(
    [ValidateSet('Inspect', 'Ensure', 'Test', 'Run')]
    [string]$Mode = 'Inspect',
    [string]$V2rayNPath,
    [string]$NodeName = 'US-owner-unlimited',
    [string]$Url,
    [string]$FilePath,
    [string[]]$CommandArgs = @()
)

$ErrorActionPreference = 'Stop'
$inspector = Join-Path $PSScriptRoot 'inspect_v2rayn.py'

function Resolve-V2rayNPath {
    param([string]$ExplicitPath)
    if ($ExplicitPath) { return (Resolve-Path -LiteralPath $ExplicitPath).Path }
    $processes = @(Get-Process -Name v2rayN -ErrorAction SilentlyContinue)
    $paths = @($processes | ForEach-Object Path | Where-Object { $_ } | Select-Object -Unique)
    if ($paths.Count -gt 1) { throw 'More than one v2rayN installation is running; specify -V2rayNPath.' }
    if ($paths.Count -eq 1) { return $paths[0] }
    if ($env:V2RAYN_PATH) { return (Resolve-Path -LiteralPath $env:V2RAYN_PATH).Path }
    $settingsPath = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Codex\v2rayn-proxy\settings.json'
    if (Test-Path -LiteralPath $settingsPath) {
        $settings = Get-Content -LiteralPath $settingsPath -Raw -Encoding utf8 | ConvertFrom-Json
        if ($settings.v2rayn_path) { return (Resolve-Path -LiteralPath $settings.v2rayn_path).Path }
    }
    throw 'v2rayN was not found. Supply -V2rayNPath or set V2RAYN_PATH.'
}

function Get-V2rayNState {
    param([string]$ExePath, [string]$ExpectedNode)
    $python = (Get-Command python.exe -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
    $json = & $python -B $inspector (Split-Path -Parent $ExePath) --node $ExpectedNode
    if ($LASTEXITCODE -ne 0) { throw 'v2rayN metadata inspection failed; see the non-secret diagnostic above.' }
    $state = ($json -join "`n") | ConvertFrom-Json
    $running = @(Get-Process -Name v2rayN -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $ExePath })
    $listening = @()
    if ($state.port) {
        $listening = @(Get-NetTCPConnection -State Listen -ErrorAction Stop |
            Where-Object { $_.LocalPort -eq $state.port -and $_.LocalAddress -eq $state.listen_host })
    }
    $expectedCores = @(
        (Join-Path (Split-Path -Parent $ExePath) 'bin\xray\xray.exe'),
        (Join-Path (Split-Path -Parent $ExePath) 'bin\sing_box\sing-box.exe')
    )
    $coreOwned = @($listening | Where-Object {
        $owner = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
        $owner -and $owner.Path -in $expectedCores
    })
    $state | Add-Member NoteProperty app_running ($running.Count -gt 0)
    $state | Add-Member NoteProperty listener_ready ($listening.Count -gt 0)
    $state | Add-Member NoteProperty listener_owned_by_core ($coreOwned.Count -gt 0)
    $state | Add-Member NoteProperty ready (
        $state.app_running -and $state.configured_for_expected -and
        ($state.core_matches_expected -ne $false) -and $state.listener_owned_by_core -and [bool]$state.http_proxy
    )
    $state
}

function Select-V2rayNNode {
    param([string]$ExePath, [string]$ExpectedNode)
    Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
    # A second launch signals the existing v2rayN instance to show its window.
    Start-Process -FilePath $ExePath -WorkingDirectory (Split-Path -Parent $ExePath) -WindowStyle Hidden | Out-Null
    $deadline = [DateTime]::UtcNow.AddSeconds(12)
    $window = $null
    do {
        $process = Get-Process -Name v2rayN | Where-Object { $_.Path -eq $ExePath } | Select-Object -First 1
        $condition = [System.Windows.Automation.PropertyCondition]::new(
            [System.Windows.Automation.AutomationElement]::ProcessIdProperty, $process.Id)
        $window = [System.Windows.Automation.AutomationElement]::RootElement.FindFirst(
            [System.Windows.Automation.TreeScope]::Children, $condition)
        if (-not $window) { Start-Sleep -Milliseconds 200 }
    } until ($window -or [DateTime]::UtcNow -ge $deadline)
    if (-not $window) { throw 'The v2rayN window is unavailable to Windows UI Automation.' }
    $gridCondition = [System.Windows.Automation.PropertyCondition]::new(
        [System.Windows.Automation.AutomationElement]::AutomationIdProperty, 'lstProfiles')
    $grid = $window.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $gridCondition)
    if (-not $grid) { throw 'The supported v2rayN profile grid was not found; no node was changed.' }
    $nameCondition = [System.Windows.Automation.PropertyCondition]::new(
        [System.Windows.Automation.AutomationElement]::NameProperty, $ExpectedNode)
    $items = $grid.FindAll([System.Windows.Automation.TreeScope]::Descendants, $nameCondition)
    $rows = @{}
    foreach ($item in $items) {
        $row = $item
        while ($row -and $row.Current.ControlType -ne [System.Windows.Automation.ControlType]::DataItem) {
            $row = [System.Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($row)
        }
        if ($row) { $rows[($row.GetRuntimeId() -join '.')] = $row }
    }
    if ($rows.Count -ne 1) {
        throw 'The exact node must be uniquely visible in the profile grid. No node was changed.'
    }
    $row = @($rows.Values)[0]
    $selection = $row.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern)
    $selection.Select()
    $shell = New-Object -ComObject WScript.Shell
    if (-not $shell.AppActivate($process.Id)) { throw 'v2rayN could not be activated; no activation key was sent.' }
    $grid.SetFocus()
    $focused = [System.Windows.Automation.AutomationElement]::FocusedElement
    if ($focused.Current.ProcessId -ne $process.Id -or -not $selection.Current.IsSelected) {
        throw 'v2rayN did not receive selection/focus; no activation key was sent.'
    }
    # Enter activates the selected profile in v2rayN 7.18; double-click can edit it.
    $shell.SendKeys('{ENTER}')
}

function Ensure-V2rayN {
    param([string]$ExePath, [string]$ExpectedNode)
    $mutex = [System.Threading.Mutex]::new($false, 'Local\CodexV2rayNNodeSelection')
    $locked = $false
    try {
        $locked = $mutex.WaitOne(15000)
        if (-not $locked) { throw 'Another controller is changing v2rayN; node selection was not attempted.' }
        $state = Get-V2rayNState $ExePath $ExpectedNode
        $originalNode = $state.active_node
        if (-not $state.app_running) {
            Start-Process -FilePath $ExePath -WorkingDirectory (Split-Path -Parent $ExePath) -WindowStyle Hidden | Out-Null
            $deadline = [DateTime]::UtcNow.AddSeconds(12)
            do {
                Start-Sleep -Milliseconds 250
                $state = Get-V2rayNState $ExePath $ExpectedNode
            } until ($state.ready -or ($state.app_running -and -not $state.configured_for_expected) -or
                [DateTime]::UtcNow -ge $deadline)
        }
        if (-not $state.configured_for_expected) {
            Select-V2rayNNode $ExePath $ExpectedNode
            $deadline = [DateTime]::UtcNow.AddSeconds(12)
            do {
                Start-Sleep -Milliseconds 250
                $state = Get-V2rayNState $ExePath $ExpectedNode
            } until ($state.ready -or [DateTime]::UtcNow -ge $deadline)
        }
        if (-not $state.ready) { throw 'The expected node and its core-owned local listener are not ready, or the generated core contradicts them.' }
        $state | Add-Member NoteProperty original_node $originalNode
        $state | Add-Member NoteProperty node_changed ($originalNode -ne $state.active_node)
        $state
    } finally {
        if ($locked) { $mutex.ReleaseMutex() }
        $mutex.Dispose()
    }
}

function Test-ProxyTarget {
    param($State, [string]$TargetUrl)
    if (-not $State.ready) { throw 'Proxy not ready. Run Inspect, then Ensure if authorized.' }
    $uri = $null
    if (-not [Uri]::TryCreate($TargetUrl, [UriKind]::Absolute, [ref]$uri) -or
        $uri.Scheme -notin @('http','https') -or $uri.UserInfo) {
        throw 'Supply an absolute HTTP(S) URL without embedded credentials.'
    }
    $status = & curl.exe --silent --show-error --noproxy '' --proxy $State.http_proxy `
        --connect-timeout 8 --max-time 25 --output NUL --write-out '%{http_code}' --url $TargetUrl
    if ($LASTEXITCODE -ne 0) { throw "Proxy request failed with curl exit code $LASTEXITCODE." }
    $httpStatus = [int]($status -join '').Trim()
    [pscustomobject]@{
        transport_ok = $true
        http_status = $httpStatus
        http_ok = ($httpStatus -ge 200 -and $httpStatus -lt 400)
        expected_node = $State.expected_node
        proxy = $State.http_proxy
    }
}

function Invoke-ProxyCommand {
    param($State, [string]$Executable, [string[]]$Arguments)
    if (-not $State.ready) { throw 'Proxy not ready. Run Inspect, then Ensure if authorized.' }
    $command = Get-Command $Executable -CommandType Application -ErrorAction Stop | Select-Object -First 1
    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $command.Source
    $startInfo.UseShellExecute = $false
    foreach ($argument in $Arguments) { $startInfo.ArgumentList.Add($argument) }
    foreach ($key in @('HTTP_PROXY','HTTPS_PROXY','http_proxy','https_proxy')) {
        $startInfo.Environment[$key] = $State.http_proxy
    }
    foreach ($key in @('ALL_PROXY','all_proxy')) {
        $startInfo.Environment[$key] = if ($State.socks_proxy) { $State.socks_proxy } else { $State.http_proxy }
    }
    $bypass = (@($env:NO_PROXY, $env:no_proxy, 'localhost,127.0.0.1,::1') |
        Where-Object { $_ }) -join ','
    $startInfo.Environment['NO_PROXY'] = $bypass
    $startInfo.Environment['no_proxy'] = $bypass
    $process = [System.Diagnostics.Process]::Start($startInfo)
    try {
        $process.WaitForExit()
        $process.ExitCode
    } finally {
        $process.Dispose()
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    try {
        $exe = Resolve-V2rayNPath $V2rayNPath
        if ($Mode -eq 'Ensure') {
            Ensure-V2rayN $exe $NodeName | ConvertTo-Json
        } else {
            $state = Get-V2rayNState $exe $NodeName
            switch ($Mode) {
                'Inspect' { $state | ConvertTo-Json }
                'Test' { Test-ProxyTarget $state $Url | ConvertTo-Json }
                'Run' {
                    if (-not $FilePath) { throw 'Run requires -FilePath.' }
                    $code = Invoke-ProxyCommand $state $FilePath $CommandArgs
                    exit $code
                }
            }
        }
    } catch {
        Write-Error $_ -ErrorAction Continue
        exit 1
    }
}
