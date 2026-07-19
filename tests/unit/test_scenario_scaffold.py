from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

from deviation_protocol.application.scenario_analysis import (
    DiagnosticSeverity,
    ScenarioAnalyzer,
    build_initial_preview,
)
from deviation_protocol.application.scenario_scaffold import (
    MAX_SCAFFOLD_PREMISE_CHARACTERS,
    MAX_SCAFFOLD_TITLE_CHARACTERS,
    SCENARIO_SCAFFOLD_TEMPLATE_VERSION,
    ScaffoldFile,
    ScenarioScaffoldInputError,
    build_scenario_scaffold,
    combined_scaffold_digest,
)
from deviation_protocol.infrastructure.content_loader import JsonContentCatalogLoader
from deviation_protocol.infrastructure.scenario_loader import JsonScenarioCatalogLoader
from deviation_protocol.tools import scenario as scenario_tool


ROOT = Path(__file__).parents[2]
DEMO_CONTENT = ROOT / "config" / "demo_content_pack.json"
FORMAL_SCENARIO_DIRECTORY = ROOT / "config" / "scenarios"
SCENARIO_ID = "abandoned_station_v1"
TITLE = "废弃车站"
PREMISE = "玩家在封闭车站中寻找离开的条件"


def demo_content_version() -> str:
    return JsonContentCatalogLoader(DEMO_CONTENT).load().content_version


def new_arguments(output_directory: Path, *extra: str) -> list[str]:
    return [
        "new",
        "--scenario-id",
        SCENARIO_ID,
        "--title",
        TITLE,
        "--premise",
        PREMISE,
        "--output-dir",
        str(output_directory),
        *extra,
    ]


def invoke_json(
    capsys: pytest.CaptureFixture[str], arguments: list[str]
) -> tuple[int, dict[str, object], str]:
    code = scenario_tool.main([*arguments, "--json"])
    captured = capsys.readouterr()
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err
    return code, json.loads(captured.out), captured.err


