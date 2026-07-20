#requires -Version 7.0

[CmdletBinding()]
param(
    [switch]$Strict,
    [switch]$RequireOffline
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$pythonPath = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
$hardFailures = [System.Collections.Generic.List[string]]::new()

function Invoke-DiagnosticNativeCommand {
    param(
        [Parameter(Mandatory)]
        [string]$Stage,
        [Parameter(Mandatory)]
        [string]$FilePath,
        [Parameter()]
        [string[]]$Arguments = @()
    )

    $output = @(& $FilePath @Arguments 2>&1)
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        Write-Warning "$Stage failed (exit code $exitCode)."
        return [pscustomobject]@{ Success = $false; Output = @() }
    }
    return [pscustomobject]@{ Success = $true; Output = $output }
}

function Test-LiveDeepSeekEnabled {
    $value = [Environment]::GetEnvironmentVariable(
        "RUN_LIVE_DEEPSEEK_TEST",
        [EnvironmentVariableTarget]::Process
    )
    return $null -ne $value -and $value.Trim().ToLowerInvariant() -in @("1", "true", "yes", "on")
}

function Test-ProcessEnvironmentVariablePresent {
    param(
        [Parameter(Mandatory)]
        [string]$VariableName
    )

    $value = [Environment]::GetEnvironmentVariable(
        $VariableName,
        [EnvironmentVariableTarget]::Process
    )

    return $null -ne $value
}

