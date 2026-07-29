"""Production opaque-identity issuers for the minimum Run core."""

from __future__ import annotations

import uuid

from deviation_protocol.domain.run import ContinuousStoryLineId, RunId


class Uuid4RunIdIssuer:
    """Issue domain-qualified Run identities from OS-random UUIDv4."""

    __slots__ = ()

    def issue(self) -> RunId:
        generated = uuid.uuid4()
        if type(generated) is not uuid.UUID or generated.version != 4:
            raise ValueError("uuid.uuid4() returned an invalid UUIDv4")
        return RunId(value=f"run.{generated.hex}")


class Uuid4ContinuousStoryLineIdIssuer:
    """Issue domain-qualified continuous-story-line identities from UUIDv4."""

    __slots__ = ()

    def issue(self) -> ContinuousStoryLineId:
        generated = uuid.uuid4()
        if type(generated) is not uuid.UUID or generated.version != 4:
            raise ValueError("uuid.uuid4() returned an invalid UUIDv4")
        return ContinuousStoryLineId(value=f"csl.{generated.hex}")
