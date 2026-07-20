from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.json_values import FrozenJsonDict, freeze_json_object


_PERSISTED_EVENT_RECEIPT_ISSUER = object()


def canonical_event_payload_digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class _ReceiptSeal:
    target: object
    issuer: object
    digest: str


@dataclass(frozen=True, slots=True, init=False)
class PersistedEventReceipt:
    """Opaque proof that an event row was inserted and flushed in the current UoW.

    A receipt is deliberately not a Pydantic model and has no public constructor.
    It is an in-process transaction capability, not proof that the transaction
    later committed.
    """

    session_id: str
    event_id: str
    sequence_no: int
    turn_id: str
    state_version: int
    event_type: str
    payload_digest: str
    _payload: FrozenJsonDict
    _seal: _ReceiptSeal

    def __new__(cls, *_: object, **__: object) -> PersistedEventReceipt:
        raise TypeError("persisted event receipts can only be issued after repository flush")

    def __copy__(self) -> PersistedEventReceipt:
        return self

    def __deepcopy__(self, _: dict[int, object]) -> PersistedEventReceipt:
        return self

    def is_authentic(self) -> bool:
        try:
            seal = self._seal
            return (
                seal.target is self
                and seal.issuer is _PERSISTED_EVENT_RECEIPT_ISSUER
                and self.payload_digest == canonical_event_payload_digest(self._payload)
                and seal.digest == _receipt_digest(self)
            )
        except (AttributeError, TypeError, ValueError):
            return False

    def authoritative_payload(self) -> FrozenJsonDict:
        if not self.is_authentic():
            raise ValueError("persisted event receipt is not authentic")
        return self._payload


def _issue_persisted_event_receipt(
    event: DomainEvent, *, state_version: int
) -> PersistedEventReceipt:
    """Infrastructure-only issuance seam called after a successful event flush."""

    if not isinstance(event, DomainEvent):
        raise TypeError("persisted event receipt requires a domain event")
    if type(state_version) is not int or state_version < 0:
        raise ValueError("persisted event state version must be non-negative")
    if type(event.sequence_no) is not int or event.sequence_no < 1:
        raise ValueError("persisted event sequence must be positive")
    payload = freeze_json_object(event.payload, path="persisted event payload")
    receipt = object.__new__(PersistedEventReceipt)
    for name, value in (
        ("session_id", event.session_id),
        ("event_id", event.event_id),
        ("sequence_no", event.sequence_no),
        ("turn_id", event.turn_id),
        ("state_version", state_version),
        ("event_type", event.event_type),
        ("payload_digest", canonical_event_payload_digest(payload)),
        ("_payload", payload),
    ):
        object.__setattr__(receipt, name, value)
    object.__setattr__(
        receipt,
        "_seal",
        _ReceiptSeal(
            target=receipt,
            issuer=_PERSISTED_EVENT_RECEIPT_ISSUER,
            digest=_receipt_digest(receipt),
        ),
    )
    return receipt


def _receipt_digest(receipt: PersistedEventReceipt) -> str:
    return canonical_event_payload_digest(
        {
            "event_id": getattr(receipt, "event_id", None),
            "event_type": getattr(receipt, "event_type", None),
            "payload_digest": getattr(receipt, "payload_digest", None),
            "sequence_no": getattr(receipt, "sequence_no", None),
            "session_id": getattr(receipt, "session_id", None),
            "state_version": getattr(receipt, "state_version", None),
            "turn_id": getattr(receipt, "turn_id", None),
        }
    )
