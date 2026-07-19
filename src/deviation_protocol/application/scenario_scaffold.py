from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
import unicodedata
from typing import Any

from deviation_protocol.application.scenario_analysis import (
    DiagnosticSeverity,
    ScenarioAnalysisReport,
    ScenarioAnalyzer,
    scenario_counts,
)
from deviation_protocol.domain.scenario import (
    SUPPORTED_SCENARIO_SCHEMA_VERSION,
    ScenarioCatalog,
)


SCENARIO_SCAFFOLD_TEMPLATE_VERSION = "scenario-scaffold-v1"
MAX_SCAFFOLD_TITLE_CHARACTERS = 100
MAX_SCAFFOLD_PREMISE_CHARACTERS = 400

_WHITESPACE = re.compile(r"\s+")


class ScenarioScaffoldInputError(ValueError):
    """A bounded scaffold input cannot be normalized safely."""


@dataclass(frozen=True, slots=True)
class ScaffoldFile:
    relative_path: str
    content: str
    sha256: str
    utf8_bytes: int


@dataclass(frozen=True, slots=True)
class ScenarioScaffold:
    scenario_id: str
    title: str
    premise: str
    catalog: ScenarioCatalog
    analysis: ScenarioAnalysisReport
    files: tuple[ScaffoldFile, ...]
    content_digest: str

    def summary(self) -> dict[str, Any]:
        counts = scenario_counts(self.catalog.scenarios[0]).model_dump(mode="json")
        return {
            "content_version": self.catalog.content_version,
            "content_digest": self.content_digest,
            "content_summary": {
                "draft_marked": True,
                "premise_characters": len(self.premise),
                "premise_unverified": True,
                "title_characters": len(self.title),
            },
            "files": [
                {
                    "path": item.relative_path,
                    "sha256": item.sha256,
                    "utf8_bytes": item.utf8_bytes,
                }
                for item in self.files
            ],
            "scenario_id": self.scenario_id,
            "structure": {
                **counts,
                "initial_location_id": self.catalog.scenarios[0].initial_location_id,
                "initial_phase_id": self.catalog.scenarios[0].initial_phase_id,
            },
            "template_version": SCENARIO_SCAFFOLD_TEMPLATE_VERSION,
            "validation": {
                "blocking_errors": self.analysis.diagnostic_counts.error,
                "catalog_valid": True,
                "preview": "requires_matching_content_pack_and_playable_character",
            },
        }


def normalize_scaffold_text(
    value: str,
    *,
    label: str,
    maximum: int,
) -> str:
    if not isinstance(value, str):
        raise ScenarioScaffoldInputError(f"{label} must be text")
    normalized = unicodedata.normalize("NFC", value)
    if any(
        unicodedata.category(character) in {"Cc", "Cf", "Cs"}
        for character in normalized
    ):
        raise ScenarioScaffoldInputError(f"{label} contains a Unicode control character")
    normalized = _WHITESPACE.sub(" ", normalized).strip()
    if not normalized or len(normalized) > maximum:
        raise ScenarioScaffoldInputError(f"{label} is empty or exceeds its length limit")
    return normalized