def tree_digest(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in directory.rglob("*") if item.is_file()):
        digest.update(path.relative_to(directory).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_new_publishes_minimal_draft_through_authoritative_loader_and_analyzer(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "草案 输出"
    code, payload, error = invoke_json(capsys, new_arguments(output))
    assert code == 0
    assert error == ""
    result = payload["result"]
    assert result["published"] is True
    assert result["template_version"] == SCENARIO_SCAFFOLD_TEMPLATE_VERSION
    final = output / SCENARIO_ID
    assert sorted(path.name for path in final.iterdir()) == ["design.md", "scenario.json"]
    staged_files = tuple(
        scenario_tool._scaffold_file_from_bytes(
            item["path"],
            (output / item["path"]).read_bytes(),
        )
        for item in result["files"]
    )
    assert [item.sha256 for item in staged_files] == [
        item["sha256"] for item in result["files"]
    ]
    assert combined_scaffold_digest(staged_files) == result["content_digest"]

    catalog = JsonScenarioCatalogLoader(final / "scenario.json").load()
    definition = catalog.scenarios[0]
    report = ScenarioAnalyzer().analyze(definition)
    assert definition.scenario_id == SCENARIO_ID
    assert report.diagnostic_counts.error == 0
    assert not any(
        item.severity is DiagnosticSeverity.ERROR for item in report.diagnostics
    )
    assert len(definition.phases) == 4
    assert len(definition.facts) == 1
    assert definition.narrative_outcome_rules == ()
    assert all(fact.value != PREMISE for fact in definition.facts)
    assert catalog.content_catalog.npcs == ()
    assert catalog.content_catalog.items == ()
    assert catalog.content_catalog.equipment == ()
    assert catalog.content_catalog.skills == ()
    design = (final / "design.md").read_text(encoding="utf-8")
    for checklist_item in (
        "核心冲突",
        "开局特色",
        "固定/隐藏/延迟事实",
        "NPC 知识边界",
        "线索与 N/M 组",
        "威胁时钟",
        "低频与 rapid 决策节奏",
        "outcome rules",
        "结局",
        "隐藏信息审查",
    ):
        assert checklist_item in design


def test_generated_pack_previews_with_demo_content_and_real_character(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "drafts"
    assert scenario_tool.main(new_arguments(output)) == 0
    capsys.readouterr()
    catalog = JsonScenarioCatalogLoader(output / SCENARIO_ID / "scenario.json").load()
    demo = JsonContentCatalogLoader(
        DEMO_CONTENT,
        expected_content_version=catalog.content_version,
    ).load()
    replaced = catalog.model_dump(mode="json")
    replaced["content_catalog"] = demo.model_dump(mode="json")
    compatible = type(catalog).model_validate(replaced)
    preview = build_initial_preview(
        compatible.content_catalog,
        compatible.scenarios[0],
        character_definition_id="character.player.default",
    )
    assert preview.report.phase_id == compatible.scenarios[0].initial_phase_id
    assert preview.report.character_definition_id == "character.player.default"
    assert preview.report.active_decision is None
    scenario_path = output / SCENARIO_ID / "scenario.json"
    validate_code, _, _ = invoke_json(capsys, ["validate", str(scenario_path)])
    analyze_code, analysis, _ = invoke_json(capsys, ["analyze", str(scenario_path)])
    preview_code, preview_payload, _ = invoke_json(
        capsys,
        [
            "preview",
            str(scenario_path),
            "--content-pack",
            str(DEMO_CONTENT),
            "--character-id",
            "character.player.default",
        ],
    )
    assert validate_code == analyze_code == preview_code == 0
    assert analysis["result"]["diagnostic_counts"]["error"] == 0
    assert preview_payload["result"]["character_definition_id"] == "character.player.default"


def test_default_content_version_tracks_demo_catalog() -> None:
    scaffold = scenario_tool._build_requested_scaffold(
        scenario_tool.build_parser().parse_args(new_arguments(Path("drafts")))
    )
    assert scaffold.catalog.content_version == demo_content_version()


def test_pure_render_and_dry_run_json_are_byte_stable_and_dry_run_writes_nothing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first = build_scenario_scaffold(
        scenario_id=SCENARIO_ID,
        title=TITLE,
        premise=PREMISE,
        content_version=demo_content_version(),
    )
    second = build_scenario_scaffold(
        scenario_id=SCENARIO_ID,
        title=TITLE,
        premise=PREMISE,
        content_version=demo_content_version(),
    )
    assert first.files == second.files
    assert first.content_digest == second.content_digest

    output = tmp_path / "never-created" / "nested"
    arguments = new_arguments(output, "--dry-run")
    assert scenario_tool.main([*arguments, "--json"]) == 0
    first_output = capsys.readouterr().out.encode("utf-8")
    assert scenario_tool.main([*arguments, "--json"]) == 0
    second_output = capsys.readouterr().out.encode("utf-8")
    assert first_output == second_output
    assert not output.exists()


@pytest.mark.parametrize("existing_name", [None, "scenario.json", "design.md"])
def test_existing_target_directory_or_file_is_rejected_without_changes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    existing_name: str | None,
) -> None:
    output = tmp_path / "drafts"
    target = output / SCENARIO_ID
    target.mkdir(parents=True)
    if existing_name is not None:
        (target / existing_name).write_text("USER CONTENT\n", encoding="utf-8")
    before = tree_digest(output)
    code, payload, error = invoke_json(capsys, new_arguments(output))
    assert code == 1
    assert error == ""
    assert payload["error"]["code"] == "SCAFFOLD_EXISTS"
    assert tree_digest(output) == before
    assert target.is_dir()
    if existing_name is None:
        assert list(target.iterdir()) == []


def test_second_file_write_failure_leaves_no_partial_final_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "drafts"
    output.mkdir()
    unrelated = output / "keep.txt"
    unrelated.write_text("keep\n", encoding="utf-8")
    real_write = scenario_tool._write_utf8_lf_file
    calls = 0

    def fail_second(path: Path, content: str) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated second write failure")
        real_write(path, content)

    monkeypatch.setattr(scenario_tool, "_write_utf8_lf_file", fail_second)
    code, payload, _ = invoke_json(capsys, new_arguments(output))
    assert code == 1
    assert payload["error"]["code"] == "SCAFFOLD_PUBLISH_FAILED"
    assert not (output / SCENARIO_ID).exists()
    assert unrelated.read_text(encoding="utf-8") == "keep\n"
    assert sorted(path.name for path in output.iterdir()) == ["keep.txt"]


@pytest.mark.parametrize(
    "unsafe_id",
    [
        "../escape",
        "part..escape",
        "C:\\absolute",
        "\\\\server\\share",
        "/absolute",
        "CON",
        "con.txt",
        "NUL.json",
        "COM1",
        "LPT9.txt",
        "bad/name",
        "bad\\name",
        "bad:name",
        "bad\u0001name",
    ],
)
def test_unsafe_scenario_ids_are_rejected(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    unsafe_id: str,
) -> None:
    arguments = new_arguments(tmp_path / "drafts")
    arguments[arguments.index(SCENARIO_ID)] = unsafe_id
    code, payload, _ = invoke_json(capsys, arguments)
    assert code == 1
    assert payload["error"]["code"] == "SCENARIO_ID_INVALID"
    assert not (tmp_path / "drafts").exists()


def test_output_directory_symlink_is_rejected_without_touching_target(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = tmp_path / "outside"
    target.mkdir()
    link = tmp_path / "linked-output"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink is not available: {exc}")
    code, payload, _ = invoke_json(capsys, new_arguments(link))
    assert code == 1
    assert payload["error"]["code"] == "OUTPUT_PATH_INVALID"
    assert list(target.iterdir()) == []


def test_output_path_file_or_control_character_is_rejected(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_file = tmp_path / "not-a-directory"
    output_file.write_text("USER CONTENT\n", encoding="utf-8")
    code, payload, _ = invoke_json(capsys, new_arguments(output_file))
    assert code == 1
    assert payload["error"]["code"] == "OUTPUT_PATH_INVALID"
    assert output_file.read_text(encoding="utf-8") == "USER CONTENT\n"

    arguments = new_arguments(tmp_path / "bad\noutput")
    code, payload, _ = invoke_json(capsys, arguments)
    assert code == 1
    assert payload["error"]["code"] == "OUTPUT_PATH_INVALID"


@pytest.mark.parametrize(
    ("flag", "value"),
    [
        ("--title", "x" * (MAX_SCAFFOLD_TITLE_CHARACTERS + 1)),
        ("--premise", "x" * (MAX_SCAFFOLD_PREMISE_CHARACTERS + 1)),
        ("--title", "bad\ntext"),
        ("--premise", "bad\u200btext"),
    ],
)
def test_bounded_text_rejects_excessive_or_control_input(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    flag: str,
    value: str,
) -> None:
    arguments = new_arguments(tmp_path / "drafts")
    arguments[arguments.index(flag) + 1] = value
    code, payload, _ = invoke_json(capsys, arguments)
    assert code == 1
    assert payload["error"]["code"] == "SCAFFOLD_INPUT_INVALID"
    assert not (tmp_path / "drafts").exists()


def test_generated_files_are_utf8_lf_with_final_newline_and_no_bom(
    tmp_path: Path,
) -> None:
    output = tmp_path / "目录 含 空格"
    assert scenario_tool.main(new_arguments(output)) == 0
    for path in (
        output / SCENARIO_ID / "scenario.json",
        output / SCENARIO_ID / "design.md",
    ):
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf")
        assert b"\r" not in data
        assert data.endswith(b"\n")
        data.decode("utf-8")


def test_cli_new_runs_outside_repository_with_stable_json(tmp_path: Path) -> None:
    working = tmp_path / "outside cwd"
    working.mkdir()
    output = working / "输出 草案"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "deviation_protocol.tools.scenario",
            *new_arguments(output),
            "--json",
        ],
        cwd=working,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0
    assert completed.stderr == ""
    assert "Traceback" not in completed.stdout
    assert str(ROOT) not in completed.stdout
    assert json.loads(completed.stdout)["result"]["published"] is True


def test_json_error_is_stable_path_free_and_has_no_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "private path" / "drafts"
    arguments = new_arguments(output)
    arguments[arguments.index(SCENARIO_ID)] = "CON"
    assert scenario_tool.main([*arguments, "--json"]) == 1
    first = capsys.readouterr()
    assert scenario_tool.main([*arguments, "--json"]) == 1
    second = capsys.readouterr()
    assert first.out.encode("utf-8") == second.out.encode("utf-8")
    assert first.err == second.err == ""
    assert str(tmp_path) not in first.out
    assert "Traceback" not in first.out


def test_outputs_have_no_machine_metadata_secret_url_time_or_uuid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "not-for-scaffold-output")
    output = tmp_path / "drafts"
    assert scenario_tool.main(new_arguments(output)) == 0
    rendered = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            output / SCENARIO_ID / "scenario.json",
            output / SCENARIO_ID / "design.md",
        )
    )
    assert str(tmp_path.resolve()) not in rendered
    assert "not-for-scaffold-output" not in rendered
    assert "http://" not in rendered and "https://" not in rendered
    assert re.search(r"\b\d{4}-\d{2}-\d{2}[T ]", rendered) is None
    assert re.search(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
        r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b",
        rendered,
    ) is None


