from __future__ import annotations

import unicodedata
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class NativeRunExitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_run_state_version: int = Field(ge=1, le=2**63 - 1)
    expected_session_state_version: int = Field(ge=0, le=2**63 - 1)


class NativeRunStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["native-run-status/v1"]
    session_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    run_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    run_state_version: int = Field(ge=1, le=2**63 - 1)
    session_state_version: int = Field(ge=0, le=2**63 - 1)
    lifecycle_status: Literal["active", "terminated"]
    can_exit: bool

    @model_validator(mode="after")
    def _state(self):
        if (self.run_state_version not in ((3,4,5) if self.lifecycle_status == "active" else (4,5,6))
                or self.lifecycle_status == "terminated" and self.can_exit):
            raise ValueError("invalid native lifecycle projection")
        return self

from deviation_protocol.application.turn_response import TurnResponse
from deviation_protocol.application.session_service import (
    NarrativeRequestStatusResult,
    PublicNarrativeRequestStatus,
    NarrativeRequestClientAction,
)
from deviation_protocol.application.player_character_projection import (
    PlayerCharacterSelfProjection,
)
from deviation_protocol.domain.actions import (
    MAX_ACTION_DESCRIPTION_LENGTH,
    MAX_ACTION_DIALOGUE_LENGTH,
    ActionSubmission,
    ActionType,
)
from deviation_protocol.domain.narrative import NarrativeFrame


SafeId64 = Annotated[
    str,
    Field(
        strict=True,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
    ),
]
SafeId128 = Annotated[
    str,
    Field(
        strict=True,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
    ),
]


class RunEntryRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )

    player_character_id: SafeId128
    expected_record_revision: Annotated[
        int,
        Field(strict=True, ge=1, le=2**63 - 1),
    ]
    scenario_id: SafeId128


class RunEntryResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )

    run_id: SafeId128
    session_id: SafeId64
    scenario_id: SafeId128
    player_character: PlayerCharacterSelfProjection


from deviation_protocol.application.public_run_protocol import (
    PublicRunModel, PublicProfileRef, PublicWorldRef, PublicRunPresentation,
    PublicNativeRunContext, PositiveInt64, ObjectiveName, ObjectiveValue,
)


class NativeRunOverride(PublicRunModel):
    parameter: ObjectiveName
    value: ObjectiveValue


class NativeRunEntryRequest(PublicRunModel):
    player_character_id: SafeId128
    expected_record_revision: PositiveInt64
    profile_ref: PublicProfileRef
    entry_world: PublicWorldRef
    overrides: Annotated[tuple[NativeRunOverride, ...], Field(max_length=5)]
    presentation: PublicRunPresentation

    @model_validator(mode="after")
    def unique_overrides(self):
        if len({entry.parameter for entry in self.overrides}) != len(self.overrides):
            raise ValueError("duplicate override parameter")
        return self


