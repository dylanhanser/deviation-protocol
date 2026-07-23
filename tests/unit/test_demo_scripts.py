from __future__ import annotations

import os
from pathlib import Path
import shutil
import socket
import subprocess
import textwrap

import pytest


ROOT = Path(__file__).parents[2]
START_SCRIPT = ROOT / "scripts" / "start-demo.ps1"
SMOKE_SCRIPT = ROOT / "scripts" / "smoke-demo.ps1"
SENSITIVE_VARIABLES = (
    "DATABASE_URL",
    "TEST_DATABASE_URL",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "DEEPSEEK_FUTURE_SETTING",
    "RUN_LIVE_DEEPSEEK_TEST",
    "DEVIATION_DEMO_SCENARIO_RESPONSE_FILE",
)


def pwsh_path() -> str:
    executable = shutil.which("pwsh")
    if executable is None:
        pytest.fail("PowerShell 7 is required by the repository toolchain")
    return executable


def sanitized_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in SENSITIVE_VARIABLES:
        environment.pop(name, None)
    return environment


def run_pwsh(
    arguments: list[str],
    *,
    environment: dict[str, str] | None = None,
    timeout: int = 15,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [pwsh_path(), "-NoLogo", "-NoProfile", *arguments],
        cwd=ROOT,
        env=environment or sanitized_environment(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
        check=False,
    )


def run_extracted_functions(
    function_names: tuple[str, ...],
    body: str,
    *,
    environment: dict[str, str] | None = None,
    script: Path = SMOKE_SCRIPT,
    timeout: int = 15,
) -> subprocess.CompletedProcess[str]:
    names = ",".join(f'"{name}"' for name in function_names)
    type_loader = ""
    if "Invoke-DrainedOwnedProcess" in function_names:
        type_loader = r"""
$addTypeAst = $ast.Find(
    {
        param($node)
        $node -is [Management.Automation.Language.CommandAst] -and
            $node.GetCommandName() -eq "Add-Type"
    },
    $true
)
if ($null -eq $addTypeAst) {
    exit 90
}
Invoke-Expression $addTypeAst.Extent.Text
"""
    probe = f"""
$ErrorActionPreference = "Stop"
$tokens = $null
$parseErrors = $null
$scriptPath = [Environment]::GetEnvironmentVariable(
    "DEMO_SCRIPT_UNDER_TEST",
    [EnvironmentVariableTarget]::Process
)
$ast = [Management.Automation.Language.Parser]::ParseFile(
    $scriptPath,
    [ref]$tokens,
    [ref]$parseErrors
)
if ($parseErrors.Count -ne 0) {{
    exit 91
}}
{type_loader}
foreach ($functionName in @({names})) {{
    $functionAst = $ast.Find(
        {{
            param($node)
            $node -is [Management.Automation.Language.FunctionDefinitionAst] -and
                $node.Name -eq $functionName
        }},
        $true
    )
    if ($null -eq $functionAst) {{
        exit 92
    }}
    Invoke-Expression $functionAst.Extent.Text
}}
{textwrap.dedent(body)}
"""
    child_environment = (environment or sanitized_environment()).copy()
    child_environment["DEMO_SCRIPT_UNDER_TEST"] = str(script)
    return run_pwsh(
        ["-Command", probe],
        environment=child_environment,
        timeout=timeout,
    )


def test_scripts_require_and_execute_under_powershell_7() -> None:
    for script in (START_SCRIPT, SMOKE_SCRIPT):
        assert script.read_text(encoding="utf-8").startswith(
            "#requires -Version 7.0\n"
        )

    completed = run_pwsh(
        ["-Command", "if ($PSVersionTable.PSVersion.Major -lt 7) { exit 1 }"]
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize("timeout_value", (9, 301))
def test_smoke_rejects_timeout_values_outside_the_inclusive_bounds(
    timeout_value: int,
) -> None:
    completed = run_pwsh(
        [
            "-File",
            str(SMOKE_SCRIPT),
            "-TimeoutSeconds",
            str(timeout_value),
        ]
    )
    assert completed.returncode != 0
    assert "allowed range" in completed.stderr


def test_smoke_timeout_default_and_bounds_are_frozen() -> None:
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")
    assert "[ValidateRange(10, 300)]" in script
    assert "[int]$TimeoutSeconds = 60" in script
    assert "Get-RemainingMilliseconds" in script
    assert "$TotalSeconds * 1000L" in script


def test_launcher_fails_before_launch_when_repository_prerequisites_are_missing(
    tmp_path: Path,
) -> None:
    temporary_scripts = tmp_path / "scripts"
    temporary_scripts.mkdir()
    copied_script = temporary_scripts / "start-demo.ps1"
    shutil.copyfile(START_SCRIPT, copied_script)

    completed = run_pwsh(["-File", str(copied_script)])

    assert completed.returncode != 0
    assert ".venv Python executable is missing" in completed.stderr


def test_occupied_loopback_port_is_rejected_by_the_executable_preflight() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        environment = sanitized_environment()
        environment["DEMO_OCCUPIED_PORT"] = str(port)
        completed = run_extracted_functions(
            ("Assert-AvailableLoopbackPort",),
            r"""
try {
    Assert-AvailableLoopbackPort -Port ([int]$env:DEMO_OCCUPIED_PORT)
}
catch {
    if ($_.Exception.Message -notmatch "occupied or unavailable") {
        exit 93
    }
    exit 0
}
exit 94
""",
            environment=environment,
        )

    assert completed.returncode == 0, completed.stderr


def test_sensitive_child_environment_is_removed_by_name_including_all_deepseek_prefixes() -> None:
    completed = run_extracted_functions(
        ("Remove-SensitiveChildEnvironment",),
        r"""
$startInfo = [Diagnostics.ProcessStartInfo]::new()
foreach ($name in @(
    "DATABASE_URL",
    "TEST_DATABASE_URL",
    "RUN_LIVE_DEEPSEEK_TEST",
    "DEVIATION_DEMO_SCENARIO_RESPONSE_FILE",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_FUTURE_SETTING"
)) {
    $startInfo.Environment[$name] = "harmless-test-value"
}
$startInfo.Environment["DEVIATION_UNRELATED"] = "keep"
Remove-SensitiveChildEnvironment -StartInfo $startInfo
foreach ($name in @(
    "DATABASE_URL",
    "TEST_DATABASE_URL",
    "RUN_LIVE_DEEPSEEK_TEST",
    "DEVIATION_DEMO_SCENARIO_RESPONSE_FILE",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_FUTURE_SETTING"
)) {
    if ($startInfo.Environment.ContainsKey($name)) {
        exit 93
    }
}
if ($startInfo.Environment["DEVIATION_UNRELATED"] -cne "keep") {
    exit 94
}
""",
    )
    assert completed.returncode == 0, completed.stderr


def _run_rendered_presentation_probe_case(
    web_child_mode: str | None,
) -> subprocess.CompletedProcess[str]:
    environment = sanitized_environment()
    environment["VITE_APP_MODE"] = "deterministic-demo"
    environment["DEMO_WEB_CHILD_MODE"] = (
        "__MISSING__" if web_child_mode is None else web_child_mode
    )
    return run_extracted_functions(
        (
            "Get-ValidatedComSpec",
            "Assert-SafeResolvedPath",
            "Get-ValidatedNpmCmd",
            "Remove-SensitiveChildEnvironment",
            "New-DemoPresentationProcessStartInfo",
            "Get-RemainingMilliseconds",
            "Assert-LongRunningChildrenAlive",
            "Invoke-DrainedOwnedProcess",
            "Stop-OwnedProcessTree",
        ),
        r"""
$webStartInfo = [Diagnostics.ProcessStartInfo]::new()
if ($env:DEMO_WEB_CHILD_MODE -eq "__MISSING__") {
    [void]$webStartInfo.Environment.Remove("VITE_APP_MODE")
}
else {
    $webStartInfo.Environment["VITE_APP_MODE"] = $env:DEMO_WEB_CHILD_MODE
}
$probeStartInfo = New-DemoPresentationProcessStartInfo `
    -CmdPath (Get-ValidatedComSpec) `
    -NpmCmdPath (Get-ValidatedNpmCmd) `
    -WebDirectory ([IO.DirectoryInfo]::new((Join-Path (Get-Location) "web"))) `
    -WebStartInfo $webStartInfo
if ($probeStartInfo -isnot [Diagnostics.ProcessStartInfo]) {
    exit 93
}
if ($env:DEMO_WEB_CHILD_MODE -eq "__MISSING__") {
    if ($probeStartInfo.Environment.ContainsKey("VITE_APP_MODE")) {
        exit 94
    }
}
elseif (
    -not $probeStartInfo.Environment.ContainsKey("VITE_APP_MODE") -or
    $probeStartInfo.Environment["VITE_APP_MODE"] -cne $env:DEMO_WEB_CHILD_MODE
) {
    exit 95
}

$owned = [Collections.Generic.List[Diagnostics.Process]]::new()
try {
    $exitCode = Invoke-DrainedOwnedProcess `
        -StartInfo $probeStartInfo `
        -OwnedProcesses $owned `
        -LongRunningProcesses @() `
        -Stopwatch ([Diagnostics.Stopwatch]::StartNew()) `
        -TotalSeconds 30 `
        -Description "the rendered Demo warning probe"
    if ($env:DEMO_WEB_CHILD_MODE -ceq "deterministic-demo") {
        if ($exitCode -ne 0) {
            exit 96
        }
    }
    elseif ($exitCode -eq 0) {
        exit 97
    }
}
finally {
    foreach ($process in $owned) {
        Stop-OwnedProcessTree -Process $process
    }
}
""",
        environment=environment,
        timeout=40,
    )


def test_presentation_probe_removes_ambient_expected_mode_when_web_child_key_is_missing() -> None:
    completed = _run_rendered_presentation_probe_case(None)

    assert completed.returncode == 0, completed.stderr


def test_presentation_probe_copies_wrong_web_child_mode_and_rendered_warning_fails() -> None:
    completed = _run_rendered_presentation_probe_case("ordinary-mode")

    assert completed.returncode == 0, completed.stderr


def test_presentation_probe_copies_exact_web_child_mode_and_rendered_warning_passes() -> None:
    completed = _run_rendered_presentation_probe_case("deterministic-demo")

    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize(
    "kind",
    ("missing", "empty", "relative", "invalid-absolute", "wrong-leaf"),
)
def test_comspec_validation_fails_closed(
    kind: str,
    tmp_path: Path,
) -> None:
    environment = sanitized_environment()
    if kind == "missing":
        environment.pop("ComSpec", None)
        environment["DEMO_REMOVE_COMSPEC"] = "1"
    elif kind == "empty":
        environment["ComSpec"] = " "
    elif kind == "relative":
        environment["ComSpec"] = r"relative\cmd.exe"
    elif kind == "invalid-absolute":
        environment["ComSpec"] = str(tmp_path / "missing" / "cmd.exe")
    else:
        wrong_leaf = tmp_path / "not-cmd.exe"
        wrong_leaf.write_bytes(b"")
        environment["ComSpec"] = str(wrong_leaf)

    completed = run_extracted_functions(
        ("Get-ValidatedComSpec",),
        r"""
if ($env:DEMO_REMOVE_COMSPEC -eq "1") {
    [Environment]::SetEnvironmentVariable(
        "ComSpec",
        $null,
        [EnvironmentVariableTarget]::Process
    )
}
try {
    [void](Get-ValidatedComSpec)
}
catch {
    exit 0
}
exit 93
""",
        environment=environment,
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize("kind", ("zero", "multiple", "unsafe"))
def test_npm_cmd_resolution_fails_for_zero_multiple_or_unsafe_results(
    kind: str,
    tmp_path: Path,
) -> None:
    environment = sanitized_environment()
    path_entries: list[str] = []
    if kind == "multiple":
        for index in (1, 2):
            directory = tmp_path / f"npm-{index}"
            directory.mkdir()
            (directory / "npm.cmd").write_text("@exit /b 0\n", encoding="utf-8")
            path_entries.append(str(directory))
    elif kind == "unsafe":
        directory = tmp_path / "unsafe&npm"
        directory.mkdir()
        (directory / "npm.cmd").write_text("@exit /b 0\n", encoding="utf-8")
        path_entries.append(str(directory))
    else:
        path_entries.append(str(tmp_path))
    environment["PATH"] = os.pathsep.join(path_entries)

    completed = run_extracted_functions(
        ("Assert-SafeResolvedPath", "Get-ValidatedNpmCmd"),
        r"""
try {
    [void](Get-ValidatedNpmCmd)
}
catch {
    exit 0
}
exit 93
""",
        environment=environment,
    )
    assert completed.returncode == 0, completed.stderr


def test_npm_cmd_resolution_accepts_one_safe_absolute_path_with_spaces(
    tmp_path: Path,
) -> None:
    npm_directory = tmp_path / "safe npm directory"
    npm_directory.mkdir()
    npm_cmd = npm_directory / "npm.cmd"
    npm_cmd.write_text("@exit /b 0\r\n", encoding="utf-8")
    environment = sanitized_environment()
    environment["PATH"] = str(npm_directory)
    environment["DEMO_EXPECTED_NPM"] = str(npm_cmd)

    completed = run_extracted_functions(
        ("Assert-SafeResolvedPath", "Get-ValidatedNpmCmd"),
        r"""
$resolved = Get-ValidatedNpmCmd
if (
    -not $resolved.Equals(
        $env:DEMO_EXPECTED_NPM,
        [StringComparison]::OrdinalIgnoreCase
    )
) {
    exit 93
}
""",
        environment=environment,
    )

    assert completed.returncode == 0, completed.stderr


def _write_fake_npm_cmd(path: Path) -> None:
    path.write_text(
        textwrap.dedent(
            r"""
            @echo off
            > "%DEMO_VALIDATOR_CAPTURE%" (
              echo ARG1=%~1
              echo ARG2=%~2
              echo RESPONSE=%DEVIATION_DEMO_SCENARIO_RESPONSE_FILE%
            )
            for /L %%i in (1,1,6000) do @echo validator-stdout-%%i
            for /L %%i in (1,1,6000) do @echo validator-stderr-%%i 1>&2
            exit /b %DEMO_VALIDATOR_EXIT%
            """
        ).lstrip(),
        encoding="utf-8",
    )


def _validator_harness_environment(
    tmp_path: Path, *, exit_code: int
) -> tuple[dict[str, str], Path, Path]:
    npm_directory = tmp_path / "validator npm with spaces"
    npm_directory.mkdir()
    npm_cmd = npm_directory / "npm.cmd"
    _write_fake_npm_cmd(npm_cmd)
    capture_path = tmp_path / "validator-capture.txt"
    response_path = tmp_path / "public scenarios.json"
    response_path.write_text("{}", encoding="utf-8")
    environment = sanitized_environment()
    environment["DEMO_TEST_NPM"] = str(npm_cmd)
    environment["DEMO_VALIDATOR_CAPTURE"] = str(capture_path)
    environment["DEMO_VALIDATOR_RESPONSE"] = str(response_path)
    environment["DEMO_VALIDATOR_EXIT"] = str(exit_code)
    return environment, capture_path, response_path


def test_validator_command_arguments_and_large_streams_execute_without_deadlock(
    tmp_path: Path,
) -> None:
    environment, capture_path, response_path = _validator_harness_environment(
        tmp_path, exit_code=0
    )
    completed = run_extracted_functions(
        (
            "Get-ValidatedComSpec",
            "Remove-SensitiveChildEnvironment",
            "New-ValidatorProcessStartInfo",
            "Assert-SuccessfulProcessExitCode",
            "Get-RemainingMilliseconds",
            "Assert-LongRunningChildrenAlive",
            "Invoke-DrainedOwnedProcess",
            "Stop-OwnedProcessTree",
        ),
        r"""
$owned = [Collections.Generic.List[Diagnostics.Process]]::new()
$stopwatch = [Diagnostics.Stopwatch]::StartNew()
$webDirectory = [IO.DirectoryInfo]::new((Get-Location).Path)
$startInfo = New-ValidatorProcessStartInfo `
    -CmdPath (Get-ValidatedComSpec) `
    -NpmCmdPath $env:DEMO_TEST_NPM `
    -WebDirectory $webDirectory `
    -ResponsePath $env:DEMO_VALIDATOR_RESPONSE
try {
    $exitCode = Invoke-DrainedOwnedProcess `
        -StartInfo $startInfo `
        -OwnedProcesses $owned `
        -LongRunningProcesses @() `
        -Stopwatch $stopwatch `
        -TotalSeconds 12 `
        -Description "the public scenario-catalog validator"
    Assert-SuccessfulProcessExitCode `
        -ExitCode $exitCode `
        -Description "The public scenario-catalog validator"
}
finally {
    foreach ($process in $owned) {
        Stop-OwnedProcessTree -Process $process
    }
}
""",
        environment=environment,
        timeout=20,
    )

    assert completed.returncode == 0, completed.stderr
    capture = capture_path.read_text(encoding="utf-8")
    assert "ARG1=run" in capture
    assert "ARG2=validate:scenario-catalog" in capture
    assert f"RESPONSE={response_path}" in capture
    assert "validator-stdout-6000" in completed.stdout
    assert "validator-stderr-6000" in completed.stderr


def test_nonzero_validator_exit_is_propagated_as_failure(tmp_path: Path) -> None:
    environment, _, _ = _validator_harness_environment(tmp_path, exit_code=23)
    completed = run_extracted_functions(
        (
            "Get-ValidatedComSpec",
            "Remove-SensitiveChildEnvironment",
            "New-ValidatorProcessStartInfo",
            "Assert-SuccessfulProcessExitCode",
            "Get-RemainingMilliseconds",
            "Assert-LongRunningChildrenAlive",
            "Invoke-DrainedOwnedProcess",
        ),
        r"""
$owned = [Collections.Generic.List[Diagnostics.Process]]::new()
$startInfo = New-ValidatorProcessStartInfo `
    -CmdPath (Get-ValidatedComSpec) `
    -NpmCmdPath $env:DEMO_TEST_NPM `
    -WebDirectory ([IO.DirectoryInfo]::new((Get-Location).Path)) `
    -ResponsePath $env:DEMO_VALIDATOR_RESPONSE
$exitCode = Invoke-DrainedOwnedProcess `
    -StartInfo $startInfo `
    -OwnedProcesses $owned `
    -LongRunningProcesses @() `
    -Stopwatch ([Diagnostics.Stopwatch]::StartNew()) `
    -TotalSeconds 12 `
    -Description "the public scenario-catalog validator"
Assert-SuccessfulProcessExitCode `
    -ExitCode $exitCode `
    -Description "The public scenario-catalog validator"
""",
        environment=environment,
        timeout=20,
    )

    assert completed.returncode != 0
    assert "failed with exit code 23" in completed.stderr


def test_unexpected_early_exit_of_owned_long_running_child_is_executable() -> None:
    environment = sanitized_environment()
    environment["DEMO_TEST_PWSH"] = pwsh_path()
    completed = run_extracted_functions(
        ("Assert-LongRunningChildrenAlive",),
        r"""
$startInfo = [Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = $env:DEMO_TEST_PWSH
$startInfo.UseShellExecute = $false
[void]$startInfo.ArgumentList.Add("-NoProfile")
[void]$startInfo.ArgumentList.Add("-Command")
[void]$startInfo.ArgumentList.Add("exit 7")
$process = [Diagnostics.Process]::Start($startInfo)
try {
    [void]$process.WaitForExit(5000)
    try {
        Assert-LongRunningChildrenAlive -Processes @($process)
    }
    catch {
        if ($_.Exception.Message -notmatch "exited early with code 7") {
            exit 93
        }
        exit 0
    }
    exit 94
}
finally {
    $process.Dispose()
}
""",
        environment=environment,
    )
    assert completed.returncode == 0, completed.stderr


def test_timeout_terminates_the_owned_process() -> None:
    environment = sanitized_environment()
    environment["DEMO_TEST_PWSH"] = pwsh_path()
    completed = run_extracted_functions(
        (
            "Get-RemainingMilliseconds",
            "Assert-LongRunningChildrenAlive",
            "Invoke-DrainedOwnedProcess",
            "Stop-OwnedProcessTree",
        ),
        r"""
$startInfo = [Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = $env:DEMO_TEST_PWSH
$startInfo.UseShellExecute = $false
$startInfo.RedirectStandardOutput = $true
$startInfo.RedirectStandardError = $true
[void]$startInfo.ArgumentList.Add("-NoProfile")
[void]$startInfo.ArgumentList.Add("-Command")
[void]$startInfo.ArgumentList.Add("Start-Sleep -Seconds 30")
$owned = [Collections.Generic.List[Diagnostics.Process]]::new()
try {
    [void](Invoke-DrainedOwnedProcess `
        -StartInfo $startInfo `
        -OwnedProcesses $owned `
        -LongRunningProcesses @() `
        -Stopwatch ([Diagnostics.Stopwatch]::StartNew()) `
        -TotalSeconds 1 `
        -Description "the bounded test child")
    exit 93
}
catch {
    if ($_.Exception.Message -notmatch "timed out") {
        exit 94
    }
    if ($owned.Count -ne 1 -or -not $owned[0].HasExited) {
        exit 95
    }
}
finally {
    foreach ($process in $owned) {
        Stop-OwnedProcessTree -Process $process
    }
}
""",
        environment=environment,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stderr


def test_owned_tree_cleanup_releases_port_and_preserves_unrelated_process(
    tmp_path: Path,
) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]

    child_script = tmp_path / "listener-child.ps1"
    child_script.write_text(
        textwrap.dedent(
            r"""
            param([int]$Port, [string]$ReadyPath)
            $listener = [Net.Sockets.TcpListener]::new(
                [Net.IPAddress]::Loopback,
                $Port
            )
            try {
                $listener.Start()
                [IO.File]::WriteAllText($ReadyPath, "ready")
                while ($true) { Start-Sleep -Milliseconds 100 }
            }
            finally {
                $listener.Stop()
            }
            """
        ).lstrip(),
        encoding="utf-8",
    )
    parent_script = tmp_path / "listener-parent.ps1"
    parent_script.write_text(
        textwrap.dedent(
            r"""
            param(
                [string]$PwshPath,
                [string]$ChildScript,
                [int]$Port,
                [string]$ReadyPath
            )
            $startInfo = [Diagnostics.ProcessStartInfo]::new()
            $startInfo.FileName = $PwshPath
            $startInfo.UseShellExecute = $false
            foreach ($argument in @(
                "-NoProfile", "-File", $ChildScript,
                "-Port", [string]$Port, "-ReadyPath", $ReadyPath
            )) {
                [void]$startInfo.ArgumentList.Add($argument)
            }
            $child = [Diagnostics.Process]::Start($startInfo)
            try {
                while ($true) { Start-Sleep -Milliseconds 100 }
            }
            finally {
                if (-not $child.HasExited) {
                    $child.Kill($true)
                    [void]$child.WaitForExit(5000)
                }
                $child.Dispose()
            }
            """
        ).lstrip(),
        encoding="utf-8",
    )
    ready_path = tmp_path / "listener.ready"
    environment = sanitized_environment()
    environment.update(
        {
            "DEMO_TEST_PWSH": pwsh_path(),
            "DEMO_TEST_PARENT": str(parent_script),
            "DEMO_TEST_CHILD": str(child_script),
            "DEMO_TEST_PORT": str(port),
            "DEMO_TEST_READY": str(ready_path),
        }
    )
    completed = run_extracted_functions(
        (
            "Assert-AvailableLoopbackPort",
            "Start-OwnedProcess",
            "Stop-OwnedProcessTree",
        ),
        r"""
$controlInfo = [Diagnostics.ProcessStartInfo]::new()
$controlInfo.FileName = $env:DEMO_TEST_PWSH
$controlInfo.UseShellExecute = $false
[void]$controlInfo.ArgumentList.Add("-NoProfile")
[void]$controlInfo.ArgumentList.Add("-Command")
[void]$controlInfo.ArgumentList.Add("Start-Sleep -Seconds 30")
$control = [Diagnostics.Process]::Start($controlInfo)
$owned = [Collections.Generic.List[Diagnostics.Process]]::new()
try {
    $parentInfo = [Diagnostics.ProcessStartInfo]::new()
    $parentInfo.FileName = $env:DEMO_TEST_PWSH
    $parentInfo.UseShellExecute = $false
    foreach ($argument in @(
        "-NoProfile", "-File", $env:DEMO_TEST_PARENT,
        "-PwshPath", $env:DEMO_TEST_PWSH,
        "-ChildScript", $env:DEMO_TEST_CHILD,
        "-Port", $env:DEMO_TEST_PORT,
        "-ReadyPath", $env:DEMO_TEST_READY
    )) {
        [void]$parentInfo.ArgumentList.Add($argument)
    }
    $parent = Start-OwnedProcess `
        -StartInfo $parentInfo `
        -OwnedProcesses $owned `
        -Description "the owned parent"
    $deadline = [DateTime]::UtcNow.AddSeconds(5)
    while (-not [IO.File]::Exists($env:DEMO_TEST_READY)) {
        if ([DateTime]::UtcNow -ge $deadline -or $parent.HasExited) {
            exit 93
        }
        Start-Sleep -Milliseconds 50
    }
    Stop-OwnedProcessTree -Process $parent
    if ($control.HasExited) {
        exit 94
    }
    Assert-AvailableLoopbackPort -Port ([int]$env:DEMO_TEST_PORT)
}
finally {
    if (-not $control.HasExited) {
        $control.Kill($true)
        [void]$control.WaitForExit(5000)
    }
    $control.Dispose()
}
""",
        environment=environment,
        timeout=15,
    )

    assert completed.returncode == 0, completed.stderr
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as released:
        released.bind(("127.0.0.1", port))


def test_cleanup_helper_failure_is_propagated() -> None:
    completed = run_extracted_functions(
        ("Stop-OwnedProcessTree",),
        r"""
$disposed = [Diagnostics.Process]::new()
$disposed.Dispose()
Stop-OwnedProcessTree -Process $disposed
""",
    )
    assert completed.returncode != 0
    assert "No process is associated with this object" in completed.stderr


def test_sentinel_and_response_files_use_create_new_and_collision_never_reads_or_overwrites() -> None:
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")
    assert script.count("[IO.FileMode]::CreateNew") == 2
    sentinel_block = script.split("$sentinelStream =", maxsplit=1)[1].split(
        "$backendStartInfo =", maxsplit=1
    )[0]
    assert "[IO.FileMode]::CreateNew" in sentinel_block
    assert "$sentinelCreated = $true" in sentinel_block
    assert "Get-Content" not in sentinel_block
    assert "ReadAll" not in sentinel_block
    assert "OpenOrCreate" not in sentinel_block
    assert "Create," not in sentinel_block


def test_smoke_uses_owned_temporary_build_and_never_targets_web_dist() -> None:
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")
    assert 'Join-Path $workspacePath "build"' in script
    assert "--outDir" in script
    assert "web/dist" not in script.replace("\\", "/").lower()
    assert "[IO.Directory]::Delete($workspacePath, $true)" in script
    assert "$workspacePath.StartsWith(" in script
    assert "$workspaceCreated" in script


def test_frozen_validator_process_start_info_and_arguments_are_exact() -> None:
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")
    validator = script.split(
        "function New-ValidatorProcessStartInfo {", maxsplit=1
    )[1].split("function Assert-SuccessfulProcessExitCode", maxsplit=1)[0]
    assert "$startInfo.FileName = $CmdPath" in validator
    assert "$startInfo.UseShellExecute = $false" in validator
    assert "$startInfo.WorkingDirectory = $WebDirectory.FullName" in validator
    assert "$startInfo.RedirectStandardOutput = $true" in validator
    assert "$startInfo.RedirectStandardError = $true" in validator
    assert (
        '$startInfo.Environment[\n'
        '        "DEVIATION_DEMO_SCENARIO_RESPONSE_FILE"\n'
        "    ] = $ResponsePath"
    ) in validator
    assert "'/d /s /c \"\"'" in validator
    assert '\'" run validate:scenario-catalog"\'' in validator
    assert "$startInfo.ArgumentList.Count -ne 0" in validator
    assert ".ArgumentList.Add" not in validator


def test_validator_streams_are_drained_asynchronously_before_exit_code_authority() -> None:
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")
    drained = script.split("function Invoke-DrainedOwnedProcess {", maxsplit=1)[
        1
    ].split("function Test-BytesContainUtf8Text", maxsplit=1)[0]
    assert drained.index("$process.add_OutputDataReceived") < drained.index(
        "$process.Start()"
    )
    assert drained.index("$process.add_ErrorDataReceived") < drained.index(
        "$process.Start()"
    )
    assert "$process.BeginOutputReadLine()" in drained
    assert "$process.BeginErrorReadLine()" in drained
    assert "$drain.StdoutEof.Wait($remaining)" in drained
    assert "$drain.StderrEof.Wait($remaining)" in drained
    assert "return [int]$process.ExitCode" in drained
    assert "ReadToEnd" not in drained
    assert "[DeviationProtocol.DemoProcessStreamDrain]::new()" in drained
    assert "[Diagnostics.DataReceivedEventHandler] {" not in drained

    success_authority = script.split(
        "function Assert-SuccessfulProcessExitCode {", maxsplit=1
    )[1].split("function Get-RemainingMilliseconds", maxsplit=1)[0]
    assert "if ($ExitCode -ne 0)" in success_authority
    assert "stdout" not in success_authority.lower()
    assert "stderr" not in success_authority.lower()


def test_timeout_early_exit_nonzero_and_cleanup_failures_propagate_nonzero() -> None:
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")
    assert 'throw "The deterministic Demo smoke timed out."' in script
    assert "exited early with code $($process.ExitCode)" in script
    assert "-ExitCode $buildExitCode" in script
    assert "-ExitCode $validatorExitCode" in script
    assert "Smoke cleanup failed:" in script
    assert "cleanup also failed" in script
    assert "if ($null -ne $failure)" in script
    assert "exit 1" in script
    assert script.rstrip().endswith("exit 0")


def test_timeout_cleanup_reaps_and_drains_the_owned_child_tree() -> None:
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")
    drained = script.split("function Invoke-DrainedOwnedProcess {", maxsplit=1)[
        1
    ].split("function Test-BytesContainUtf8Text", maxsplit=1)[0]
    catch_block = drained.split("catch {", maxsplit=1)[1].split(
        "finally {", maxsplit=1
    )[0]
    assert "$process.Kill($true)" in catch_block
    assert "$process.WaitForExit(10000)" in catch_block
    assert "$drain.StdoutEof.Wait(10000)" in catch_block
    assert "$drain.StderrEof.Wait(10000)" in catch_block


def test_only_script_owned_process_objects_are_terminated() -> None:
    for path in (START_SCRIPT, SMOKE_SCRIPT):
        script = path.read_text(encoding="utf-8")
        assert "$ownedProcesses.Add(" in script or "$OwnedProcesses.Add(" in script
        assert "$Process.Kill($true)" in script or "$process.Kill($true)" in script
        assert "Get-Process" not in script
        assert "Stop-Process" not in script
        assert "taskkill" not in script.lower()
        assert "Win32_Process" not in script


def test_launcher_ctrl_c_handler_is_runspace_independent() -> None:
    script = START_SCRIPT.read_text(encoding="utf-8")
    assert "public sealed class DemoCancelState" in script
    assert "public void HandleCancel(" in script
    assert "eventArgs.Cancel = true;" in script
    assert "StopRequested = true;" in script
    assert "$cancelHandler = $cancelState.HandleCancel" in script
    assert "while (-not $cancelState.StopRequested)" in script
    assert "[ConsoleCancelEventHandler] {" not in script


def test_smoke_process_helpers_accept_the_initial_empty_ownership_list() -> None:
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")
    assert script.count(
        "[AllowEmptyCollection()]\n"
        "        [Collections.Generic.List[Diagnostics.Process]]$OwnedProcesses"
    ) == 2


def test_smoke_uses_per_request_cancellation_under_one_total_deadline() -> None:
    script = SMOKE_SCRIPT.read_text(encoding="utf-8")
    assert "$httpClient.Timeout = [Threading.Timeout]::InfiniteTimeSpan" in script
    assert script.count("[Threading.CancellationTokenSource]::new(") == 2
    assert script.count("$cancellation.Token") == 2
    assert script.count("$cancellation.Dispose()") == 2


def test_launcher_and_smoke_freeze_loopback_single_worker_demo_composition() -> None:
    for path in (START_SCRIPT, SMOKE_SCRIPT):
        script = path.read_text(encoding="utf-8")
        assert '"deviation_protocol.api.demo:app"' in script
        assert '"--host"' in script
        assert '"127.0.0.1"' in script
        assert '"--workers"' in script
        assert '"1"' in script
        assert "--reload" not in script
        assert "--host 127.0.0.1 --port 5173 --strictPort --mode deterministic-demo" in script
        assert '$webStartInfo.Environment["VITE_APP_MODE"] = "deterministic-demo"' in script
        assert "npm install" not in script
        assert "npm ci" not in script
        assert "npx" not in script
        assert "Start-Process" not in script


def test_port_checks_precede_every_child_launch() -> None:
    for path in (START_SCRIPT, SMOKE_SCRIPT):
        script = path.read_text(encoding="utf-8")
        port_checks_end = script.index(
            "Assert-AvailableLoopbackPort -Port 5173",
            script.index("try {", script.index("$failure = $null")),
        )
        first_start = script.index("$backendProcess =", port_checks_end)
        assert script.index("Assert-AvailableLoopbackPort -Port 8000") < first_start
        assert script.index("Assert-AvailableLoopbackPort -Port 5173") < first_start