def test_generic_scaffold_modules_have_no_formal_scenario_markers_or_forbidden_layers() -> None:
    paths = (
        ROOT / "src" / "deviation_protocol" / "application" / "scenario_scaffold.py",
        ROOT / "src" / "deviation_protocol" / "tools" / "scenario.py",
    )
    forbidden_markers = (
        "death_certificate",
        "hospital",
        "body_bag",
        "nurse",
        "死亡证明",
        "医院",
        "尸袋",
        "护士",
    )
    for path in paths:
        source = path.read_text(encoding="utf-8").lower()
        assert all(marker not in source for marker in forbidden_markers)
    application_source = paths[0].read_text(encoding="utf-8")
    for forbidden_layer in (
        "deviation_protocol.infrastructure",
        "deviation_protocol.tools",
        "NarrativeProvider",
        "Repository",
        "UnitOfWork",
        "sqlalchemy",
        "httpx",
    ):
        assert forbidden_layer not in application_source


def test_generation_does_not_modify_formal_scenarios_docs_or_demo_content(
    tmp_path: Path,
) -> None:
    tracked_inputs = (
        DEMO_CONTENT,
        ROOT / "README.md",
        ROOT / "docs" / "scenario_workbench.md",
        *sorted(FORMAL_SCENARIO_DIRECTORY.glob("*.json")),
    )
    before = {path: hashlib.sha256(path.read_bytes()).digest() for path in tracked_inputs}
    assert scenario_tool.main(new_arguments(tmp_path / "drafts")) == 0
    after = {path: hashlib.sha256(path.read_bytes()).digest() for path in tracked_inputs}
    assert after == before


