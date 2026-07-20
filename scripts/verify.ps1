#requires -Version 7.0

[CmdletBinding()]
param(
    [Parameter()]
    [ValidateSet("Quick", "Full", "MySQL", "Security", "Offline")]
    [string]$Mode = "Quick",

    [Parameter(DontShow)]
    [switch]$OfflineChild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom

$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$pythonPath = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
$doctorPath = Join-Path $repositoryRoot "scripts\doctor.ps1"

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory)]
        [string]$Stage,
        [Parameter(Mandatory)]
        [string]$FilePath,
        [Parameter()]
        [string[]]$Arguments = @(),
        [switch]$CaptureOutput
    )

    Write-Host "==> $Stage"
    if ($CaptureOutput) {
        $output = @(& $FilePath @Arguments 2>&1)
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            throw "$Stage failed (exit code $exitCode)."
        }
        return $output
    }

    # Let PowerShell forward native stdout and stderr as the process runs.  A
    # ProcessStartInfo with inherited handles can deadlock in piped hosts while
    # WaitForExit is blocking, which made MySQL verification appear to hang.
    & $FilePath @Arguments 2>&1 | ForEach-Object { Write-Host $_ }
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "$Stage failed (exit code $exitCode)."
    }
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

function Get-OfflineVariableNames {
    return @(
        "TEST_DATABASE_URL",
        "DATABASE_URL",
        "DEEPSEEK_API_KEY",
        "RUN_LIVE_DEEPSEEK_TEST"
    )
}

function Assert-OfflineEnvironment {
    $violations = @(
        foreach ($variableName in Get-OfflineVariableNames) {
            if (Test-ProcessEnvironmentVariablePresent -VariableName $variableName) {
                $variableName
            }
        }
    )

    if ($violations.Count -gt 0) {
        throw "Offline child inherited prohibited environment variables: $($violations -join ', ')."
    }

    Write-Host "Offline child environment: database, Provider, and live-test variables are absent."
}

function Get-PowerShellExecutablePath {
    $executableName = if ($IsWindows) {
        "pwsh.exe"
    }
    else {
        "pwsh"
    }

    $pwshPath = Join-Path $PSHOME $executableName

    if (-not (Test-Path -LiteralPath $pwshPath -PathType Leaf)) {
        throw "Unable to locate the current PowerShell 7 executable."
    }

    return $pwshPath
}

function Invoke-OfflineChildProcess {
    $pwshPath = Get-PowerShellExecutablePath

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $pwshPath
    $startInfo.UseShellExecute = $false
    $startInfo.WorkingDirectory = $repositoryRoot

    [void]$startInfo.ArgumentList.Add("-NoLogo")
    [void]$startInfo.ArgumentList.Add("-NoProfile")
    [void]$startInfo.ArgumentList.Add("-File")
    [void]$startInfo.ArgumentList.Add($PSCommandPath)
    [void]$startInfo.ArgumentList.Add("-Mode")
    [void]$startInfo.ArgumentList.Add("Offline")
    [void]$startInfo.ArgumentList.Add("-OfflineChild")

    foreach ($variableName in Get-OfflineVariableNames) {
        [void]$startInfo.Environment.Remove($variableName)
    }

    Write-Host "==> Starting isolated Offline verification child process"

    $process = [System.Diagnostics.Process]::Start($startInfo)
    if ($null -eq $process) {
        throw "Failed to start the Offline verification child process."
    }

    try {
        $process.WaitForExit()
        return [int]$process.ExitCode
    }
    finally {
        $process.Dispose()
    }
}

