from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).parents[2]
VERIFY_SCRIPT = ROOT / "scripts" / "verify.ps1"
DOCTOR_SCRIPT = ROOT / "scripts" / "doctor.ps1"
RESTRICTED_VARIABLES = (
    "TEST_DATABASE_URL",
    "DATABASE_URL",
    "DEEPSEEK_API_KEY",
    "RUN_LIVE_DEEPSEEK_TEST",
)


def pwsh_path() -> str:
    executable = shutil.which("pwsh")
    if executable is None:
        pytest.fail("PowerShell 7 is required by the repository toolchain")
    return executable


def offline_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for variable_name in RESTRICTED_VARIABLES:
        environment.pop(variable_name, None)
    return environment


def test_non_capture_native_command_streams_diagnostics_before_exit() -> None:
    probe = r'''
$tokens = $null
$parseErrors = $null
$scriptPath = [Environment]::GetEnvironmentVariable(
    "VERIFY_SCRIPT_UNDER_TEST",
    [EnvironmentVariableTarget]::Process
)
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $scriptPath,
    [ref]$tokens,
    [ref]$parseErrors
)
if ($parseErrors.Count -ne 0) {
    exit 91
}
$functionAst = $ast.Find(
    {
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $node.Name -eq "Invoke-NativeCommand"
    },
    $true
)
if ($null -eq $functionAst) {
    exit 92
}
Invoke-Expression $functionAst.Extent.Text
$childPath = Join-Path $PSHOME $(if ($IsWindows) { "pwsh.exe" } else { "pwsh" })
try {
    Invoke-NativeCommand `
        -Stage "streaming regression probe" `
        -FilePath $childPath `
        -Arguments @(
            "-NoLogo",
            "-NoProfile",
            "-Command",
            "Write-Output 'diagnostic-before-exit-中文'; Start-Sleep -Milliseconds 1200; exit 23"
        )
}
catch {
    Write-Output "expected-command-failure"
    exit 0
}
exit 93
'''
    environment = offline_environment()
    environment["VERIFY_SCRIPT_UNDER_TEST"] = str(VERIFY_SCRIPT)
    process = subprocess.Popen(
        [pwsh_path(), "-NoLogo", "-NoProfile", "-Command", probe],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )
    try:
        assert process.stdout is not None
        assert process.stdout.readline().strip() == "==> streaming regression probe"
        assert process.stdout.readline().strip() == "diagnostic-before-exit-中文"
        assert process.poll() is None
        remaining_output, _ = process.communicate(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)

    assert process.returncode == 0
    assert "expected-command-failure" in remaining_output


def test_capture_native_command_returns_only_captured_output() -> None:
    probe = r'''
$tokens = $null
$parseErrors = $null
$scriptPath = [Environment]::GetEnvironmentVariable(
    "VERIFY_SCRIPT_UNDER_TEST",
    [EnvironmentVariableTarget]::Process
)
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $scriptPath,
    [ref]$tokens,
    [ref]$parseErrors
)
if ($parseErrors.Count -ne 0) {
    exit 91
}
$functionAst = $ast.Find(
    {
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $node.Name -eq "Invoke-NativeCommand"
    },
    $true
)
Invoke-Expression $functionAst.Extent.Text
$childPath = Join-Path $PSHOME $(if ($IsWindows) { "pwsh.exe" } else { "pwsh" })
$captured = @(Invoke-NativeCommand `
    -Stage "capture regression probe" `
    -FilePath $childPath `
    -Arguments @("-NoLogo", "-NoProfile", "-Command", "Write-Output 'captured-中文'") `
    -CaptureOutput)
if ($captured.Count -ne 1 -or $captured[0].ToString() -cne "captured-中文") {
    exit 92
}
Write-Output "capture-returned-only-captured-content"
'''
    environment = offline_environment()
    environment["VERIFY_SCRIPT_UNDER_TEST"] = str(VERIFY_SCRIPT)

    completed = subprocess.run(
        [pwsh_path(), "-NoLogo", "-NoProfile", "-Command", probe],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        "==> capture regression probe",
        "capture-returned-only-captured-content",
    ]


def test_mysql_mode_routes_integration_tests_through_streaming_native_path() -> None:
    script = VERIFY_SCRIPT.read_text(encoding="utf-8")

    assert 'Invoke-NativeCommand -Stage "MySQL integration tests"' in script
    native_function = script.split("function Invoke-NativeCommand {", maxsplit=1)[1].split(
        "function Test-LiveDeepSeekEnabled", maxsplit=1
    )[0]
    assert "& $FilePath @Arguments 2>&1 | ForEach-Object { Write-Host $_ }" in native_function
    assert "[System.Diagnostics.ProcessStartInfo]" not in native_function


def test_offline_doctor_treats_empty_variable_as_present() -> None:
    environment = offline_environment()
    environment["DATABASE_URL"] = ""

    completed = subprocess.run(
        [
            pwsh_path(),
            "-NoLogo",
            "-NoProfile",
            "-File",
            str(DOCTOR_SCRIPT),
            "-Strict",
            "-RequireOffline",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
        check=False,
    )

    output = completed.stdout + completed.stderr
    assert completed.returncode != 0
    assert "DATABASE_URL: present" in output
    assert "offline requirement: failed" in output