def build_scenario_scaffold(
    *,
    scenario_id: str,
    title: str,
    premise: str,
    content_version: str,
    schema_version: int = SUPPORTED_SCENARIO_SCHEMA_VERSION,
) -> ScenarioScaffold:
    """Construct deterministic draft artifacts without file or environment access."""

    normalized_title = normalize_scaffold_text(
        title,
        label="title",
        maximum=MAX_SCAFFOLD_TITLE_CHARACTERS,
    )
    normalized_premise = normalize_scaffold_text(
        premise,
        label="premise",
        maximum=MAX_SCAFFOLD_PREMISE_CHARACTERS,
    )
    if (
        type(schema_version) is not int
        or schema_version != SUPPORTED_SCENARIO_SCHEMA_VERSION
    ):
        raise ScenarioScaffoldInputError("scenario schema version is not supported")

    prefix = f"draft.{sha256(scenario_id.encode('utf-8')).hexdigest()[:16]}"
    phase_opening = f"{prefix}.phase.opening"
    phase_investigation = f"{prefix}.phase.investigation"
    phase_conflict = f"{prefix}.phase.core_conflict"
    phase_resolution = f"{prefix}.phase.resolution"
    location_initial = f"{prefix}.location.initial"
    draft_fact = f"{prefix}.fact.review_status"

    payload = {
        "schema_version": schema_version,
        "content_version": content_version,
        "content_catalog": {
            "schema_version": 1,
            "content_version": content_version,
            "characters": [],
            "npcs": [],
            "items": [],
            "equipment": [],
            "skills": [],
            "effects": [],
        },
        "scenarios": [
            {
                "scenario_id": scenario_id,
                "schema_version": schema_version,
                "content_version": content_version,
                "title": f"DRAFT: {normalized_title}",
                "summary": f"DRAFT premise (unverified): {normalized_premise}",
                "initial_phase_id": phase_opening,
                "initial_location_id": location_initial,
                "locations": [
                    {
                        "location_id": location_initial,
                        "title": "DRAFT 初始地点占位",
                        "summary": "DRAFT：待人工设计与内容审查的通用地点占位。",
                        "initially_open": True,
                        "visible_entity_ids": [],
                    }
                ],
                "npc_references": [],
                "facts": [
                    {
                        "fact_id": draft_fact,
                        "kind": "FIXED",
                        "visibility": "PLAYER_KNOWN",
                        "value": "DRAFT_UNREVIEWED",
                    }
                ],
                "clues": [],
                "clue_groups": [],
                "threat_clocks": [],
                "decision_windows": [],
                "phases": [
                    {
                        "phase_id": phase_opening,
                        "title": "DRAFT 开局占位",
                        "must_render_fact_ids": [draft_fact],
                        "visible_location_ids": [location_initial],
                        "allowed_action_types": ["observe"],
                        "min_auto_beats": 2,
                        "max_auto_beats": 4,
                        "transitions": [
                            {
                                "transition_id": f"{prefix}.transition.opening_to_investigation",
                                "target_phase_id": phase_investigation,
                                "trigger": "AUTOMATIC",
                                "conditions": [
                                    {"rule_type": "PHASE_BEAT_AT_LEAST", "value": 2}
                                ],
                            }
                        ],
                        "tone_hints": ["DRAFT 通用低频开局节奏占位"],
                    },
                    {
                        "phase_id": phase_investigation,
                        "title": "DRAFT 调查阶段占位",
                        "must_render_fact_ids": [draft_fact],
                        "visible_location_ids": [location_initial],
                        "allowed_action_types": ["investigate", "observe"],
                        "min_auto_beats": 2,
                        "max_auto_beats": 4,
                        "transitions": [
                            {
                                "transition_id": f"{prefix}.transition.investigation_to_conflict",
                                "target_phase_id": phase_conflict,
                                "trigger": "AUTOMATIC",
                                "conditions": [
                                    {"rule_type": "PHASE_BEAT_AT_LEAST", "value": 2}
                                ],
                            }
                        ],
                        "tone_hints": ["DRAFT 调查结构占位"],
                    },
                    {
                        "phase_id": phase_conflict,
                        "title": "DRAFT 核心冲突占位",
                        "must_render_fact_ids": [draft_fact],
                        "visible_location_ids": [location_initial],
                        "allowed_action_types": ["observe"],
                        "min_auto_beats": 1,
                        "max_auto_beats": 2,
                        "transitions": [
                            {
                                "transition_id": f"{prefix}.transition.conflict_to_resolution",
                                "target_phase_id": phase_resolution,
                                "trigger": "AUTOMATIC",
                                "conditions": [
                                    {"rule_type": "PHASE_BEAT_AT_LEAST", "value": 1}
                                ],
                            }
                        ],
                        "tone_hints": ["DRAFT 核心冲突结构占位"],
                    },
                    {
                        "phase_id": phase_resolution,
                        "title": "DRAFT 终局与结算占位",
                        "must_render_fact_ids": [draft_fact],
                        "visible_location_ids": [location_initial],
                        "allowed_action_types": ["observe"],
                        "min_auto_beats": 0,
                        "max_auto_beats": 0,
                        "terminal": True,
                        "tone_hints": ["DRAFT 结局占位"],
                    },
                ],
                "endings": [
                    {
                        "ending_id": f"{prefix}.ending.draft_resolution",
                        "status": "RESOLVED",
                        "conditions": [
                            {
                                "rule_type": "PHASE_VISIT_AT_LEAST",
                                "phase_id": phase_resolution,
                                "value": 1,
                            }
                        ],
                    }
                ],
                "available_profession_tags": [],
                "story_item_definition_ids": [],
                "dynamic_fact_limit": 1,
                "dynamic_fact_key_max_length": 40,
                "dynamic_fact_value_max_length": 80,
                "narrative_length": {"target": 240, "minimum": 120, "maximum": 360},
                "narrative_outcome_rules": [],
            }
        ],
    }
    catalog = ScenarioCatalog.model_validate(payload)
    analysis = ScenarioAnalyzer().analyze(catalog.scenarios[0])
    if any(item.severity is DiagnosticSeverity.ERROR for item in analysis.diagnostics):
        raise ScenarioScaffoldInputError("generated scaffold has a blocking analysis error")

    scenario_json = _render_json(catalog.model_dump(mode="json"))
    design_markdown = _render_design_markdown(
        scenario_id=scenario_id,
        title=normalized_title,
        premise=normalized_premise,
        content_version=content_version,
    )
    files = (
        _scaffold_file(f"{scenario_id}/scenario.json", scenario_json),
        _scaffold_file(f"{scenario_id}/design.md", design_markdown),
    )
    return ScenarioScaffold(
        scenario_id=scenario_id,
        title=normalized_title,
        premise=normalized_premise,
        catalog=catalog,
        analysis=analysis,
        files=files,
        content_digest=combined_scaffold_digest(files),
    )