function Get-SafeTestDatabaseInfo {
    $value = [Environment]::GetEnvironmentVariable(
        "TEST_DATABASE_URL",
        [EnvironmentVariableTarget]::Process
    )
    if ($null -eq $value) {
        return $null
    }

    $parser = @'
import json
import os

from sqlalchemy.engine import make_url

try:
    raw = os.environ["TEST_DATABASE_URL"]
    if not raw:
        raise ValueError("empty URL")
    parsed = make_url(raw)
    print(json.dumps({"valid": True, "driver": parsed.drivername, "database": parsed.database}))
except Exception:
    print(json.dumps({"valid": False}))
'@
    $output = @(Invoke-NativeCommand `
        -Stage "Parse TEST_DATABASE_URL safely" `
        -FilePath $pythonPath `
        -Arguments @("-c", $parser) `
        -CaptureOutput)
    if ($output.Count -ne 1) {
        throw "TEST_DATABASE_URL parsing returned an invalid result."
    }
    try {
        $parsed = $output[0].ToString() | ConvertFrom-Json
    }
    catch {
        throw "TEST_DATABASE_URL parsing returned an invalid result."
    }
    if (-not $parsed.valid) {
        throw "TEST_DATABASE_URL has an invalid format."
    }
    return [pscustomobject]@{
        Driver = [string]$parsed.driver
        Database = if ($null -eq $parsed.database) { "(none)" } else { [string]$parsed.database }
    }
}

function Assert-SafeTestDatabase {
    param(
        [Parameter(Mandatory)]
        [bool]$Required
    )

    $info = Get-SafeTestDatabaseInfo
    if ($null -eq $info) {
        if ($Required) {
            throw "TEST_DATABASE_URL is missing; MySQL verification requires the explicit test database."
        }
        Write-Host "TEST_DATABASE_URL: missing (integration tests may use their existing skip behavior)."
        return
    }
    Write-Host "TEST_DATABASE_URL driver: $($info.Driver)"
    Write-Host "TEST_DATABASE_URL database: $($info.Database)"
    if ($info.Driver -cne "mysql+asyncmy" -or $info.Database -cne "deviation_protocol_test") {
        throw "TEST_DATABASE_URL is not the allowed mysql+asyncmy deviation_protocol_test database."
    }
}

function Assert-Environment {
    if ($PSVersionTable.PSVersion.Major -lt 7) {
        throw "PowerShell 7 or newer is required."
    }
    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        throw "The repository .venv interpreter is missing."
    }
    $gitCommand = Get-Command git -ErrorAction SilentlyContinue
    if ($null -eq $gitCommand) {
        throw "Git is required for verification."
    }
    Invoke-NativeCommand `
        -Stage "Python 3.12 check" `
        -FilePath $pythonPath `
        -Arguments @("-c", "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 3)")
    Invoke-NativeCommand `
        -Stage "pytest availability check" `
        -FilePath $pythonPath `
        -Arguments @("-m", "pytest", "--version")
    return $gitCommand.Source
}

function Invoke-CompileAll {
    Invoke-NativeCommand -Stage "compileall" -FilePath $pythonPath -Arguments @("-m", "compileall", "-q", "src", "tests", "alembic")
}

function Invoke-PipCheck {
    Invoke-NativeCommand -Stage "pip check" -FilePath $pythonPath -Arguments @("-m", "pip", "check")
}

function Invoke-AlembicMetadataChecks {
    Invoke-NativeCommand -Stage "Alembic heads" -FilePath $pythonPath -Arguments @("-m", "alembic", "heads")
    Invoke-NativeCommand -Stage "Alembic history" -FilePath $pythonPath -Arguments @("-m", "alembic", "history")
}

function Invoke-GitDiffCheck {
    param(
        [Parameter(Mandatory)]
        [string]$GitPath
    )
    Invoke-NativeCommand -Stage "git diff --check" -FilePath $GitPath -Arguments @("diff", "--check")
}

