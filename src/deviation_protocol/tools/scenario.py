from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from typing import Any, NoReturn
import unicodedata

from pydantic import BaseModel

from deviation_protocol.application.scenario_analysis import (
    DiagnosticSeverity,
    ScenarioAnalyzer,
    build_initial_preview,
    validation_summary,
)
from deviation_protocol.application.scenario_scaffold import (
    SCENARIO_SCAFFOLD_TEMPLATE_VERSION,
    SUPPORTED_SCENARIO_SCHEMA_VERSION,
    ScaffoldFile,
    ScenarioScaffold,
    ScenarioScaffoldInputError,
    build_scenario_scaffold,
    combined_scaffold_digest,
)
from deviation_protocol.domain.content import ContentCatalog
from deviation_protocol.domain.scenario import ScenarioCatalog, ScenarioDefinition
from deviation_protocol.infrastructure.content_loader import (
    ContentPackLoadError,
    JsonContentCatalogLoader,
)
from deviation_protocol.infrastructure.scenario_loader import (
    JsonScenarioCatalogLoader,
    ScenarioPackLoadError,
)

MAX_INPUT_PATH_CHARACTERS = 1_024
MAX_CHARACTER_ID_CHARACTERS = 128
MAX_SCENARIO_ID_CHARACTERS = 128
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEMO_CONTENT_PACK = REPOSITORY_ROOT / "config" / "demo_content_pack.json"
FORMAL_SCENARIO_DIRECTORY = REPOSITORY_ROOT / "config" / "scenarios"
_DIRECTORY_RENAME_NO_REPLACE_SUPPORTED = os.name == "nt"
_WINDOWS_RESERVED_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "CONIN$",
        "CONOUT$",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }
)


class WorkbenchCliError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class WorkbenchArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        raise WorkbenchCliError(
            "CLI_USAGE_ERROR",
            "Command-line arguments are invalid.",
        )