def _render_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    ) + "\n"


def _render_design_markdown(
    *,
    scenario_id: str,
    title: str,
    premise: str,
    content_version: str,
) -> str:
    workbench_module = "deviation_protocol." + "tools.scenario"
    lines = [
        "# DRAFT Scenario Design",
        "",
        "> DRAFT：此 scaffold 不是正式剧情，尚未通过人工内容审查。premise 仅是用户提供的草案说明，不是已验证世界事实。",
        "",
        f"- Scenario ID: `{scenario_id}`",
        f"- Content version: `{content_version}`",
        f"- Scaffold template: `{SCENARIO_SCAFFOLD_TEMPLATE_VERSION}`",
        "",
        "## 用户提供的草案数据",
        "",
        "Title（规范化原文，仅作为数据）：",
        "",
        f"    {title}",
        "",
        "Premise（规范化原文、未验证，仅作为数据）：",
        "",
        f"    {premise}",
        "",
        "## 待填写清单",
        "",
        "- [ ] 核心冲突",
        "- [ ] 开局特色",
        "- [ ] 固定/隐藏/延迟事实",
        "- [ ] NPC 知识边界",
        "- [ ] 线索与 N/M 组",
        "- [ ] 威胁时钟",
        "- [ ] 低频与 rapid 决策节奏",
        "- [ ] outcome rules",
        "- [ ] 结局",
        "- [ ] 隐藏信息审查",
        "",
        "## 本地验证工作流",
        "",
        "以下命令中的 `<output-dir>`、`<matching-content-pack>` 与 `<playable-character-id>` 需要替换为本地相对路径或匹配值：",
        "",
        "```powershell",
        f"$scenario = Join-Path '<output-dir>' '{scenario_id}\\scenario.json'",
        f".\\.venv\\Scripts\\python.exe -m {workbench_module} validate $scenario",
        f".\\.venv\\Scripts\\python.exe -m {workbench_module} analyze $scenario",
        f".\\.venv\\Scripts\\python.exe -m {workbench_module} preview $scenario --content-pack <matching-content-pack> --character-id <playable-character-id>",
        "```",
        "",
        "## 边界",
        "",
        "此模板只提供通用 DRAFT 结构，不生成正式剧情、NPC、装备、技能、可信事件、outcome token、capability、seal、脚本表达式或自动测试代码。人工完成内容与隐藏信息审查后，才可手动复制并纳入正式 scenario 目录及其索引/测试流程。",
    ]
    return "\n".join(lines) + "\n"


def _scaffold_file(relative_path: str, content: str) -> ScaffoldFile:
    encoded = content.encode("utf-8")
    return ScaffoldFile(
        relative_path=relative_path,
        content=content,
        sha256=sha256(encoded).hexdigest(),
        utf8_bytes=len(encoded),
    )


def combined_scaffold_digest(files: tuple[ScaffoldFile, ...]) -> str:
    """Bind ordered file names and bytes with unambiguous length prefixes."""

    digest = sha256(b"scenario-scaffold-content-v1\0")
    for item in files:
        relative_path = item.relative_path.encode("utf-8")
        content = item.content.encode("utf-8")
        digest.update(len(relative_path).to_bytes(8, "big"))
        digest.update(relative_path)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()