def test_repeated_execution_never_overwrites_first_generation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "drafts"
    assert scenario_tool.main(new_arguments(output)) == 0
    capsys.readouterr()
    before = tree_digest(output)
    code, payload, _ = invoke_json(capsys, new_arguments(output))
    assert code == 1
    assert payload["error"]["code"] == "SCAFFOLD_EXISTS"
    assert tree_digest(output) == before


def test_cli_does_not_offer_force_or_overwrite() -> None:
    parser_help = scenario_tool.build_parser().format_help()
    new_parser = next(
        action.choices["new"]
        for action in scenario_tool.build_parser()._actions
        if getattr(action, "choices", None) and "new" in action.choices
    )
    new_help = new_parser.format_help()
    assert "--force" not in parser_help + new_help
    assert "--overwrite" not in parser_help + new_help


def test_unknown_schema_version_returns_stable_usage_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, payload, _ = invoke_json(
        capsys,
        new_arguments(tmp_path / "drafts", "--schema-version", "2"),
    )
    assert code == 1
    assert payload["error"]["code"] == "CLI_USAGE_ERROR"
    assert not (tmp_path / "drafts").exists()


def test_two_concurrent_processes_publish_at_most_one_complete_draft(
    tmp_path: Path,
) -> None:
    output = tmp_path / "concurrent drafts"
    output.mkdir()
    command = [
        sys.executable,
        "-m",
        "deviation_protocol.tools.scenario",
        *new_arguments(output),
        "--json",
    ]
    processes = [
        subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        for _ in range(2)
    ]
    completed = [process.communicate(timeout=20) for process in processes]
    assert sorted(process.returncode for process in processes) == [0, 1]
    assert all(error == "" for _, error in completed)
    payloads = [json.loads(output_text) for output_text, _ in completed]
    loser = next(payload for payload in payloads if "error" in payload)
    assert loser["error"]["code"] in {
        "SCAFFOLD_BUSY",
        "SCAFFOLD_EXISTS",
        "SCAFFOLD_PUBLISH_FAILED",
    }
    final = output / SCENARIO_ID
    assert sorted(path.name for path in final.iterdir()) == ["design.md", "scenario.json"]
    JsonScenarioCatalogLoader(final / "scenario.json").load()


