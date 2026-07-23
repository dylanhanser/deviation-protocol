#requires -Version 7.0

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom

Add-Type -TypeDefinition @'
using System;

namespace DeviationProtocol
{
    public sealed class DemoCancelState
    {
        public volatile bool StopRequested;

        public void HandleCancel(object sender, ConsoleCancelEventArgs eventArgs)
        {
            eventArgs.Cancel = true;
            StopRequested = true;
        }
    }
}
'@

function Get-ValidatedComSpec {
    $comSpec = [Environment]::GetEnvironmentVariable(
        "ComSpec",
        [EnvironmentVariableTarget]::Process
    )
    if ([string]::IsNullOrWhiteSpace($comSpec)) {
        throw "ComSpec is required."
    }
    if (-not [IO.Path]::IsPathFullyQualified($comSpec)) {
        throw "ComSpec must be an absolute path."
    }

    try {
        $item = Get-Item -LiteralPath $comSpec -Force -ErrorAction Stop
    }
    catch {
        throw "ComSpec does not resolve to an existing file."
    }
    if (
        $item -isnot [IO.FileInfo] -or
        -not $item.Exists -or
        -not $item.Name.Equals("cmd.exe", [StringComparison]::OrdinalIgnoreCase)
    ) {
        throw "ComSpec must resolve to cmd.exe."
    }
    return $item.FullName
}

function Assert-SafeBatchPath {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    foreach ($character in $Path.ToCharArray()) {
        if ([char]::IsControl($character)) {
            throw "The resolved npm.cmd path contains unsafe characters."
        }
    }
    if ($Path.IndexOfAny([char[]]'"%!^&|<>()') -ge 0) {
        throw "The resolved npm.cmd path contains unsafe characters."
    }
}

function Get-ValidatedNpmCmd {
    $npmCommands = @(
        Get-Command -Name "npm.cmd" -CommandType Application -All -ErrorAction Stop
    )
    if ($npmCommands.Count -ne 1) {
        throw "Exactly one npm.cmd Application must resolve."
    }

    $command = $npmCommands[0]
    if (
        $command.CommandType -ne [Management.Automation.CommandTypes]::Application -or
        [string]::IsNullOrWhiteSpace($command.Path) -or
        -not [IO.Path]::IsPathFullyQualified($command.Path)
    ) {
        throw "npm.cmd must resolve to one absolute Application path."
    }
    try {
        $item = Get-Item -LiteralPath $command.Path -Force -ErrorAction Stop
    }
    catch {
        throw "npm.cmd does not resolve to an existing file."
    }
    if (
        $item -isnot [IO.FileInfo] -or
        -not $item.Exists -or
        -not $item.Extension.Equals(".cmd", [StringComparison]::OrdinalIgnoreCase) -or
        -not $item.Name.Equals("npm.cmd", [StringComparison]::OrdinalIgnoreCase)
    ) {
        throw "npm.cmd must resolve to an npm.cmd file."
    }
    Assert-SafeBatchPath -Path $item.FullName
    return $item.FullName
}

function Assert-AvailableLoopbackPort {
    param(
        [Parameter(Mandatory)]
        [int]$Port
    )

    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $Port)
    try {
        $listener.Start()
    }
    catch {
        throw "Required loopback port $Port is already occupied or unavailable."
    }
    finally {
        $listener.Stop()
    }
}

function Remove-SensitiveChildEnvironment {
    param(
        [Parameter(Mandatory)]
        [Diagnostics.ProcessStartInfo]$StartInfo
    )

    $names = @($StartInfo.Environment.Keys)
    foreach ($name in $names) {
        if (
            $name.Equals("DATABASE_URL", [StringComparison]::OrdinalIgnoreCase) -or
            $name.Equals("TEST_DATABASE_URL", [StringComparison]::OrdinalIgnoreCase) -or
            $name.Equals("RUN_LIVE_DEEPSEEK_TEST", [StringComparison]::OrdinalIgnoreCase) -or
            $name.Equals(
                "DEVIATION_DEMO_SCENARIO_RESPONSE_FILE",
                [StringComparison]::OrdinalIgnoreCase
            ) -or
            $name.StartsWith("DEEPSEEK_", [StringComparison]::OrdinalIgnoreCase)
        ) {
            [void]$StartInfo.Environment.Remove($name)
        }
    }
}

function Stop-OwnedProcessTree {
    param(
        [Parameter(Mandatory)]
        [Diagnostics.Process]$Process
    )

    try {
        if (-not $Process.HasExited) {
            $Process.Kill($true)
        }
        if (-not $Process.WaitForExit(10000)) {
            throw "An owned child process did not terminate."
        }
    }
    finally {
        $Process.Dispose()
    }
}

$repositoryRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$webRoot = [IO.Path]::GetFullPath((Join-Path $repositoryRoot "web"))
$pythonPath = [IO.Path]::GetFullPath(
    (Join-Path $repositoryRoot ".venv\Scripts\python.exe")
)
$ownedProcesses = [Collections.Generic.List[Diagnostics.Process]]::new()
$failure = $null
$cancelHandler = $null
$cancelState = [DeviationProtocol.DemoCancelState]::new()

try {
    if ($PSVersionTable.PSVersion.Major -lt 7) {
        throw "PowerShell 7 or later is required."
    }
    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        throw "The repository .venv Python executable is missing."
    }
    if (-not (Test-Path -LiteralPath $webRoot -PathType Container)) {
        throw "The Web project directory is missing."
    }
    if (-not (Test-Path -LiteralPath (Join-Path $webRoot "package.json") -PathType Leaf)) {
        throw "web/package.json is missing."
    }
    if (-not (Test-Path -LiteralPath (Join-Path $webRoot "node_modules") -PathType Container)) {
        throw "web/node_modules is missing. Install dependencies separately before launch."
    }

    $cmdPath = Get-ValidatedComSpec
    $npmCmdPath = Get-ValidatedNpmCmd
    Assert-AvailableLoopbackPort -Port 8000
    Assert-AvailableLoopbackPort -Port 5173

    $backendStartInfo = [Diagnostics.ProcessStartInfo]::new()
    $backendStartInfo.FileName = $pythonPath
    $backendStartInfo.UseShellExecute = $false
    $backendStartInfo.WorkingDirectory = $repositoryRoot
    foreach ($argument in @(
        "-m",
        "uvicorn",
        "deviation_protocol.api.demo:app",
        "--app-dir",
        "src",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
        "--workers",
        "1"
    )) {
        [void]$backendStartInfo.ArgumentList.Add($argument)
    }
    Remove-SensitiveChildEnvironment -StartInfo $backendStartInfo

    $webStartInfo = [Diagnostics.ProcessStartInfo]::new()
    $webStartInfo.FileName = $cmdPath
    $webStartInfo.UseShellExecute = $false
    $webStartInfo.WorkingDirectory = $webRoot
    $webStartInfo.Arguments =
        '/d /s /c ""' +
        $npmCmdPath +
        '" run dev -- --host 127.0.0.1 --port 5173 --strictPort --mode deterministic-demo"'
    Remove-SensitiveChildEnvironment -StartInfo $webStartInfo
    $webStartInfo.Environment["VITE_APP_MODE"] = "deterministic-demo"

    $backendProcess = [Diagnostics.Process]::Start($backendStartInfo)
    if ($null -eq $backendProcess) {
        throw "Failed to start the Demo backend."
    }
    $ownedProcesses.Add($backendProcess)

    $webProcess = [Diagnostics.Process]::Start($webStartInfo)
    if ($null -eq $webProcess) {
        throw "Failed to start the Demo Web client."
    }
    $ownedProcesses.Add($webProcess)

    $cancelHandler = $cancelState.HandleCancel
    [Console]::add_CancelKeyPress($cancelHandler)

    Write-Host "Deterministic Demo: local only, temporary data, not a production Provider."
    Write-Host "Web: http://127.0.0.1:5173"
    Write-Host "Press Ctrl+C to stop the launcher-owned process trees."

    while (-not $cancelState.StopRequested) {
        foreach ($process in $ownedProcesses) {
            if ($process.HasExited) {
                throw "A launcher-owned child exited unexpectedly with code $($process.ExitCode)."
            }
        }
        Start-Sleep -Milliseconds 200
    }
}
catch {
    $failure = $_.Exception.Message
}
finally {
    if ($null -ne $cancelHandler) {
        [Console]::remove_CancelKeyPress($cancelHandler)
    }
    for ($index = $ownedProcesses.Count - 1; $index -ge 0; $index -= 1) {
        try {
            Stop-OwnedProcessTree -Process $ownedProcesses[$index]
        }
        catch {
            if ($null -eq $failure) {
                $failure = "Launcher cleanup failed: $($_.Exception.Message)"
            }
            else {
                $failure += " Launcher cleanup also failed: $($_.Exception.Message)"
            }
        }
    }
}

if ($null -ne $failure) {
    [Console]::Error.WriteLine("Demo launcher failed: $failure")
    exit 1
}
exit 0
