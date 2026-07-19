from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, NoReturn

from pydantic import BaseModel

from deviation_protocol.application.scenario_analysis import (
    DiagnosticSeverity,
    ScenarioAnalyzer,
    build_initial_preview,
    validation_summary,
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
        description="Validate, analyze, or preview a local scenario pack.",
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
    return parser


def main(argv: list[str] | None = None) -> int:
    json_requested = argv is not None and "--json" in argv
    if argv is None:
        json_requested = "--json" in sys.argv[1:]
    try:
        arguments = build_parser().parse_args(argv)
        json_requested = bool(arguments.json)
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


if __name__ == "__main__":
    raise SystemExit(main())