def test_publish_race_preserves_concurrently_created_final_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    if not scenario_tool._DIRECTORY_RENAME_NO_REPLACE_SUPPORTED:
        pytest.skip("Windows no-replace directory rename behavior is platform-specific")
    output = tmp_path / "drafts"
    output.mkdir()
    real_rename = scenario_tool.os.rename

    def create_target_then_rename(source: Path, target: Path) -> None:
        target.mkdir()
        (target / "user.txt").write_text("USER CONTENT\n", encoding="utf-8")
        real_rename(source, target)

    monkeypatch.setattr(scenario_tool.os, "rename", create_target_then_rename)
    code, payload, _ = invoke_json(capsys, new_arguments(output))
    assert code == 1
    assert payload["error"]["code"] == "SCAFFOLD_PUBLISH_FAILED"
    assert (output / SCENARIO_ID / "user.txt").read_text(encoding="utf-8") == "USER CONTENT\n"
    assert sorted(path.name for path in output.iterdir()) == [SCENARIO_ID]


def test_posix_publish_seam_refuses_empty_existing_target_without_rename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "staging"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    (source / "scenario.json").write_text("staged\n", encoding="utf-8")
    staging = scenario_tool._capture_owned_directory(source)
    rename_called = False

    def forbidden_rename(source_path: Path, target_path: Path) -> None:
        nonlocal rename_called
        rename_called = True

    monkeypatch.setattr(
        scenario_tool,
        "_DIRECTORY_RENAME_NO_REPLACE_SUPPORTED",
        False,
    )
    monkeypatch.setattr(scenario_tool.os, "rename", forbidden_rename)
    with pytest.raises(scenario_tool.WorkbenchCliError) as error:
        scenario_tool._publish_staging_directory(source, target, staging=staging)
    assert error.value.code == "SCAFFOLD_PLATFORM_UNSUPPORTED"
    assert rename_called is False
    assert (source / "scenario.json").read_text(encoding="utf-8") == "staged\n"
    assert list(target.iterdir()) == []


def test_staging_identity_change_and_reparse_seam_prevent_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    staging_path = tmp_path / "staging"
    staging_path.mkdir()
    owned = scenario_tool._capture_owned_directory(staging_path)
    moved = tmp_path / "original"
    staging_path.rename(moved)
    staging_path.mkdir()
    replacement = staging_path / "scenario.json"
    replacement.write_text("USER CONTENT\n", encoding="utf-8")
    scenario_tool._cleanup_owned_staging(owned)
    assert replacement.read_text(encoding="utf-8") == "USER CONTENT\n"

    replacement_owned = scenario_tool._capture_owned_directory(staging_path)
    real_check = scenario_tool._is_link_or_junction
    monkeypatch.setattr(
        scenario_tool,
        "_is_link_or_junction",
        lambda path: path == staging_path or real_check(path),
    )
    scenario_tool._cleanup_owned_staging(replacement_owned)
    assert replacement.read_text(encoding="utf-8") == "USER CONTENT\n"


