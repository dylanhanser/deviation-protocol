from __future__ import annotations


class TurnApplicationError(RuntimeError):
    """A stable application-boundary failure that is safe to report by code."""

    code = "TURN_APPLICATION_ERROR"

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"{self.code}: {session_id}")


class SessionNotFoundError(TurnApplicationError):
    code = "SESSION_NOT_FOUND"


class SnapshotNotFoundError(TurnApplicationError):
    code = "SNAPSHOT_NOT_FOUND"


class SnapshotStateVersionMismatchError(TurnApplicationError):
    code = "SNAPSHOT_STATE_VERSION_MISMATCH"


class SnapshotSchemaVersionMismatchError(TurnApplicationError):
    code = "SNAPSHOT_SCHEMA_VERSION_MISMATCH"


class SnapshotContentVersionMismatchError(TurnApplicationError):
    code = "SNAPSHOT_CONTENT_VERSION_MISMATCH"


class SnapshotInvalidError(TurnApplicationError):
    code = "SNAPSHOT_INVALID"


class SnapshotSessionMismatchError(TurnApplicationError):
    code = "SNAPSHOT_SESSION_MISMATCH"


class CandidateStateInvalidError(TurnApplicationError):
    code = "CANDIDATE_STATE_INVALID"


class StoredTurnResponseInvalidError(TurnApplicationError):
    code = "STORED_TURN_RESPONSE_INVALID"


class IdempotencyConflictError(TurnApplicationError):
    code = "IDEMPOTENCY_CONFLICT"


class UnsupportedResolutionError(TurnApplicationError):
    code = "UNSUPPORTED_RESOLUTION"


class ConcurrentTurnRequestError(RuntimeError):
    """Internal signal that the database idempotency constraint won a race."""


class ConcurrentSessionCreateError(RuntimeError):
    """Internal signal that the session creation uniqueness constraint won a race."""


class InvalidCharacterDefinitionError(ValueError):
    code = "INVALID_CHARACTER_DEFINITION"

    def __init__(self, character_definition_id: str) -> None:
        self.character_definition_id = character_definition_id
        super().__init__(self.code)