function Get-SafeDatabaseInfo {
    param(
        [Parameter(Mandatory)]
        [ValidateSet("TEST_DATABASE_URL", "DATABASE_URL")]
        [string]$VariableName
    )

    $parser = @'
import json
import os
import sys

from sqlalchemy.engine import make_url

try:
    raw = os.environ[sys.argv[1]]
    if not raw:
        raise ValueError("empty URL")
    parsed = make_url(raw)
    print(json.dumps({"valid": True, "driver": parsed.drivername, "database": parsed.database}))
except Exception:
    print(json.dumps({"valid": False}))
'@
    $result = Invoke-DiagnosticNativeCommand `
        -Stage "Parse $VariableName safely" `
        -FilePath $pythonPath `
        -Arguments @("-c", $parser, $VariableName)
    if (-not $result.Success -or $result.Output.Count -ne 1) {
        return [pscustomobject]@{ Valid = $false }
    }
    try {
        $parsed = $result.Output[0].ToString() | ConvertFrom-Json
        if (-not $parsed.valid) {
            return [pscustomobject]@{ Valid = $false }
        }
        return [pscustomobject]@{
            Valid = $true
            Driver = [string]$parsed.driver
            Database = if ($null -eq $parsed.database) { "(none)" } else { [string]$parsed.database }
        }
    }
    catch {
        return [pscustomobject]@{ Valid = $false }
    }
}

function Write-DatabaseVariableStatus {
    param(
    [Parameter(Mandatory)]
    [ValidateSet("TEST_DATABASE_URL", "DATABASE_URL")]
    [string]$VariableName,

    [Parameter()]
    [switch]$PresenceOnly
)

    $value = [Environment]::GetEnvironmentVariable(
        $VariableName,
        [EnvironmentVariableTarget]::Process
    )
    if ($null -eq $value) {
        Write-Host "  ${VariableName}: missing"
        return
    }

    Write-Host "  ${VariableName}: present"
    if ($PresenceOnly) {
        return
    }
    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        Write-Host "    URL details: unavailable (.venv interpreter missing)"
        return
    }
    $info = Get-SafeDatabaseInfo -VariableName $VariableName
    if (-not $info.Valid) {
        Write-Host "    URL details: invalid format"
        return
    }
    Write-Host "    driver: $($info.Driver)"
    Write-Host "    database: $($info.Database)"
}

Write-Host "Deviation Protocol development doctor"
Write-Host "Repository: $repositoryRoot"
Write-Host ""

Write-Host "[PowerShell]"
if ($PSVersionTable.PSVersion.Major -lt 7) {
    Write-Host "  failed: PowerShell 7 or newer is required."
    $hardFailures.Add("PowerShell 7+")
}
else {
    Write-Host "  version: $($PSVersionTable.PSVersion)"
}

Write-Host "[Python toolchain]"
$pythonReady = Test-Path -LiteralPath $pythonPath -PathType Leaf
if (-not $pythonReady) {
    Write-Host "  .venv interpreter: missing"
    $hardFailures.Add(".venv interpreter")
}
else {
    Write-Host "  .venv interpreter: present"
    $versionCheck = Invoke-DiagnosticNativeCommand `
        -Stage "Python version check" `
        -FilePath $pythonPath `
        -Arguments @("-c", "import sys; print('.'.join(map(str, sys.version_info[:3]))); raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 3)")
    if ($versionCheck.Success) {
        Write-Host "  Python version: $($versionCheck.Output[0])"
    }
    else {
        Write-Host "  Python version: required 3.12.x"
        $hardFailures.Add("Python 3.12.x")
    }

    $pytestCheck = Invoke-DiagnosticNativeCommand `
        -Stage "pytest availability check" `
        -FilePath $pythonPath `
        -Arguments @("-m", "pytest", "--version")
    if ($pytestCheck.Success) {
        Write-Host "  pytest: $($pytestCheck.Output -join ' ')"
    }
    else {
        Write-Host "  pytest: unavailable"
        $hardFailures.Add("pytest")
    }
}

Write-Host "[Git]"
$gitCommand = Get-Command git -ErrorAction SilentlyContinue
if ($null -eq $gitCommand) {
    Write-Host "  Git: unavailable"
}
else {
    $branchResult = Invoke-DiagnosticNativeCommand -Stage "Git branch check" -FilePath $gitCommand.Source -Arguments @("-C", $repositoryRoot, "branch", "--show-current")
    $statusResult = Invoke-DiagnosticNativeCommand -Stage "Git worktree check" -FilePath $gitCommand.Source -Arguments @("-C", $repositoryRoot, "status", "--porcelain=v1")
    if ($branchResult.Success -and $statusResult.Success) {
        $branch = if ($branchResult.Output.Count -eq 0) { "(detached)" } else { $branchResult.Output[0].ToString() }
        $staged = 0
        $modified = 0
        $untracked = 0
        foreach ($lineObject in $statusResult.Output) {
            $line = $lineObject.ToString()
            if ($line.StartsWith("??")) {
                $untracked++
                continue
            }
            if ($line.Length -ge 2) {
                if ($line[0] -ne ' ') { $staged++ }
                if ($line[1] -ne ' ') { $modified++ }
            }
        }
        Write-Host "  branch: $branch"
        Write-Host "  staged: $staged"
        Write-Host "  modified: $modified"
        Write-Host "  untracked: $untracked"
    }
}

Write-Host "[Environment]"

Write-DatabaseVariableStatus `
    -VariableName "TEST_DATABASE_URL" `
    -PresenceOnly:$RequireOffline

Write-DatabaseVariableStatus `
    -VariableName "DATABASE_URL" `
    -PresenceOnly:$RequireOffline

$deepSeekKeyPresent = Test-ProcessEnvironmentVariablePresent `
    -VariableName "DEEPSEEK_API_KEY"

$liveVariablePresent = Test-ProcessEnvironmentVariablePresent `
    -VariableName "RUN_LIVE_DEEPSEEK_TEST"

$liveVariableStatus = if (-not $liveVariablePresent) {
    "missing"
}
elseif (Test-LiveDeepSeekEnabled) {
    "present (enabled)"
}
else {
    "present (disabled)"
}

Write-Host "  DEEPSEEK_API_KEY: $(if ($deepSeekKeyPresent) { 'present' } else { 'missing' })"
Write-Host "  RUN_LIVE_DEEPSEEK_TEST: $liveVariableStatus"

$offlineVariableNames = @(
    "TEST_DATABASE_URL",
    "DATABASE_URL",
    "DEEPSEEK_API_KEY",
    "RUN_LIVE_DEEPSEEK_TEST"
)

$offlineViolations = @(
    foreach ($offlineVariableName in $offlineVariableNames) {
        if (Test-ProcessEnvironmentVariablePresent -VariableName $offlineVariableName) {
            $offlineVariableName
        }
    }
)

if ($RequireOffline) {
    if ($offlineViolations.Count -eq 0) {
        Write-Host "  offline requirement: satisfied"
    }
    else {
        Write-Host "  offline requirement: failed"
    }
}

if ($RequireOffline -and $offlineViolations.Count -gt 0) {
    [Console]::Error.WriteLine(
        "Offline diagnostics failed: prohibited process environment variables are present: $($offlineViolations -join ', ')."
    )
    exit 1
}

Write-Host "[Alembic offline metadata]"
if ($pythonReady) {
    Push-Location -LiteralPath $repositoryRoot
    try {
        $heads = Invoke-DiagnosticNativeCommand -Stage "Alembic heads" -FilePath $pythonPath -Arguments @("-m", "alembic", "heads")
        if ($heads.Success) {
            foreach ($line in $heads.Output) { Write-Host "  $line" }
        }
        $history = Invoke-DiagnosticNativeCommand -Stage "Alembic history" -FilePath $pythonPath -Arguments @("-m", "alembic", "history")
        if ($history.Success) {
            foreach ($line in $history.Output) { Write-Host "  $line" }
        }
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "  unavailable (.venv interpreter missing)"
}

Write-Host ""
if ($Strict -and $hardFailures.Count -gt 0) {
    [Console]::Error.WriteLine("Strict diagnostics failed: $($hardFailures -join ', ').")
    exit 1
}
Write-Host "Doctor completed$(if ($hardFailures.Count -gt 0) { ' with toolchain warnings' } else { ' successfully' })."
exit 0