try {
    Write-Host "Deviation Protocol verification mode: $Mode"

    if ($OfflineChild -and $Mode -ne "Offline") {
        throw "-OfflineChild is valid only with -Mode Offline."
    }

    if ($Mode -eq "Offline" -and -not $OfflineChild) {
        $offlineExitCode = Invoke-OfflineChildProcess

        if ($offlineExitCode -ne 0) {
            throw "Offline verification child failed (exit code $offlineExitCode)."
        }

        Write-Host "Verification completed successfully: Offline"
        exit 0
    }

    if (Test-LiveDeepSeekEnabled) {
        throw "RUN_LIVE_DEEPSEEK_TEST is enabled; ordinary verification refuses to run."
    }

    if ($Mode -eq "Offline") {
        Assert-OfflineEnvironment
    }

    $gitPath = Assert-Environment
    Push-Location -LiteralPath $repositoryRoot
    try {
        switch ($Mode) {
            "Quick" {
                Invoke-CompileAll
                Invoke-NativeCommand -Stage "unit tests" -FilePath $pythonPath -Arguments @("-m", "pytest", "tests/unit", "-q")
                Invoke-GitDiffCheck -GitPath $gitPath
            }
            "Full" {
                Assert-SafeTestDatabase -Required $false
                Invoke-NativeCommand -Stage "full pytest" -FilePath $pythonPath -Arguments @("-m", "pytest")
                Invoke-CompileAll
                Invoke-PipCheck
                Invoke-AlembicMetadataChecks
                Invoke-GitDiffCheck -GitPath $gitPath
            }
            "MySQL" {
                Assert-SafeTestDatabase -Required $true
                Invoke-NativeCommand -Stage "MySQL integration tests" -FilePath $pythonPath -Arguments @("-m", "pytest", "tests/integration", "-q")
                Invoke-CompileAll
                Invoke-PipCheck
                Invoke-AlembicMetadataChecks
                Write-Host "==> Alembic online current/check skipped: alembic/env.py has no TEST_DATABASE_URL-only entry point."
                Invoke-GitDiffCheck -GitPath $gitPath
            }
            "Security" {
                Write-Host "Security verification uses an explicit tracked-file test list; it does not perform a broad text scan."
                $securityTestFiles = @(
                    "tests/unit/test_action_gateway.py",
                    "tests/unit/test_content_catalog.py",
                    "tests/unit/test_database_configuration.py",
                    "tests/unit/test_narrative_provider.py",
                    "tests/unit/test_scenario_catalog.py",
                    "tests/unit/test_story_mutations.py"
                )
                $securityArguments = @("-B", "-m", "pytest", "-p", "no:cacheprovider") + $securityTestFiles + @("-q")
                Invoke-NativeCommand -Stage "security and architecture unit tests" -FilePath $pythonPath -Arguments $securityArguments
                Write-Host "Dedicated dependency-direction lint: unavailable (no stable repository check exists)."
                Write-Host "Dedicated dynamic-execution lint: unavailable (no stable repository check exists)."
                Invoke-GitDiffCheck -GitPath $gitPath
            }
            "Offline" {
                Assert-OfflineEnvironment

                $pwshPath = Get-PowerShellExecutablePath

                Invoke-NativeCommand `
                    -Stage "offline doctor diagnostics" `
                    -FilePath $pwshPath `
                    -Arguments @(
                        "-NoLogo",
                        "-NoProfile",
                        "-File",
                        $doctorPath,
                        "-Strict",
                        "-RequireOffline"
                    )

                Invoke-NativeCommand `
                    -Stage "full offline pytest" `
                    -FilePath $pythonPath `
                    -Arguments @("-m", "pytest")

                Invoke-CompileAll
                Invoke-PipCheck
                Invoke-AlembicMetadataChecks
                Invoke-GitDiffCheck -GitPath $gitPath

                Write-Host "Offline verification ran without database, Provider, or live-test environment variables."
                Write-Host "MySQL integration and live Provider tests used their existing skip guards."
            }
        }
    }
    finally {
        Pop-Location
    }
    Write-Host "Verification completed successfully: $Mode"
    exit 0
}
catch {
    [Console]::Error.WriteLine("Verification failed during mode ${Mode}: $($_.Exception.Message)")
    exit 1
}