def build_parser() -> argparse.ArgumentParser:
    parser = WorkbenchArgumentParser(
        prog="python -m deviation_protocol.tools.scenario",
        description="Validate, analyze, preview, or scaffold a local scenario pack.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "analyze", "preview"):
        subparser = subparsers.add_parser(
            command,
            help=f"{command.capitalize()} one strictly versioned scenario pack.",
        )
        subparser.add_argument("scenario_pack", help="Path to the scenario JSON pack.")
        subparser.add_argument(
            "--content-pack",
            help="Optional external content pack; it must match the scenario version and references.",
        )
        subparser.add_argument(
            "--character-id",
            help="Playable ContentCatalog character used for Frame construction.",
        )
        subparser.add_argument(
            "--json",
            action="store_true",
            help="Emit stable machine-readable JSON.",
        )
    new_parser = subparsers.add_parser(
        "new",
        help="Create a deterministic draft in a new scenario-specific directory.",
    )
    new_parser.add_argument("--scenario-id", required=True)
    new_parser.add_argument("--title", required=True)
    new_parser.add_argument("--premise", required=True)
    new_parser.add_argument("--output-dir", required=True)
    new_parser.add_argument(
        "--content-version",
        default=None,
    )
    new_parser.add_argument(
        "--schema-version",
        type=int,
        choices=(SUPPORTED_SCENARIO_SCHEMA_VERSION,),
        default=SUPPORTED_SCENARIO_SCHEMA_VERSION,
    )
    new_parser.add_argument("--dry-run", action="store_true")
    new_parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_windows_utf8_streams()
    json_requested = argv is not None and "--json" in argv
    if argv is None:
        json_requested = "--json" in sys.argv[1:]
    try:
        arguments = build_parser().parse_args(argv)
        json_requested = bool(arguments.json)
        if arguments.command == "new":
            scaffold = _build_requested_scaffold(arguments)
            plan = _resolve_output_plan(arguments.output_dir, scaffold.scenario_id)
            if not arguments.dry_run:
                _publish_scaffold(plan, scaffold)
            _write_new_result(scaffold, dry_run=arguments.dry_run, as_json=arguments.json)
            return 0

        catalog, definition = _load_definition(
            arguments.scenario_pack,
            content_pack=arguments.content_pack,
        )
        if arguments.character_id is not None:
            _require_playable_character(catalog.content_catalog, arguments.character_id)

        if arguments.command == "validate":
            analysis = ScenarioAnalyzer().analyze(definition)
            result: BaseModel = validation_summary(
                definition,
                blocking_diagnostics=analysis.diagnostics,
            )
            exit_code = (
                2
                if any(
                    item.severity is DiagnosticSeverity.ERROR
                    for item in result.diagnostics
                )
                else 0
            )
        elif arguments.command == "analyze":
            preview = (
                build_initial_preview(
                    catalog.content_catalog,
                    definition,
                    character_definition_id=arguments.character_id,
                )
                if arguments.character_id is not None
                else None
            )
            result = ScenarioAnalyzer().analyze(
                definition,
                initial_public_frame=(preview.frame if preview is not None else None),
            )
            exit_code = (
                2
                if any(
                    item.severity is DiagnosticSeverity.ERROR
                    for item in result.diagnostics
                )
                else 0
            )
        else:
            if arguments.character_id is None:
                raise WorkbenchCliError(
                    "CHARACTER_REQUIRED",
                    "preview requires --character-id with a playable catalog character.",
                )
            result = build_initial_preview(
                catalog.content_catalog,
                definition,
                character_definition_id=arguments.character_id,
            ).report
            exit_code = 0

        _write_result(arguments.command, result, as_json=arguments.json)
        return exit_code
    except WorkbenchCliError as exc:
        _write_error(exc.code, exc.message, as_json=json_requested)
        return 1
    except ScenarioPackLoadError:
        _write_error(
            "SCENARIO_PACK_INVALID",
            "The scenario pack could not be decoded or validated.",
            as_json=json_requested,
        )
        return 1
    except ScenarioScaffoldInputError:
        _write_error(
            "SCAFFOLD_INPUT_INVALID",
            "A scaffold input is invalid or exceeds its configured boundary.",
            as_json=json_requested,
        )
        return 1
    except ContentPackLoadError:
        _write_error(
            "CONTENT_PACK_INVALID",
            "The content pack could not be decoded or validated.",
            as_json=json_requested,
        )
        return 1
    except (OSError, UnicodeError):
        _write_error(
            "WORKBENCH_FILE_ERROR",
            "A requested local input file could not be read.",
            as_json=json_requested,
        )
        return 1
    except (TypeError, ValueError):
        _write_error(
            "WORKBENCH_INPUT_INVALID",
            "The requested operation could not be completed with the supplied catalog inputs.",
            as_json=json_requested,
        )
        return 1
    except Exception:
        _write_error(
            "WORKBENCH_INTERNAL_ERROR",
            "The local workbench could not complete the command.",
            as_json=json_requested,
        )
        return 1


def _load_definition(
    scenario_pack: str,
    *,
    content_pack: str | None,
) -> tuple[ScenarioCatalog, ScenarioDefinition]:
    scenario_path = _require_input_file(scenario_pack, kind="scenario pack")
    catalog = JsonScenarioCatalogLoader(scenario_path).load()
    if content_pack is not None:
        content_path = _require_input_file(content_pack, kind="content pack")
        external = JsonContentCatalogLoader(
            content_path,
            expected_content_version=catalog.content_version,
        ).load()
        payload = catalog.model_dump(mode="json")
        payload["content_catalog"] = external.model_dump(mode="json")
        try:
            catalog = ScenarioCatalog.model_validate(payload)
        except ValueError as exc:
            raise ContentPackLoadError("external content catalog is incompatible") from exc
    if len(catalog.scenarios) != 1:
        raise WorkbenchCliError(
            "SCENARIO_SELECTION_REQUIRED",
            "The scenario pack must contain exactly one scenario for this command.",
        )
    return catalog, catalog.scenarios[0]


@dataclass(frozen=True, slots=True)
class _OutputPlan:
    output_root: Path
    final_directory: Path
    temporary_directory: Path


@dataclass(frozen=True, slots=True)
class _DirectoryIdentity:
    device: int
    inode: int
    created_ns: int


@dataclass(frozen=True, slots=True)
class _OwnedDirectory:
    path: Path
    identity: _DirectoryIdentity


def _build_requested_scaffold(arguments: argparse.Namespace) -> ScenarioScaffold:
    scenario_id = _require_safe_scenario_id(arguments.scenario_id)
    supported_content_version = _load_supported_scaffold_content_version()
    content_version = (
        supported_content_version
        if arguments.content_version is None
        else arguments.content_version
    )
    if content_version != supported_content_version:
        raise WorkbenchCliError(
            "CONTENT_VERSION_UNSUPPORTED",
            "The requested scaffold content version is not in the current catalog.",
        )
    return build_scenario_scaffold(
        scenario_id=scenario_id,
        title=arguments.title,
        premise=arguments.premise,
        content_version=content_version,
        schema_version=arguments.schema_version,
    )


def _load_supported_scaffold_content_version() -> str:
    return JsonContentCatalogLoader(DEMO_CONTENT_PACK).load().content_version


def _require_safe_scenario_id(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    if (
        not normalized
        or len(normalized) > MAX_SCENARIO_ID_CHARACTERS
        or not normalized[0].isalnum()
        or not normalized.isascii()
        or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-" for character in normalized)
        or ".." in normalized
        or normalized.endswith(".")
    ):
        raise WorkbenchCliError(
            "SCENARIO_ID_INVALID",
            "The scenario identifier is not a safe draft directory name.",
        )
    if Path(normalized).is_absolute() or Path(normalized).anchor:
        raise WorkbenchCliError(
            "SCENARIO_ID_INVALID",
            "The scenario identifier is not a safe draft directory name.",
        )
    device_stem = normalized.split(".", 1)[0].upper()
    if device_stem in _WINDOWS_RESERVED_NAMES:
        raise WorkbenchCliError(
            "SCENARIO_ID_INVALID",
            "The scenario identifier is not a safe draft directory name.",
        )
    return normalized


def _resolve_output_plan(raw_output_directory: str, scenario_id: str) -> _OutputPlan:
    if (
        not raw_output_directory
        or len(raw_output_directory) > MAX_INPUT_PATH_CHARACTERS
        or any(
            unicodedata.category(character) in {"Cc", "Cf", "Cs"}
            for character in raw_output_directory
        )
    ):
        raise WorkbenchCliError(
            "OUTPUT_PATH_INVALID",
            "The output directory is invalid or exceeds its configured length limit.",
        )
    try:
        requested = Path(raw_output_directory)
        _reject_existing_reparse_components(Path(os.path.abspath(requested)))
        if _path_lexists(requested):
            if not requested.is_dir() or _is_link_or_junction(requested):
                raise WorkbenchCliError(
                    "OUTPUT_PATH_INVALID",
                    "The output path must be a real directory, not a file or link.",
                )
        output_root = requested.resolve(strict=False)
        formal_directory = FORMAL_SCENARIO_DIRECTORY.resolve(strict=True)
        if output_root == formal_directory or output_root.is_relative_to(
            formal_directory
        ):
            raise WorkbenchCliError(
                "FORMAL_SCENARIO_OUTPUT_FORBIDDEN",
                "Draft scaffolds cannot be written into the formal scenario directory.",
            )
        final_directory = output_root / scenario_id
        temporary_directory = output_root / (
            ".scenario-new-"
            + sha256(scenario_id.encode("utf-8")).hexdigest()[:20]
            + ".tmp"
        )
        if final_directory.resolve(strict=False).parent != output_root:
            raise WorkbenchCliError(
                "OUTPUT_PATH_INVALID",
                "The resolved scaffold target is outside the output directory.",
            )
        if _path_lexists(final_directory):
            raise WorkbenchCliError(
                "SCAFFOLD_EXISTS",
                "The scenario draft target already exists; existing content is never overwritten.",
            )
        if _path_lexists(temporary_directory):
            raise WorkbenchCliError(
                "SCAFFOLD_BUSY",
                "A staging directory for this scenario already exists.",
            )
        return _OutputPlan(output_root, final_directory, temporary_directory)
    except WorkbenchCliError:
        raise
    except (OSError, ValueError):
        raise WorkbenchCliError(
            "OUTPUT_PATH_INVALID",
            "The output directory could not be resolved safely.",
        ) from None


def _reject_existing_reparse_components(path: Path) -> None:
    cursor = path
    while True:
        if _path_lexists(cursor) and _is_link_or_junction(cursor):
            raise WorkbenchCliError(
                "OUTPUT_PATH_INVALID",
                "The output path cannot traverse a link or reparse-point directory.",
            )
        if cursor.parent == cursor:
            return
        cursor = cursor.parent


def _publish_scaffold(plan: _OutputPlan, scaffold: ScenarioScaffold) -> None:
    created_directories: list[_OwnedDirectory] = []
    staging: _OwnedDirectory | None = None
    try:
        created_directories = _create_directory_chain(plan.output_root)
        if _is_link_or_junction(plan.output_root):
            raise WorkbenchCliError(
                "OUTPUT_PATH_INVALID",
                "The output path must be a real directory, not a file or link.",
            )
        if _path_lexists(plan.final_directory):
            raise WorkbenchCliError(
                "SCAFFOLD_EXISTS",
                "The scenario draft target already exists; existing content is never overwritten.",
            )
        plan.temporary_directory.mkdir(exist_ok=False)
        staging = _capture_owned_directory(plan.temporary_directory)
        scenario_path = plan.temporary_directory / "scenario.json"
        design_path = plan.temporary_directory / "design.md"
        _require_owned_directory(staging)
        _write_utf8_lf_file(scenario_path, scaffold.files[0].content)
        _require_owned_directory(staging)
        _write_utf8_lf_file(design_path, scaffold.files[1].content)
        _require_owned_directory(staging)
        _validate_staged_scaffold(
            scenario_path,
            design_path,
            scaffold,
            staging=staging,
        )
        _require_owned_directory(staging)
        if _path_lexists(plan.final_directory):
            raise WorkbenchCliError(
                "SCAFFOLD_EXISTS",
                "The scenario draft target already exists; existing content is never overwritten.",
            )
        _publish_staging_directory(
            plan.temporary_directory,
            plan.final_directory,
            staging=staging,
        )
        staging = None
    except WorkbenchCliError:
        if staging is not None:
            _cleanup_owned_staging(staging)
        _cleanup_empty_directories(created_directories)
        raise
    except (OSError, UnicodeError, ScenarioPackLoadError, ValueError):
        if staging is not None:
            _cleanup_owned_staging(staging)
        _cleanup_empty_directories(created_directories)
        raise WorkbenchCliError(
            "SCAFFOLD_PUBLISH_FAILED",
            "The complete draft directory could not be published safely.",
        ) from None


def _create_directory_chain(directory: Path) -> list[_OwnedDirectory]:
    missing: list[Path] = []
    cursor = directory
    while not _path_lexists(cursor):
        missing.append(cursor)
        if cursor.parent == cursor:
            break
        cursor = cursor.parent
    if not cursor.is_dir() or _is_link_or_junction(cursor):
        raise WorkbenchCliError(
            "OUTPUT_PATH_INVALID",
            "The output directory has an unsafe existing ancestor.",
        )
    created: list[_OwnedDirectory] = []
    try:
        for item in reversed(missing):
            parent = item.parent
            if (
                not parent.is_dir()
                or _is_link_or_junction(parent)
                or parent.resolve(strict=True) != parent
            ):
                raise WorkbenchCliError(
                    "OUTPUT_PATH_INVALID",
                    "The output directory has an unsafe existing ancestor.",
                )
            item.mkdir(exist_ok=False)
            created.append(_capture_owned_directory(item))
    except (OSError, WorkbenchCliError):
        _cleanup_empty_directories(created)
        raise
    return created


def _write_utf8_lf_file(path: Path, content: str) -> None:
    if "\r" in content or not content.endswith("\n"):
        raise ValueError("scaffold text is not normalized to LF with a final newline")
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


def _validate_staged_scaffold(
    scenario_path: Path,
    design_path: Path,
    scaffold: ScenarioScaffold,
    *,
    staging: _OwnedDirectory,
) -> None:
    _require_owned_directory(staging)
    loaded = JsonScenarioCatalogLoader(scenario_path).load()
    if loaded != scaffold.catalog:
        raise ValueError("staged scenario catalog differs from its in-memory model")
    analyzed = ScenarioAnalyzer().analyze(loaded.scenarios[0])
    if any(item.severity is DiagnosticSeverity.ERROR for item in analyzed.diagnostics):
        raise ValueError("staged scenario has a blocking analysis error")
    scenario_bytes = scenario_path.read_bytes()
    design_bytes = design_path.read_bytes()
    if scenario_bytes != scaffold.files[0].content.encode("utf-8"):
        raise ValueError("staged scenario bytes differ from the deterministic render")
    if design_bytes != scaffold.files[1].content.encode("utf-8"):
        raise ValueError("staged design bytes differ from the deterministic render")
    staged_files = (
        _scaffold_file_from_bytes(scaffold.files[0].relative_path, scenario_bytes),
        _scaffold_file_from_bytes(scaffold.files[1].relative_path, design_bytes),
    )
    if tuple(item.sha256 for item in staged_files) != tuple(
        item.sha256 for item in scaffold.files
    ):
        raise ValueError("staged file digest differs from the deterministic render")
    if combined_scaffold_digest(staged_files) != scaffold.content_digest:
        raise ValueError("staged combined digest differs from the deterministic render")
    _require_owned_directory(staging)


def _scaffold_file_from_bytes(relative_path: str, content: bytes) -> ScaffoldFile:
    decoded = content.decode("utf-8")
    return ScaffoldFile(
        relative_path=relative_path,
        content=decoded,
        sha256=sha256(content).hexdigest(),
        utf8_bytes=len(content),
    )


def _publish_staging_directory(
    source: Path,
    target: Path,
    *,
    staging: _OwnedDirectory,
) -> None:
    _require_owned_directory(staging)
    if not _DIRECTORY_RENAME_NO_REPLACE_SUPPORTED:
        raise WorkbenchCliError(
            "SCAFFOLD_PLATFORM_UNSUPPORTED",
            "Safe directory publication is unavailable on this platform.",
        )
    os.rename(source, target)


def _cleanup_owned_staging(staging: _OwnedDirectory) -> None:
    if not _owned_directory_matches(staging):
        return
    for filename in ("scenario.json", "design.md"):
        if not _owned_directory_matches(staging):
            return
        path = staging.path / filename
        try:
            if _path_lexists(path):
                path.unlink()
        except OSError:
            pass
    if not _owned_directory_matches(staging):
        return
    try:
        staging.path.rmdir()
    except OSError:
        pass


def _cleanup_empty_directories(directories: list[_OwnedDirectory]) -> None:
    for directory in reversed(directories):
        if not _owned_directory_matches(directory):
            break
        try:
            directory.path.rmdir()
        except OSError:
            break


def _capture_owned_directory(path: Path) -> _OwnedDirectory:
    if _is_link_or_junction(path) or not path.is_dir():
        raise OSError("created directory identity is unavailable")
    metadata = path.stat(follow_symlinks=False)
    return _OwnedDirectory(
        path=path,
        identity=_DirectoryIdentity(
            device=metadata.st_dev,
            inode=metadata.st_ino,
            created_ns=metadata.st_ctime_ns,
        ),
    )


def _owned_directory_matches(directory: _OwnedDirectory) -> bool:
    try:
        if _is_link_or_junction(directory.path) or not directory.path.is_dir():
            return False
        metadata = directory.path.stat(follow_symlinks=False)
    except OSError:
        return False
    return directory.identity == _DirectoryIdentity(
        device=metadata.st_dev,
        inode=metadata.st_ino,
        created_ns=metadata.st_ctime_ns,
    )


def _require_owned_directory(directory: _OwnedDirectory) -> None:
    if not _owned_directory_matches(directory):
        raise WorkbenchCliError(
            "SCAFFOLD_STAGING_CHANGED",
            "The scaffold staging directory identity changed during publication.",
        )


def _path_lexists(path: Path) -> bool:
    return os.path.lexists(path)


def _is_link_or_junction(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    return path.is_symlink() or bool(is_junction is not None and is_junction())


def _write_new_result(
    scaffold: ScenarioScaffold,
    *,
    dry_run: bool,
    as_json: bool,
) -> None:
    payload = {
        **scaffold.summary(),
        "dry_run": dry_run,
        "output_layout": f"{scaffold.scenario_id}/",
        "published": not dry_run,
    }
    if as_json:
        sys.stdout.write(_stable_json({"command": "new", "result": payload}) + "\n")
        return
    print("Scenario Workbench: new")
    print(f"scenario: {scaffold.scenario_id}")
    print(f"template: {SCENARIO_SCAFFOLD_TEMPLATE_VERSION}")
    print(f"dry run: {str(dry_run).lower()}")
    print(f"content digest: {scaffold.content_digest}")
    print("files:")
    for item in scaffold.files:
        print(f"  {item.relative_path} ({item.utf8_bytes} bytes, sha256={item.sha256})")


def _require_playable_character(catalog: ContentCatalog, character_id: str) -> None:
    if len(character_id) > MAX_CHARACTER_ID_CHARACTERS:
        raise WorkbenchCliError(
            "CHARACTER_INVALID",
            "The selected character identifier exceeds the configured length limit.",
        )
    character = catalog.character(character_id)
    if character is None or "npc" in character.tags or "player" not in character.tags:
        raise WorkbenchCliError(
            "CHARACTER_INVALID",
            "The selected character is not a playable ContentCatalog character.",
        )


def _require_input_file(raw_path: str, *, kind: str) -> Path:
    if not raw_path or len(raw_path) > MAX_INPUT_PATH_CHARACTERS:
        raise WorkbenchCliError(
            "INPUT_PATH_INVALID",
            f"The {kind} path is empty or exceeds the configured length limit.",
        )
    path = Path(raw_path)
    try:
        valid = path.exists() and path.is_file()
    except (OSError, ValueError):
        valid = False
    if not valid:
        raise WorkbenchCliError(
            "INPUT_PATH_INVALID",
            f"The {kind} path does not identify a readable file.",
        )
    return path


def _write_result(command: str, result: BaseModel, *, as_json: bool) -> None:
    payload = result.model_dump(mode="json")
    if as_json:
        sys.stdout.write(_stable_json({"command": command, "result": payload}) + "\n")
        return
    print(f"Scenario Workbench: {command}")
    print(f"scenario: {payload['scenario_id']}")
    print(f"content version: {payload['content_version']}")
    if command == "validate":
        counts = payload["counts"]
        print(
            "counts: "
            + ", ".join(f"{key}={counts[key]}" for key in sorted(counts))
        )
        print(f"initial phase: {payload['initial_phase_id']}")
        print(f"initial location: {payload['initial_location_id']}")
    elif command == "analyze":
        graph = payload["graph"]
        print(f"reachable phases: {len(graph['reachable_phase_ids'])}")
        print(f"unreachable phases: {len(graph['unreachable_phase_ids'])}")
        print(f"transitions: {len(graph['transitions'])}")
        print(f"cycles: {len(graph['cycles'])}")
        print(
            "endings: "
            f"potential={len(graph['potentially_reachable_ending_ids'])}, "
            f"unreachable={len(graph['unreachable_ending_ids'])}, "
            f"unknown={len(graph['ending_reachability_unknown_ids'])}"
        )
        print(
            "clues: "
            f"total={len(payload['clues'])}, "
            f"declared_source={sum(item['has_declared_source'] for item in payload['clues'])}, "
            "structurally_reachable_source="
            f"{sum(item['source_structurally_reachable'] for item in payload['clues'])}"
        )
        print(
            "facts: "
            + ", ".join(
                f"{key}={payload['facts']['counts_by_kind'][key]}"
                for key in sorted(payload["facts"]["counts_by_kind"])
            )
        )
        for cadence in payload["decision_cadence"]:
            print(
                f"cadence {cadence['phase_id']}: {cadence['cadence_type']}, "
                f"windows={cadence['window_count']}, "
                f"auto={cadence['min_auto_beats']}..{cadence['max_auto_beats']}"
            )
        for clock in payload["clocks"]:
            print(
                f"clock {clock['clock_id']}: "
                f"initial={clock['initial']}, maximum={clock['maximum']}, "
                f"visible={str(clock['player_visible']).lower()}, "
                "declared_progression_source="
                f"{str(clock['has_declared_progression_source']).lower()}, "
                "structurally_reachable_source="
                f"{str(clock['source_structurally_reachable']).lower()}"
            )
        print(f"frame budgets: {len(payload['frame_budgets'])}")
    else:
        print(f"preview identity: {payload['preview_identity_kind']}")
        print(f"decision binding scope: {payload['decision_binding_scope']}")
        print("production API credential: false")
        print(f"phase: {payload['phase_id']}")
        print(f"public location: {payload['public_location_id']}")
        print(
            "visible NPC IDs: "
            + (", ".join(payload["visible_npc_ids"]) or "(none)")
        )
        for fact in payload["player_known_facts"]:
            print(f"public fact {fact['fact_id']}: {_stable_json(fact['value'])}")
        for clock in payload["public_clocks"]:
            print(
                f"public clock {clock['clock_id']}: "
                f"{clock['value']}/{clock['maximum']}"
            )
        decision = payload["active_decision"]
        if decision is None:
            print("active decision: (none)")
        else:
            print(
                f"active decision: {decision['decision_id']} "
                f"reason={decision['reason']}"
            )
            print(
                "suggested action IDs: "
                + ", ".join(
                    action["action_id"] for action in decision["suggested_actions"]
                )
            )
        print(f"frame: {payload['frame_id']}")
    diagnostic_counts = payload.get("diagnostic_counts")
    if diagnostic_counts is not None:
        print(
            "diagnostics: "
            f"error={diagnostic_counts['error']}, "
            f"warning={diagnostic_counts['warning']}, "
            f"info={diagnostic_counts['info']}"
        )
        for item in payload.get("diagnostics", []):
            print(
                f"[{item['severity']}] {item['code']} "
                f"{item['subject_type']}:{item['subject_id']} - {item['message']}"
            )


def _write_error(code: str, message: str, *, as_json: bool) -> None:
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    stream = sys.stdout if as_json else sys.stderr
    if as_json:
        stream.write(_stable_json(payload) + "\n")
    else:
        stream.write(f"error {code}: {message}\n")


def _stable_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _configure_windows_utf8_streams() -> None:
    if os.name != "nt":
        return
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None and (stream.encoding or "").lower() != "utf-8":
            reconfigure(encoding="utf-8", errors="strict")


if __name__ == "__main__":
    raise SystemExit(main())