class NativeRunEntryResponse(PublicRunModel):
    session_id: SafeId64
    scenario_id: SafeId128
    scenario_content_version: Annotated[str, Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")]
    run_context: PublicNativeRunContext


class StrictApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def reject_unicode_controls(cls, value: object) -> object:
        values: tuple[object, ...]
        if isinstance(value, (list, tuple, set, frozenset)):
            values = tuple(value)
        else:
            values = (value,)
        for item in values:
            if isinstance(item, str) and any(
                unicodedata.category(character) in {"Cc", "Cf"} for character in item
            ):
                raise ValueError("Unicode control characters are not allowed")
        return value


class CreateSessionRequest(StrictApiModel):
    client_request_id: SafeId64
    character_definition_id: SafeId128
    scenario_id: SafeId128


class ActionRequest(StrictApiModel):
    turn_id: SafeId64
    client_request_id: SafeId64
    action_type: ActionType
    target_ids: tuple[SafeId128, ...] = Field(default=(), max_length=16)
    tool_ids: tuple[SafeId128, ...] = Field(default=(), max_length=16)
    description: Annotated[
        str,
        Field(strict=True, min_length=1, max_length=MAX_ACTION_DESCRIPTION_LENGTH),
    ] | None = None
    dialogue: Annotated[
        str,
        Field(strict=True, min_length=1, max_length=MAX_ACTION_DIALOGUE_LENGTH),
    ] | None = None
    decision_id: SafeId128 | None = None
    choice_id: SafeId128 | None = None
    item_instance_id: SafeId128 | None = None
    equipment_slot_id: SafeId128 | None = None
    skill_definition_id: SafeId128 | None = None

    @model_validator(mode="after")
    def validate_continue_payload(self) -> ActionRequest:
        if self.action_type is not ActionType.CONTINUE:
            return self
        payload_fields = {
            "target_ids",
            "tool_ids",
            "description",
            "dialogue",
            "decision_id",
            "choice_id",
            "item_instance_id",
            "equipment_slot_id",
            "skill_definition_id",
        }
        if self.model_fields_set.intersection(payload_fields):
            raise ValueError("CONTINUE does not accept an action payload")
        return self

    def to_submission(self, session_id: str) -> ActionSubmission:
        return ActionSubmission(
            session_id=session_id,
            **self.model_dump(),
        )


class ActionResponse(BaseModel):
    """Player-safe action result without persistence-only integrity fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: SafeId64
    client_request_id: SafeId64
    resolution_kind: Literal[
        "RESOLVED_LOCAL",
        "REJECTED_LOCAL",
        "NARRATIVE_REQUIRED",
        "NARRATIVE_COMMITTED",
    ]
    result_code: str
    feedback_code: str
    feedback_parameters: dict[str, Any] = Field(default_factory=dict)
    resulting_state_version: int = Field(ge=0)
    state_changed: bool
    narrative_required: bool
    narrative_pending: bool
    narrative_frame: NarrativeFrame | None = None
    narrative_text: str | None = Field(default=None, min_length=1, max_length=10_000)
    narrative_status: Literal["PENDING", "COMMITTED"] | None = None
    local_query_result: dict[str, Any] | None = None

    @classmethod
    def from_turn_response(cls, response: TurnResponse) -> ActionResponse:
        return cls(
            session_id=response.session_id,
            client_request_id=response.client_request_id,
            resolution_kind=response.resolution_kind.value,
            result_code=response.result_code,
            feedback_code=response.feedback_code,
            feedback_parameters=dict(response.feedback_parameters),
            resulting_state_version=response.resulting_state_version,
            state_changed=response.state_changed,
            narrative_required=response.narrative_required,
            narrative_pending=response.narrative_pending,
            narrative_frame=response.narrative_frame,
            narrative_text=response.narrative_text,
            narrative_status=response.narrative_status,
            local_query_result=(
                dict(response.local_query_result)
                if response.local_query_result is not None
                else None
            ),
        )


class NarrativeRequestStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: SafeId64
    client_request_id: SafeId64
    status: PublicNarrativeRequestStatus
    client_action: NarrativeRequestClientAction
    error_code: Annotated[
        str, Field(strict=True, pattern=r"^[A-Z][A-Z0-9_]{0,127}$")
    ] | None = None
    retry_after_seconds: int | None = Field(default=None, ge=1, le=60)
    response: ActionResponse | None = None

    @model_validator(mode="after")
    def validate_status_shape(self) -> NarrativeRequestStatusResponse:
        if self.status is PublicNarrativeRequestStatus.PENDING:
            valid = (
                self.client_action is NarrativeRequestClientAction.POLL_SAME_REQUEST
                and self.retry_after_seconds is not None
                and self.error_code is None
                and self.response is None
            )
        elif self.status is PublicNarrativeRequestStatus.COMMITTED:
            valid = (
                self.client_action
                is NarrativeRequestClientAction.RESPONSE_AVAILABLE
                and self.response is not None
                and self.retry_after_seconds is None
                and self.error_code is None
            )
        else:
            expected = {
                PublicNarrativeRequestStatus.STALE: (
                    NarrativeRequestClientAction.REFRESH_VIEW,
                    "NARRATIVE_REQUEST_STALE",
                ),
                PublicNarrativeRequestStatus.OUTCOME_UNKNOWN: (
                    NarrativeRequestClientAction.DO_NOT_RETRY,
                    "NARRATIVE_OUTCOME_UNKNOWN",
                ),
                PublicNarrativeRequestStatus.FAILED: (
                    NarrativeRequestClientAction.DO_NOT_RETRY,
                    "NARRATIVE_REQUEST_FAILED",
                ),
            }[self.status]
            valid = (
                (self.client_action, self.error_code) == expected
                and self.retry_after_seconds is None
                and self.response is None
            )
        if not valid:
            raise ValueError("narrative request status response has an invalid shape")
        return self

    @classmethod
    def from_application_result(
        cls, result: NarrativeRequestStatusResult
    ) -> NarrativeRequestStatusResponse:
        return cls(
            session_id=result.session_id,
            client_request_id=result.client_request_id,
            status=result.status,
            client_action=result.client_action,
            error_code=result.error_code,
            retry_after_seconds=result.retry_after_seconds,
            response=(
                ActionResponse.from_turn_response(result.response)
                if result.response is not None
                else None
            ),
        )


class NativeRunContinuationRequest(NativeRunExitRequest):
    pass


class NativeWorldVisitResponse(BaseModel):
    model_config = ConfigDict(extra="forbid",strict=True)
    visit_id: str = Field(min_length=1,max_length=128,pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    visit_ordinal: int = Field(ge=1,le=2)
    world_id: str = Field(min_length=1,max_length=128,pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    world_version: int = Field(ge=1,le=2**63-1)
    region_id: str = Field(min_length=1,max_length=128,pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    region_version: int = Field(ge=1,le=2**63-1)

    @model_validator(mode="after")
    def _identity(self):
        if self.world_id == "world.fog_station":
            expected_region = "region.fog_station.station" if self.visit_ordinal == 1 else "region.fog_station.patrol_pass"
            if self.region_id != expected_region or self.world_version != 1 or self.region_version != 1:
                raise ValueError("invalid fog visit identity")
            return self
        expected = (("world.death_certificate", "region.death_certificate.facility")
            if self.visit_ordinal == 1 else ("world.undelivered_receipt", "region.undelivered_receipt.dispatch_hall"))
        if (self.world_id, self.region_id) != expected or self.world_version != 1 or self.region_version != 1:
            raise ValueError("invalid authored visit identity")
        return self


class NativeRunPredecessorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid",strict=True)
    session_id: str = Field(min_length=1,max_length=64,pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    session_state_version: int = Field(ge=0,le=2**63-1)
    scenario_id: str = Field(min_length=1,max_length=128,pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    scenario_content_version: str = Field(min_length=1,max_length=32,pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    visit: NativeWorldVisitResponse

    @model_validator(mode="after")
    def _first(self):
        if self.visit.world_id == "world.fog_station":
            if self.visit.visit_ordinal != 1 or (self.scenario_id, self.scenario_content_version) != ("fog_station", "fog-station-1.0.0"):
                raise ValueError("invalid fog predecessor")
            return self
        if (self.visit.visit_ordinal != 1 or self.scenario_id != "death_certificate"
                or self.scenario_content_version != "death-certificate-1.1.0"):
            raise ValueError("predecessor must be visit one")
        return self


class NativeRunContinuationResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid",strict=True)
    schema_version: Literal["native-run-continuation-result/v1"]
    source_session_id: str = Field(min_length=1,max_length=64,pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    source_session_state_version: int = Field(ge=0,le=2**63-1)
    run_id: str = Field(min_length=1,max_length=128,pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    resulting_run_state_version: int = Field(ge=4,le=4)
    session_id: str = Field(min_length=1,max_length=64,pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    initial_session_state_version: int = Field(ge=0,le=0)
    scenario_id: Literal["undelivered_receipt", "fog_patrol"]
    scenario_content_version: Literal["undelivered-receipt-1.0.0", "fog-patrol-1.0.0"]
    run_context: PublicNativeRunContext
    visit: NativeWorldVisitResponse

    @model_validator(mode="after")
    def _second(self):
        expected = ("fog_patrol", "fog-patrol-1.0.0", "world.fog_station") if self.visit.world_id == "world.fog_station" else ("undelivered_receipt", "undelivered-receipt-1.0.0", "world.death_certificate")
        if (self.scenario_id, self.scenario_content_version, self.run_context.entry_world.entry_world_id) != expected:
            raise ValueError("crossed continuation world/content")
        if self.visit.visit_ordinal != 2 or self.source_session_id == self.session_id or self.run_id != self.run_context.run_id:
            raise ValueError("invalid continuation edge")
        return self


class NativeWorldArrivalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    previous_ending_status: Literal["RESOLVED", "FAILED"]
    previous_ending_title: str = Field(min_length=1, max_length=120)
    entry_notice: str = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def _authored(self):
        from deviation_protocol.application.fog_continuation_service import NOTICE, ENDING_TITLES as FOG_ENDINGS
        if self.previous_ending_title in FOG_ENDINGS.values():
            if self.previous_ending_status != "RESOLVED" or self.entry_notice != NOTICE:
                raise ValueError("invalid fog arrival")
            return self
        from deviation_protocol.application.world_visit_context import ENTRY_NOTICES, ENDING_TITLES
        titles = (tuple(ENDING_TITLES.values())[:2] if self.previous_ending_status == "RESOLVED"
                  else (ENDING_TITLES["death_certificate.ending.deadline_reached"],))
        if self.previous_ending_title not in titles or self.entry_notice != ENTRY_NOTICES[self.previous_ending_status]:
            raise ValueError("invalid authored arrival annotation")
        return self


class NativeRunContinuationStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid",strict=True)
    schema_version: Literal["native-run-continuation-status/v1"]
    session_id: str = Field(min_length=1,max_length=64,pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    run_id: str = Field(min_length=1,max_length=128,pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    run_state_version: int = Field(ge=3,le=5)
    session_state_version: int = Field(ge=0,le=2**63-1)
    lifecycle_status: Literal["active","terminated"]
    can_continue: bool
    current_session_id: str = Field(min_length=1,max_length=64,pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    visit: NativeWorldVisitResponse | None
    predecessor: NativeRunPredecessorResponse | None
    successor: NativeRunContinuationResultResponse | None
    arrival: NativeWorldArrivalResponse | None

    @model_validator(mode="after")
    def _edge(self):
        if (self.arrival is not None) != (self.visit is not None and self.visit.visit_ordinal == 2):
            raise ValueError("arrival requires the destination visit")
        expected_revision = (3 if self.visit is None else 4) + (self.lifecycle_status == "terminated")
        if self.run_state_version != expected_revision:
            raise ValueError("invalid continuation lifecycle")
        if self.can_continue and (self.run_state_version != 3 or self.visit is not None):
            raise ValueError("invalid continuation eligibility")
        if self.visit is None:
            if self.predecessor is not None or self.successor is not None or self.current_session_id != self.session_id:
                raise ValueError("invalid first visit association")
        elif self.visit.visit_ordinal == 2:
            if self.predecessor is None or self.successor is not None or self.current_session_id != self.session_id or self.predecessor.session_id == self.session_id:
                raise ValueError("incomplete successor association")
        elif (self.predecessor is not None or self.successor is None or self.successor.source_session_id != self.session_id
                or self.successor.session_id != self.current_session_id or self.successor.run_id != self.run_id
                or self.successor.source_session_state_version != self.session_state_version):
            raise ValueError("incomplete predecessor association")
        return self


class NativeRunRevisitRequest(NativeRunExitRequest):
    pass


class NativeJourneyVisitResponse(NativeWorldVisitResponse):
    visit_ordinal: int = Field(ge=1, le=3)

    @model_validator(mode="after")
    def _identity(self):
        if self.world_id == "world.fog_station":
            if self.visit_ordinal not in (1, 2):
                raise ValueError("no third fog visit")
            return super()._identity()
        pairs = {1: ("world.death_certificate", "region.death_certificate.facility"),
                 2: ("world.undelivered_receipt", "region.undelivered_receipt.dispatch_hall"),
                 3: ("world.undelivered_receipt", "region.undelivered_receipt.verification_archive")}
        if ((self.world_id, self.region_id) != pairs[self.visit_ordinal]
                or self.world_version != 1 or self.region_version != 1):
            raise ValueError("invalid journey visit identity")
        return self


class NativeVisitAssociationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    session_id: SafeId64
    session_state_version: int = Field(ge=0, le=2**63 - 1)
    scenario_id: SafeId128
    scenario_content_version: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    visit: NativeJourneyVisitResponse | None

    @model_validator(mode="after")
    def _catalogue(self):
        if self.visit is None:
            from deviation_protocol.domain.entry_world import AUTHORED_ENTRY_WORLDS_V1
            if any((self.scenario_id, self.scenario_content_version) == (w.scenario_id, w.scenario_content_version)
                   for w in AUTHORED_ENTRY_WORLDS_V1):
                return self
        if self.visit is not None and self.visit.world_id == "world.fog_station":
            expected = ("fog_station", "fog-station-1.0.0") if self.visit.visit_ordinal == 1 else ("fog_patrol", "fog-patrol-1.0.0")
            if (self.scenario_id, self.scenario_content_version) != expected:
                raise ValueError("fog visit/content mismatch")
            return self
        ordinal = 1 if self.visit is None else self.visit.visit_ordinal
        expected = {1: ("death_certificate", "death-certificate-1.1.0"),
                    2: ("undelivered_receipt", "undelivered-receipt-1.0.0"),
                    3: ("receipt_archive", "receipt-archive-1.0.0")}
        if (self.scenario_id, self.scenario_content_version) != expected[ordinal]:
            raise ValueError("visit content mismatch")
        return self


class NativeJourneyArrivalResponse(NativeWorldArrivalResponse):
    @model_validator(mode="after")
    def _authored(self):
        from deviation_protocol.domain.world_revisit import ARCHIVE_NOTICE
        if (self.previous_ending_status, self.previous_ending_title, self.entry_notice) == (
                "RESOLVED", "回执待核，发运暂缓", ARCHIVE_NOTICE):
            return self
        return super()._authored()


class NativeNextTransitionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    kind: Literal["first_continuation", "regional_revisit", "fog_patrol"]
    world_title: str = Field(min_length=1, max_length=120)
    region_title: str = Field(min_length=1, max_length=120)
    notice: str = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def _authored(self):
        if self.kind == "fog_patrol":
            from deviation_protocol.application.fog_continuation_service import NOTICE
            if (self.world_title, self.region_title, self.notice) != ("雾哨站", "巡路风口", NOTICE):
                raise ValueError("invalid fog transition")
            return self
        from deviation_protocol.domain.world_revisit import ARCHIVE_NOTICE
        expected = ("核验档案室", ARCHIVE_NOTICE) if self.kind == "regional_revisit" else (
            "发运大厅", "沿用当前角色和剩余资源进入发运大厅；原有资源不会恢复。")
        if self.world_title != "未送达的回执" or (self.region_title, self.notice) != expected:
            raise ValueError("invalid authored transition")
        return self


class NativeRunJourneyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["native-run-journey/v1"]
    session_id: SafeId64
    run_id: SafeId128
    run_state_version: int = Field(ge=3, le=6)
    lifecycle_status: Literal["active", "terminated"]
    run_context: PublicNativeRunContext
    path: NativeVisitAssociationResponse
    current: NativeVisitAssociationResponse
    predecessor: NativeVisitAssociationResponse | None
    successor: NativeVisitAssociationResponse | None
    next_transition: NativeNextTransitionResponse | None
    arrival: NativeJourneyArrivalResponse | None

    @model_validator(mode="after")
    def _chain(self):
        if self.session_id != self.path.session_id or self.run_id != self.run_context.run_id:
            raise ValueError("crossed journey identity")
        if self.current.visit is None:
            from deviation_protocol.domain.entry_world import AUTHORED_ENTRY_WORLDS_V1
            world = next((w for w in AUTHORED_ENTRY_WORLDS_V1
                if (w.entry_world_id.value, w.entry_world_version.value) == (
                    self.run_context.entry_world.entry_world_id, self.run_context.entry_world.entry_world_version)), None)
            if world is None or (self.current.scenario_id, self.current.scenario_content_version) != (world.scenario_id, world.scenario_content_version):
                raise ValueError("journey admission world mismatch")
            if world.scenario_id not in ("death_certificate", "fog_station") and self.next_transition is not None:
                raise ValueError("starting world has no published continuation")
            if (self.path != self.current or self.predecessor is not None or self.successor is not None
                    or self.arrival is not None):
                raise ValueError("invalid unmaterialized journey")
            count, ordinal = 1, 1
        else:
            if self.run_context.entry_world.entry_world_id not in ("world.death_certificate", "world.fog_station"):
                raise ValueError("unpublished continuation world")
            if self.path.visit is None:
                raise ValueError("missing materialized path")
            count, ordinal = self.current.visit.visit_ordinal, self.path.visit.visit_ordinal
            if count not in (2, 3) or ordinal > count:
                raise ValueError("invalid current position")
            for neighbor, expected in ((self.predecessor, ordinal - 1), (self.successor, ordinal + 1)):
                if 1 <= expected <= count:
                    if (neighbor is None or neighbor.visit is None or neighbor.visit.visit_ordinal != expected
                            or neighbor.session_id == self.session_id):
                        raise ValueError("missing or crossed journey neighbor")
                elif neighbor is not None:
                    raise ValueError("extra journey neighbor")
            if (ordinal == count) != (self.path == self.current):
                raise ValueError("journey current path mismatch")
            fog = self.run_context.entry_world.entry_world_id == "world.fog_station"
            if fog and (count != 2 or any(row is not None and row.visit.world_id != "world.fog_station"
                    for row in (self.path, self.current, self.predecessor, self.successor))):
                raise ValueError("crossed fog journey")
            if not fog and any(row is not None and row.visit.world_id == "world.fog_station"
                    for row in (self.path, self.current, self.predecessor, self.successor)):
                raise ValueError("crossed old journey")
            if ordinal == 2:
                from deviation_protocol.application.fog_continuation_service import NOTICE
                if self.arrival is None or (self.arrival.entry_notice == NOTICE) != fog:
                    raise ValueError("crossed arrival")
            associations = [row for row in (self.path, self.current, self.predecessor, self.successor) if row is not None]
            for index, left in enumerate(associations):
                for right in associations[index + 1:]:
                    if left.visit.visit_ordinal == right.visit.visit_ordinal:
                        if left != right:
                            raise ValueError("contradictory repeated journey association")
                    elif left.session_id == right.session_id or left.visit.visit_id == right.visit.visit_id:
                        raise ValueError("duplicate journey identity")
            if (self.arrival is None) != (ordinal == 1):
                raise ValueError("journey arrival mismatch")
            if ordinal == 3 and self.arrival.previous_ending_title != "回执待核，发运暂缓":
                raise ValueError("regional arrival mismatch")
            if ordinal == 2 and self.arrival.previous_ending_title == "回执待核，发运暂缓":
                raise ValueError("continued arrival mismatch")
        if self.run_state_version != count + 2 + (self.lifecycle_status != "active"):
            raise ValueError("journey lifecycle mismatch")
        if self.next_transition is not None:
            if (self.path != self.current or self.lifecycle_status != "active" or count == 3
                    or (self.run_context.entry_world.entry_world_id == "world.fog_station" and count != 1)
                    or self.next_transition.kind != ("fog_patrol" if self.run_context.entry_world.entry_world_id == "world.fog_station" else "first_continuation" if count == 1 else "regional_revisit")):
                raise ValueError("unavailable journey transition")
        return self


class NativeRunRevisitResultResponse(NativeRunContinuationResultResponse):
    schema_version: Literal["native-run-revisit-result/v1"]
    resulting_run_state_version: int = Field(ge=5, le=5)
    scenario_id: Literal["receipt_archive"]
    scenario_content_version: Literal["receipt-archive-1.0.0"]
    visit: NativeJourneyVisitResponse

    @model_validator(mode="after")
    def _second(self):
        if self.visit.visit_ordinal != 3 or self.source_session_id == self.session_id or self.run_id != self.run_context.run_id:
            raise ValueError("invalid regional edge")
        return self


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error_code: str
    message: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error: ErrorDetail


class NativeRunCompletionRequest(NativeRunExitRequest):
    pass


class NativeRunCanonOutcomeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    dispatch: Literal["held"]
    delivery: Literal["unproven"]
    record: Literal["sealed"]
    verification: Literal["closed_unresolved"]


class NativeRunCompletionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    completion_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome: Literal["unresolved_record_preserved"]
    title: Literal["待核事项保留，核验旅程已结案"]
    notice: Literal["本次旅程已正常完成。发运暂缓继续有效，送达仍未得到证明；旧记录与资源保持原状。"]
    canon_outcome: NativeRunCanonOutcomeResponse


class NativeRunCompletionOfferResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    title: Literal["完成本次旅程：保留待核事项"]
    notice: Literal["封存待核记录已确认；可以将本次旅程以待核事项保留结案。发运暂缓继续有效，送达仍未得到证明。"]


class NativeRunCompletedStatusResponse(NativeRunStatusResponse):
    schema_version: Literal["native-run-status/v2"]
    lifecycle_status: Literal["completed"]
    run_state_version: int = Field(ge=6, le=6)
    can_exit: Literal[False]


class NativeRunCompletedJourneyResponse(NativeRunJourneyResponse):
    schema_version: Literal["native-run-journey/v2"]
    lifecycle_status: Literal["completed"]
    run_state_version: int = Field(ge=6, le=6)
    next_transition: None
    completion: NativeRunCompletionResponse

    @model_validator(mode="after")
    def _completed(self):
        if self.current.visit is None or self.current.visit.visit_ordinal != 3:
            raise ValueError("completion requires the third visit")
        return self


NativeRunStatusUnion = Annotated[NativeRunStatusResponse | NativeRunCompletedStatusResponse, Field(discriminator="schema_version")]
NativeRunJourneyUnion = Annotated[NativeRunJourneyResponse | NativeRunCompletedJourneyResponse, Field(discriminator="schema_version")]


class NativeRunCompletionStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["native-run-completion-status/v1"]
    session_id: SafeId64
    run_id: SafeId128
    run_state_version: int = Field(ge=3, le=6)
    lifecycle_status: Literal["active", "terminated", "completed"]
    run_context: PublicNativeRunContext
    path: NativeVisitAssociationResponse
    current: NativeVisitAssociationResponse
    can_complete: bool
    reason: Literal["eligible", "run_terminal", "not_current_visit", "character_ineligible",
                    "session_not_ended", "ending_not_eligible", "route_not_eligible"]
    offer: NativeRunCompletionOfferResponse | None
    completion: NativeRunCompletionResponse | None

    @model_validator(mode="after")
    def _association(self):
        count = self.current.visit.visit_ordinal if self.current.visit else 1
        if (self.run_id != self.run_context.run_id or self.session_id != self.path.session_id
                or self.run_state_version != count + 2 + (self.lifecycle_status != "active")
                or self.can_complete != (self.reason == "eligible")
                or self.can_complete != (self.offer is not None)
                or (self.lifecycle_status == "completed") != (self.completion is not None)
                or (self.lifecycle_status != "active") != (self.reason == "run_terminal")):
            raise ValueError("completion status association")
        if self.can_complete and (self.lifecycle_status != "active" or count != 3 or self.path != self.current):
            raise ValueError("invalid completion offer")
        if self.lifecycle_status == "completed" and count != 3:
            raise ValueError("invalid completed position")
        return self


class NativeRunCompletionResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["native-run-completion-result/v1"]
    source_session_id: SafeId64
    source_session_state_version: int = Field(ge=0, le=2**63 - 1)
    run_id: SafeId128
    resulting_run_state_version: int = Field(ge=6, le=6)
    lifecycle_status: Literal["completed"]
    run_context: PublicNativeRunContext
    visit: NativeJourneyVisitResponse
    completion: NativeRunCompletionResponse

    @model_validator(mode="after")
    def _association(self):
        if self.run_id != self.run_context.run_id or self.visit.visit_ordinal != 3:
            raise ValueError("completion result association")
        return self