def test_preexisting_staging_directory_is_preserved(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "drafts"
    plan = scenario_tool._resolve_output_plan(str(output), SCENARIO_ID)
    output.mkdir()
    plan.temporary_directory.mkdir()
    sentinel = plan.temporary_directory / "user.txt"
    sentinel.write_text("USER CONTENT\n", encoding="utf-8")
    code, payload, _ = invoke_json(capsys, new_arguments(output))
    assert code == 1
    assert payload["error"]["code"] == "SCAFFOLD_BUSY"
    assert sentinel.read_text(encoding="utf-8") == "USER CONTENT\n"


@pytest.mark.parametrize(
    "formal_output",
    [FORMAL_SCENARIO_DIRECTORY, FORMAL_SCENARIO_DIRECTORY / "nested drafts"],
)
def test_formal_scenario_directory_and_descendants_are_forbidden(
    formal_output: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, payload, _ = invoke_json(
        capsys,
        new_arguments(formal_output, "--dry-run"),
    )
    assert code == 1
    assert payload["error"]["code"] == "FORMAL_SCENARIO_OUTPUT_FORBIDDEN"


@pytest.mark.parametrize(
    "unsafe_id",
    [
        *(name for stem in ("CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$") for name in (stem, f"{stem}.txt")),
        *(name for prefix in ("COM", "LPT") for index in range(1, 10) for name in (f"{prefix}{index}", f"{prefix}{index}.json")),
        "trailing.",
        "trailing ",
        "C:drive-relative",
        "C:\\rooted",
        "\\rooted",
        "\\\\server\\share",
        "name:stream",
        ".",
        "..",
        "x" * (scenario_tool.MAX_SCENARIO_ID_CHARACTERS + 1),
    ],
)
def test_complete_windows_path_boundary_ids_are_rejected(
    unsafe_id: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    arguments = new_arguments(tmp_path / "drafts")
    arguments[arguments.index(SCENARIO_ID)] = unsafe_id
    code, payload, _ = invoke_json(capsys, arguments)
    assert code == 1
    assert payload["error"]["code"] == "SCENARIO_ID_INVALID"
    assert not (tmp_path / "drafts").exists()


def test_unicode_nfc_equivalent_scenario_ids_are_both_rejected(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    for unsafe_id in ("é", "e\u0301"):
        arguments = new_arguments(tmp_path / "drafts")
        arguments[arguments.index(SCENARIO_ID)] = unsafe_id
        code, payload, _ = invoke_json(capsys, arguments)
        assert code == 1
        assert payload["error"]["code"] == "SCENARIO_ID_INVALID"
    assert not (tmp_path / "drafts").exists()


def test_markdown_metacharacters_remain_indented_draft_data(
    tmp_path: Path,
) -> None:
    title = "# injected heading <!-- comment -->"
    premise = "```powershell Remove-Item important ```"
    arguments = new_arguments(tmp_path / "drafts")
    arguments[arguments.index("--title") + 1] = title
    arguments[arguments.index("--premise") + 1] = premise
    assert scenario_tool.main(arguments) == 0
    design = (tmp_path / "drafts" / SCENARIO_ID / "design.md").read_text(
        encoding="utf-8"
    )
    title_line = next(line for line in design.splitlines() if title in line)
    premise_line = next(line for line in design.splitlines() if premise in line)
    assert title_line == f"    {title}"
    assert premise_line == f"    {premise}"
    assert not any(line == title or line == premise for line in design.splitlines())


def test_unknown_content_version_is_rejected_before_writes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "drafts"
    code, payload, _ = invoke_json(
        capsys,
        new_arguments(output, "--content-version", "unknown-version"),
    )
    assert code == 1
    assert payload["error"]["code"] == "CONTENT_VERSION_UNSUPPORTED"
    assert not output.exists()
    sources = (
        ROOT / "src" / "deviation_protocol" / "application" / "scenario_scaffold.py",
        ROOT / "src" / "deviation_protocol" / "tools" / "scenario.py",
    )
    assert all('"demo-1"' not in path.read_text(encoding="utf-8") for path in sources)


@pytest.mark.parametrize("schema_version", [True, 1.0, "1"])
def test_pure_scaffold_requires_strict_integer_schema_version(
    schema_version: object,
) -> None:
    with pytest.raises(ScenarioScaffoldInputError):
        build_scenario_scaffold(
            scenario_id=SCENARIO_ID,
            title=TITLE,
            premise=PREMISE,
            content_version=demo_content_version(),
            schema_version=schema_version,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("schema_version", ["true", "1.0", '"1"'])
def test_cli_rejects_non_integer_schema_version_forms(
    schema_version: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, payload, _ = invoke_json(
        capsys,
        new_arguments(tmp_path / "drafts", "--schema-version", schema_version),
    )
    assert code == 1
    assert payload["error"]["code"] == "CLI_USAGE_ERROR"


def test_combined_digest_has_unambiguous_file_boundaries() -> None:
    def file(path: str, content: str) -> ScaffoldFile:
        encoded = content.encode("utf-8")
        return ScaffoldFile(
            relative_path=path,
            content=content,
            sha256=hashlib.sha256(encoded).hexdigest(),
            utf8_bytes=len(encoded),
        )

    first = (file("a", "bc"), file("d", "e"))
    boundary_variant = (file("ab", "c"), file("d", "e"))
    reordered = tuple(reversed(first))
    assert combined_scaffold_digest(first) != combined_scaffold_digest(boundary_variant)
    assert combined_scaffold_digest(first) != combined_scaffold_digest(reordered)


def test_dry_run_and_published_files_have_identical_digests(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dry_output = tmp_path / "dry"
    code, dry_payload, _ = invoke_json(
        capsys,
        new_arguments(dry_output, "--dry-run"),
    )
    assert code == 0
    assert not dry_output.exists()
    real_output = tmp_path / "real"
    code, real_payload, _ = invoke_json(capsys, new_arguments(real_output))
    assert code == 0
    assert dry_payload["result"]["content_digest"] == real_payload["result"]["content_digest"]
    assert dry_payload["result"]["files"] == real_payload["result"]["files"]


def test_publish_failure_removes_only_owned_staging_and_leaves_no_final(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "drafts"
    output.mkdir()
    unrelated = output / "keep.txt"
    unrelated.write_text("keep\n", encoding="utf-8")

    def fail_publish(*args: object, **kwargs: object) -> None:
        raise OSError("simulated publish failure")

    monkeypatch.setattr(scenario_tool, "_publish_staging_directory", fail_publish)
    code, payload, _ = invoke_json(capsys, new_arguments(output))
    assert code == 1
    assert payload["error"]["code"] == "SCAFFOLD_PUBLISH_FAILED"
    assert sorted(path.name for path in output.iterdir()) == ["keep.txt"]
    assert unrelated.read_text(encoding="utf-8") == "keep\n"


def test_staged_validation_failure_leaves_no_final_or_staging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "drafts"
    output.mkdir()

    def fail_validation(*args: object, **kwargs: object) -> None:
        raise ValueError("simulated validation failure")

    monkeypatch.setattr(scenario_tool, "_validate_staged_scaffold", fail_validation)
    code, payload, _ = invoke_json(capsys, new_arguments(output))
    assert code == 1
    assert payload["error"]["code"] == "SCAFFOLD_PUBLISH_FAILED"
    assert list(output.iterdir()) == []


def test_reparse_parent_logic_is_covered_without_symlink_privilege(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "simulated-junction"
    parent.mkdir()
    output = parent / "drafts"
    real_check = scenario_tool._is_link_or_junction
    monkeypatch.setattr(
        scenario_tool,
        "_is_link_or_junction",
        lambda path: path == parent or real_check(path),
    )
    with pytest.raises(scenario_tool.WorkbenchCliError) as error:
        scenario_tool._resolve_output_plan(str(output), SCENARIO_ID)
    assert error.value.code == "OUTPUT_PATH_INVALID"
    assert list(parent.iterdir()) == []


def test_json_success_does_not_echo_output_path_or_user_path_like_text(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    private_text = str(tmp_path / "private absolute note")
    arguments = new_arguments(tmp_path / "drafts", "--dry-run")
    arguments[arguments.index("--premise") + 1] = private_text
    code, payload, _ = invoke_json(capsys, arguments)
    assert code == 0
    encoded = json.dumps(payload, ensure_ascii=False)
    assert str(tmp_path) not in encoded
    assert private_text not in encoded


def test_template_structure_does_not_branch_on_title_or_premise() -> None:
    first = build_scenario_scaffold(
        scenario_id=SCENARIO_ID,
        title="First title",
        premise="First premise",
        content_version=demo_content_version(),
    )
    second = build_scenario_scaffold(
        scenario_id=SCENARIO_ID,
        title="Second title",
        premise="Second premise",
        content_version=demo_content_version(),
    )
    first_definition = first.catalog.scenarios[0].model_dump(mode="json")
    second_definition = second.catalog.scenarios[0].model_dump(mode="json")
    for payload in (first_definition, second_definition):
        payload.pop("title")
        payload.pop("summary")
    assert first_definition == second_definition


def test_publish_implementation_never_uses_replacing_path_apis() -> None:
    source = (ROOT / "src" / "deviation_protocol" / "tools" / "scenario.py").read_text(
        encoding="utf-8"
    )
    assert "os.replace" not in source
    assert ".replace(" not in source


def test_new_modules_have_no_database_provider_environment_or_git_operations() -> None:
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            ROOT / "src" / "deviation_protocol" / "application" / "scenario_scaffold.py",
            ROOT / "src" / "deviation_protocol" / "tools" / "scenario.py",
        )
    )
    for forbidden in (
        "DeepSeek",
        "NarrativeProvider",
        "AsyncSession",
        "create_engine",
        "DATABASE_URL",
        "TEST_DATABASE_URL",
        "Repository",
        "UnitOfWork",
        "subprocess",
        "git add",
        "git commit",
        "git push",
    ):
        assert forbidden not in sources
