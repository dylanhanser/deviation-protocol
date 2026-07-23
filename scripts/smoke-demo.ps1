#requires -Version 7.0

[CmdletBinding()]
param(
    [Parameter()]
    [ValidateRange(10, 300)]
    [int]$TimeoutSeconds = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom

Add-Type -TypeDefinition @'
using System;
using System.Diagnostics;
using System.Threading;

namespace DeviationProtocol
{
    public sealed class DemoProcessStreamDrain : IDisposable
    {
        public ManualResetEventSlim StdoutEof { get; } = new(false);
        public ManualResetEventSlim StderrEof { get; } = new(false);

        public void HandleStdout(object sender, DataReceivedEventArgs eventArgs)
        {
            if (eventArgs.Data == null)
            {
                StdoutEof.Set();
            }
            else
            {
                Console.Out.WriteLine(eventArgs.Data);
            }
        }

        public void HandleStderr(object sender, DataReceivedEventArgs eventArgs)
        {
            if (eventArgs.Data == null)
            {
                StderrEof.Set();
            }
            else
            {
                Console.Error.WriteLine(eventArgs.Data);
            }
        }

        public void Dispose()
        {
            StdoutEof.Dispose();
            StderrEof.Dispose();
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

function Assert-SafeResolvedPath {
    param(
        [Parameter(Mandatory)]
        [string]$Path,
        [Parameter(Mandatory)]
        [string]$Description
    )

    foreach ($character in $Path.ToCharArray()) {
        if ([char]::IsControl($character)) {
            throw "$Description contains unsafe characters."
        }
    }
    if ($Path.IndexOfAny([char[]]'"%!^&|<>()') -ge 0) {
        throw "$Description contains unsafe characters."
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
    Assert-SafeResolvedPath -Path $item.FullName -Description "The resolved npm.cmd path"
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

function New-DemoPresentationProcessStartInfo {
    param(
        [Parameter(Mandatory)]
        [string]$CmdPath,
        [Parameter(Mandatory)]
        [string]$NpmCmdPath,
        [Parameter(Mandatory)]
        [IO.DirectoryInfo]$WebDirectory,
        [Parameter(Mandatory)]
        [Diagnostics.ProcessStartInfo]$WebStartInfo
    )

    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $CmdPath
    $startInfo.UseShellExecute = $false
    $startInfo.WorkingDirectory = $WebDirectory.FullName
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.Arguments =
        '/d /s /c ""' +
        $NpmCmdPath +
        '" run test:run -- App.action-loop.test.tsx -t "' +
        'renders the exact deterministic Demo warning from the effective Vite mode""'
    Remove-SensitiveChildEnvironment -StartInfo $startInfo
    $startInfo.Environment["VITE_DEVIATION_DEMO_PRESENTATION_PROBE"] = "1"
    [void]$startInfo.Environment.Remove("VITE_APP_MODE")
    if ($WebStartInfo.Environment.ContainsKey("VITE_APP_MODE")) {
        $startInfo.Environment["VITE_APP_MODE"] =
            $WebStartInfo.Environment["VITE_APP_MODE"]
    }
    if ($startInfo.ArgumentList.Count -ne 0) {
        throw "The Demo-presentation probe ArgumentList must remain empty."
    }
    return $startInfo
}

function New-ValidatorProcessStartInfo {
    param(
        [Parameter(Mandatory)]
        [string]$CmdPath,
        [Parameter(Mandatory)]
        [string]$NpmCmdPath,
        [Parameter(Mandatory)]
        [IO.DirectoryInfo]$WebDirectory,
        [Parameter(Mandatory)]
        [string]$ResponsePath
    )

    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $CmdPath
    $startInfo.UseShellExecute = $false
    $startInfo.WorkingDirectory = $WebDirectory.FullName
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.Arguments =
        '/d /s /c ""' +
        $NpmCmdPath +
        '" run validate:scenario-catalog"'
    Remove-SensitiveChildEnvironment -StartInfo $startInfo
    $startInfo.Environment[
        "DEVIATION_DEMO_SCENARIO_RESPONSE_FILE"
    ] = $ResponsePath
    if ($startInfo.ArgumentList.Count -ne 0) {
        throw "The validator ArgumentList must remain empty."
    }
    return $startInfo
}

function Assert-SuccessfulProcessExitCode {
    param(
        [Parameter(Mandatory)]
        [int]$ExitCode,
        [Parameter(Mandatory)]
        [string]$Description
    )

    if ($ExitCode -ne 0) {
        throw "$Description failed with exit code $ExitCode."
    }
}

function Get-RemainingMilliseconds {
    param(
        [Parameter(Mandatory)]
        [Diagnostics.Stopwatch]$Stopwatch,
        [Parameter(Mandatory)]
        [int]$TotalSeconds
    )

    $remaining = ($TotalSeconds * 1000L) - $Stopwatch.ElapsedMilliseconds
    if ($remaining -le 0) {
        throw "The deterministic Demo smoke timed out."
    }
    return [int][Math]::Min($remaining, [int]::MaxValue)
}

function Assert-LongRunningChildrenAlive {
    param(
        [Parameter(Mandatory)]
        [Diagnostics.Process[]]$Processes
    )

    foreach ($process in $Processes) {
        if ($process.HasExited) {
            throw "A smoke-owned backend or Web child exited early with code $($process.ExitCode)."
        }
    }
}

function Start-OwnedProcess {
    param(
        [Parameter(Mandatory)]
        [Diagnostics.ProcessStartInfo]$StartInfo,
        [Parameter(Mandatory)]
        [AllowEmptyCollection()]
        [Collections.Generic.List[Diagnostics.Process]]$OwnedProcesses,
        [Parameter(Mandatory)]
        [string]$Description
    )

    $process = [Diagnostics.Process]::Start($StartInfo)
    if ($null -eq $process) {
        throw "Failed to start $Description."
    }
    $OwnedProcesses.Add($process)
    return $process
}

function Invoke-DrainedOwnedProcess {
    param(
        [Parameter(Mandatory)]
        [Diagnostics.ProcessStartInfo]$StartInfo,
        [Parameter(Mandatory)]
        [AllowEmptyCollection()]
        [Collections.Generic.List[Diagnostics.Process]]$OwnedProcesses,
        [Parameter(Mandatory)]
        [AllowEmptyCollection()]
        [Diagnostics.Process[]]$LongRunningProcesses,
        [Parameter(Mandatory)]
        [Diagnostics.Stopwatch]$Stopwatch,
        [Parameter(Mandatory)]
        [int]$TotalSeconds,
        [Parameter(Mandatory)]
        [string]$Description
    )

    $drain = [DeviationProtocol.DemoProcessStreamDrain]::new()

    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $StartInfo
    $process.add_OutputDataReceived($drain.HandleStdout)
    $process.add_ErrorDataReceived($drain.HandleStderr)
    $started = $false
    try {
        $started = $process.Start()
        if (-not $started) {
            throw "Failed to start $Description."
        }
        $OwnedProcesses.Add($process)
        $process.BeginOutputReadLine()
        $process.BeginErrorReadLine()

        while (-not $process.WaitForExit(100)) {
            if ($LongRunningProcesses.Count -gt 0) {
                Assert-LongRunningChildrenAlive -Processes $LongRunningProcesses
            }
            [void](Get-RemainingMilliseconds `
                -Stopwatch $Stopwatch `
                -TotalSeconds $TotalSeconds)
        }

        $remaining = Get-RemainingMilliseconds `
            -Stopwatch $Stopwatch `
            -TotalSeconds $TotalSeconds
        if (-not $drain.StdoutEof.Wait($remaining)) {
            throw "$Description stdout did not reach EOF."
        }
        $remaining = Get-RemainingMilliseconds `
            -Stopwatch $Stopwatch `
            -TotalSeconds $TotalSeconds
        if (-not $drain.StderrEof.Wait($remaining)) {
            throw "$Description stderr did not reach EOF."
        }
        return [int]$process.ExitCode
    }
    catch {
        if ($started) {
            if (-not $process.HasExited) {
                $process.Kill($true)
                if (-not $process.WaitForExit(10000)) {
                    throw "$Description failed and its owned process tree did not terminate."
                }
            }
            if (-not $drain.StdoutEof.Wait(10000)) {
                throw "$Description failed and stdout did not reach EOF during cleanup."
            }
            if (-not $drain.StderrEof.Wait(10000)) {
                throw "$Description failed and stderr did not reach EOF during cleanup."
            }
        }
        throw
    }
    finally {
        if ($started) {
            $process.remove_OutputDataReceived($drain.HandleStdout)
            $process.remove_ErrorDataReceived($drain.HandleStderr)
        }
        else {
            $process.Dispose()
        }
        $drain.Dispose()
    }
}

function Test-BytesContainUtf8Text {
    param(
        [Parameter(Mandatory)]
        [byte[]]$Bytes,
        [Parameter(Mandatory)]
        [string]$Text
    )

    $needle = [Text.Encoding]::UTF8.GetBytes($Text)
    if ($needle.Length -eq 0 -or $Bytes.Length -lt $needle.Length) {
        return $false
    }
    for ($offset = 0; $offset -le $Bytes.Length - $needle.Length; $offset += 1) {
        $matches = $true
        for ($index = 0; $index -lt $needle.Length; $index += 1) {
            if ($Bytes[$offset + $index] -ne $needle[$index]) {
                $matches = $false
                break
            }
        }
        if ($matches) {
            return $true
        }
    }
    return $false
}

function Get-RequiredLoopbackBytes {
    param(
        [Parameter(Mandatory)]
        [Net.Http.HttpClient]$Client,
        [Parameter(Mandatory)]
        [string]$Url,
        [Parameter(Mandatory)]
        [Diagnostics.Process[]]$LongRunningProcesses,
        [Parameter(Mandatory)]
        [Diagnostics.Stopwatch]$Stopwatch,
        [Parameter(Mandatory)]
        [int]$TotalSeconds
    )

    Assert-LongRunningChildrenAlive -Processes $LongRunningProcesses
    $remaining = Get-RemainingMilliseconds `
        -Stopwatch $Stopwatch `
        -TotalSeconds $TotalSeconds
    $requestTimeout = [Math]::Min(2000, $remaining)
    $cancellation = [Threading.CancellationTokenSource]::new($requestTimeout)
    try {
        $response = $Client.GetAsync(
            $Url,
            $cancellation.Token
        ).GetAwaiter().GetResult()
        try {
            if ([int]$response.StatusCode -ne 200) {
                throw "Loopback request returned HTTP $([int]$response.StatusCode)."
            }
            return $response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
        }
        finally {
            $response.Dispose()
        }
    }
    finally {
        $cancellation.Dispose()
    }
}

function Wait-ForProxyCatalog {
    param(
        [Parameter(Mandatory)]
        [Net.Http.HttpClient]$Client,
        [Parameter(Mandatory)]
        [Diagnostics.Process[]]$LongRunningProcesses,
        [Parameter(Mandatory)]
        [Diagnostics.Stopwatch]$Stopwatch,
        [Parameter(Mandatory)]
        [int]$TotalSeconds
    )

    while ($true) {
        Assert-LongRunningChildrenAlive -Processes $LongRunningProcesses
        $remaining = Get-RemainingMilliseconds `
            -Stopwatch $Stopwatch `
            -TotalSeconds $TotalSeconds
        $requestTimeout = [Math]::Min(1000, $remaining)
        $cancellation = [Threading.CancellationTokenSource]::new($requestTimeout)
        try {
            $response = $Client.GetAsync(
                "http://127.0.0.1:5173/api/v1/scenarios",
                $cancellation.Token
            ).GetAwaiter().GetResult()
            try {
                if ([int]$response.StatusCode -eq 200) {
                    $mediaType = $response.Content.Headers.ContentType.MediaType
                    if (
                        $null -eq $mediaType -or
                        -not $mediaType.Equals(
                            "application/json",
                            [StringComparison]::OrdinalIgnoreCase
                        )
                    ) {
                        throw "The proxied scenario response is not JSON."
                    }
                    return $response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
                }
            }
            finally {
                $response.Dispose()
            }
        }
        catch [OperationCanceledException] {
        }
        catch [Net.Http.HttpRequestException] {
        }
        finally {
            $cancellation.Dispose()
        }

        Start-Sleep -Milliseconds 100
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
$webPathText = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\web"))
if (-not [IO.Path]::IsPathFullyQualified($webPathText)) {
    throw "The Web working directory must be absolute."
}
$webDirectory = [IO.DirectoryInfo]::new($webPathText)
$pythonPath = [IO.Path]::GetFullPath(
    (Join-Path $repositoryRoot ".venv\Scripts\python.exe")
)
$sentinelPath = Join-Path $webDirectory.FullName ".env.deterministic-demo.local"
$ownedProcesses = [Collections.Generic.List[Diagnostics.Process]]::new()
$stopwatch = [Diagnostics.Stopwatch]::StartNew()
$workspacePath = $null
$buildPath = $null
$responsePath = $null
$workspaceCreated = $false
$sentinelCreated = $false
$responseCreated = $false
$failure = $null
$httpClient = $null

try {
    if ($PSVersionTable.PSVersion.Major -lt 7) {
        throw "PowerShell 7 or later is required."
    }
    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        throw "The repository .venv Python executable is missing."
    }
    if (-not $webDirectory.Exists) {
        throw "The Web project directory is missing."
    }
    if (-not (Test-Path -LiteralPath (Join-Path $webDirectory.FullName "package.json") -PathType Leaf)) {
        throw "web/package.json is missing."
    }
    if (-not (Test-Path -LiteralPath (Join-Path $webDirectory.FullName "node_modules") -PathType Container)) {
        throw "web/node_modules is missing. Install dependencies separately before smoke."
    }

    $cmdPath = Get-ValidatedComSpec
    $npmCmdPath = Get-ValidatedNpmCmd
    Assert-AvailableLoopbackPort -Port 8000
    Assert-AvailableLoopbackPort -Port 5173

    $temporaryRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    $workspacePath = [IO.Path]::GetFullPath(
        (Join-Path $temporaryRoot "deviation-demo-smoke-$([Guid]::NewGuid().ToString('N'))")
    )
    $temporaryPrefix = $temporaryRoot.TrimEnd(
        [IO.Path]::DirectorySeparatorChar,
        [IO.Path]::AltDirectorySeparatorChar
    ) + [IO.Path]::DirectorySeparatorChar
    if (
        -not $workspacePath.StartsWith(
            $temporaryPrefix,
            [StringComparison]::OrdinalIgnoreCase
        ) -or
        (Test-Path -LiteralPath $workspacePath)
    ) {
        throw "Unable to allocate a safe owned temporary workspace."
    }
    [void][IO.Directory]::CreateDirectory($workspacePath)
    $workspaceCreated = $true
    $buildPath = [IO.Path]::GetFullPath((Join-Path $workspacePath "build"))
    $responsePath = [IO.Path]::GetFullPath(
        (Join-Path $workspacePath "public-scenarios-response.json")
    )
    Assert-SafeResolvedPath -Path $buildPath -Description "The temporary build path"

    $sentinelName = "VITE_DEVIATION_DEMO_SENTINEL"
    $sentinelValue = "deviation-demo-sentinel-$([Guid]::NewGuid().ToString('N'))"
    $sentinelStream = [IO.FileStream]::new(
        $sentinelPath,
        [IO.FileMode]::CreateNew,
        [IO.FileAccess]::Write,
        [IO.FileShare]::Read
    )
    try {
        $sentinelCreated = $true
        $sentinelWriter = [IO.StreamWriter]::new($sentinelStream, $utf8NoBom)
        try {
            $sentinelWriter.WriteLine("$sentinelName=$sentinelValue")
            $sentinelWriter.Flush()
        }
        finally {
            $sentinelWriter.Dispose()
        }
    }
    finally {
        $sentinelStream.Dispose()
    }

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
    $webStartInfo.WorkingDirectory = $webDirectory.FullName
    $webStartInfo.Arguments =
        '/d /s /c ""' +
        $npmCmdPath +
        '" run dev -- --host 127.0.0.1 --port 5173 --strictPort --mode deterministic-demo"'
    Remove-SensitiveChildEnvironment -StartInfo $webStartInfo
    $webStartInfo.Environment["VITE_APP_MODE"] = "deterministic-demo"

    $backendProcess = Start-OwnedProcess `
        -StartInfo $backendStartInfo `
        -OwnedProcesses $ownedProcesses `
        -Description "the Demo backend"
    $webProcess = Start-OwnedProcess `
        -StartInfo $webStartInfo `
        -OwnedProcesses $ownedProcesses `
        -Description "the Demo Web client"
    $longRunningProcesses = @($backendProcess, $webProcess)

    $httpClient = [Net.Http.HttpClient]::new()
    $httpClient.Timeout = [Threading.Timeout]::InfiniteTimeSpan
    $proxyBytes = Wait-ForProxyCatalog `
        -Client $httpClient `
        -LongRunningProcesses $longRunningProcesses `
        -Stopwatch $stopwatch `
        -TotalSeconds $TimeoutSeconds
    if (Test-BytesContainUtf8Text -Bytes $proxyBytes -Text $sentinelValue) {
        throw "The dotenv sentinel reached the proxied API response."
    }

    $pageBytes = Get-RequiredLoopbackBytes `
        -Client $httpClient `
        -Url "http://127.0.0.1:5173/" `
        -LongRunningProcesses $longRunningProcesses `
        -Stopwatch $stopwatch `
        -TotalSeconds $TimeoutSeconds
    $moduleBytes = Get-RequiredLoopbackBytes `
        -Client $httpClient `
        -Url "http://127.0.0.1:5173/src/App.tsx" `
        -LongRunningProcesses $longRunningProcesses `
        -Stopwatch $stopwatch `
        -TotalSeconds $TimeoutSeconds
    if (
        (Test-BytesContainUtf8Text -Bytes $pageBytes -Text $sentinelValue) -or
        (Test-BytesContainUtf8Text -Bytes $moduleBytes -Text $sentinelValue)
    ) {
        throw "The dotenv sentinel reached served Web content."
    }
    $presentationStartInfo = New-DemoPresentationProcessStartInfo `
        -CmdPath $cmdPath `
        -NpmCmdPath $npmCmdPath `
        -WebDirectory $webDirectory `
        -WebStartInfo $webStartInfo
    $presentationExitCode = Invoke-DrainedOwnedProcess `
        -StartInfo $presentationStartInfo `
        -OwnedProcesses $ownedProcesses `
        -LongRunningProcesses $longRunningProcesses `
        -Stopwatch $stopwatch `
        -TotalSeconds $TimeoutSeconds `
        -Description "the effective deterministic Demo presentation probe"
    Assert-SuccessfulProcessExitCode `
        -ExitCode $presentationExitCode `
        -Description "The effective deterministic Demo presentation probe"

    $buildStartInfo = [Diagnostics.ProcessStartInfo]::new()
    $buildStartInfo.FileName = $cmdPath
    $buildStartInfo.UseShellExecute = $false
    $buildStartInfo.WorkingDirectory = $webDirectory.FullName
    $buildStartInfo.RedirectStandardOutput = $true
    $buildStartInfo.RedirectStandardError = $true
    $buildStartInfo.Arguments =
        '/d /s /c ""' +
        $npmCmdPath +
        '" run build -- --mode deterministic-demo --outDir "' +
        $buildPath +
        '""'
    Remove-SensitiveChildEnvironment -StartInfo $buildStartInfo
    $buildStartInfo.Environment["VITE_APP_MODE"] = "deterministic-demo"
    if ($buildStartInfo.ArgumentList.Count -ne 0) {
        throw "The build ArgumentList must remain empty."
    }
    $buildExitCode = Invoke-DrainedOwnedProcess `
        -StartInfo $buildStartInfo `
        -OwnedProcesses $ownedProcesses `
        -LongRunningProcesses $longRunningProcesses `
        -Stopwatch $stopwatch `
        -TotalSeconds $TimeoutSeconds `
        -Description "the deterministic Demo Web build"
    Assert-SuccessfulProcessExitCode `
        -ExitCode $buildExitCode `
        -Description "The deterministic Demo Web build"
    if (-not (Test-Path -LiteralPath $buildPath -PathType Container)) {
        throw "The deterministic Demo Web build produced no owned output."
    }
    foreach ($file in Get-ChildItem -LiteralPath $buildPath -File -Recurse) {
        $buildBytes = [IO.File]::ReadAllBytes($file.FullName)
        if (Test-BytesContainUtf8Text -Bytes $buildBytes -Text $sentinelValue) {
            throw "The dotenv sentinel reached the deterministic Demo bundle."
        }
    }

    $responseStream = [IO.FileStream]::new(
        $responsePath,
        [IO.FileMode]::CreateNew,
        [IO.FileAccess]::Write,
        [IO.FileShare]::Read
    )
    try {
        $responseCreated = $true
        $responseStream.Write($proxyBytes, 0, $proxyBytes.Length)
        $responseStream.Flush($true)
    }
    finally {
        $responseStream.Dispose()
    }

    $validatorStartInfo = New-ValidatorProcessStartInfo `
        -CmdPath $cmdPath `
        -NpmCmdPath $npmCmdPath `
        -WebDirectory $webDirectory `
        -ResponsePath $responsePath

    $validatorExitCode = Invoke-DrainedOwnedProcess `
        -StartInfo $validatorStartInfo `
        -OwnedProcesses $ownedProcesses `
        -LongRunningProcesses $longRunningProcesses `
        -Stopwatch $stopwatch `
        -TotalSeconds $TimeoutSeconds `
        -Description "the public scenario-catalog validator"
    Assert-SuccessfulProcessExitCode `
        -ExitCode $validatorExitCode `
        -Description "The public scenario-catalog validator"
    Assert-LongRunningChildrenAlive -Processes $longRunningProcesses
    [void](Get-RemainingMilliseconds `
        -Stopwatch $stopwatch `
        -TotalSeconds $TimeoutSeconds)

    Write-Host "Deterministic Demo smoke passed: loopback startup, proxy, schema, rendered warning, dotenv isolation, and owned build."
}
catch {
    $failure = $_.Exception.Message
}
finally {
    if ($null -ne $httpClient) {
        $httpClient.Dispose()
    }

    for ($index = $ownedProcesses.Count - 1; $index -ge 0; $index -= 1) {
        try {
            Stop-OwnedProcessTree -Process $ownedProcesses[$index]
        }
        catch {
            if ($null -eq $failure) {
                $failure = "Smoke cleanup failed: $($_.Exception.Message)"
            }
            else {
                $failure += " Smoke cleanup also failed: $($_.Exception.Message)"
            }
        }
    }

    if ($responseCreated -and $null -ne $responsePath) {
        try {
            [IO.File]::Delete($responsePath)
        }
        catch {
            if ($null -eq $failure) {
                $failure = "Smoke response-file cleanup failed."
            }
            else {
                $failure += " Smoke response-file cleanup also failed."
            }
        }
    }
    if ($workspaceCreated -and $null -ne $workspacePath) {
        try {
            $temporaryRootForCleanup = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
            $temporaryPrefixForCleanup = $temporaryRootForCleanup.TrimEnd(
                [IO.Path]::DirectorySeparatorChar,
                [IO.Path]::AltDirectorySeparatorChar
            ) + [IO.Path]::DirectorySeparatorChar
            if (
                -not $workspacePath.StartsWith(
                    $temporaryPrefixForCleanup,
                    [StringComparison]::OrdinalIgnoreCase
                )
            ) {
                throw "Owned workspace path escaped the temporary root."
            }
            if ([IO.Directory]::Exists($workspacePath)) {
                [IO.Directory]::Delete($workspacePath, $true)
            }
        }
        catch {
            if ($null -eq $failure) {
                $failure = "Smoke workspace cleanup failed."
            }
            else {
                $failure += " Smoke workspace cleanup also failed."
            }
        }
    }
    if ($sentinelCreated) {
        try {
            [IO.File]::Delete($sentinelPath)
        }
        catch {
            if ($null -eq $failure) {
                $failure = "Smoke sentinel cleanup failed."
            }
            else {
                $failure += " Smoke sentinel cleanup also failed."
            }
        }
    }
}

if ($null -ne $failure) {
    [Console]::Error.WriteLine("Deterministic Demo smoke failed: $failure")
    exit 1
}
exit 0
