"""Opening preparation repositories share the admission UoW and character lock."""
from dataclasses import asdict
import json

from sqlalchemy import select

from deviation_protocol.application.opening_preparation import OpeningPreparation
from deviation_protocol.application.native_run_admission import NativeRunAdmissionIntegrityError
from deviation_protocol.infrastructure.orm_models import OpeningPreparationRow


def encode(record):
    record.validate()
    return json.dumps(asdict(record), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def decode(raw):
    data = json.loads(raw)
    data["candidates"] = tuple(data["candidates"])
    data["selections"] = tuple(data["selections"])
    record = OpeningPreparation(**data).validate()
    if encode(record) != raw:
        raise NativeRunAdmissionIntegrityError("noncanonical opening preparation")
    return record


class SqlOpeningPreparationRepository:
    def __init__(self, session):
        self.session = session

    async def _one(self, query, locked=True):
        if locked:
            query = query.with_for_update()
        row = (await self.session.execute(query.execution_options(populate_existing=True))).scalar_one_or_none()
        if row is None:
            return None
        record = decode(row.record_canonical)
        if (row.preparation_id, row.owner, row.character_id, row.ordinal, row.request_key, row.state, row.run_id,
                row.pending_character_id) != (record.preparation_id, record.owner, record.character_id,
                record.ordinal, record.request_key, record.state, record.run_id,
                record.character_id if record.state == "PENDING" else None):
            raise NativeRunAdmissionIntegrityError("opening index association")
        return record

    async def get(self, identity, *, locked=False):
        return await self._one(select(OpeningPreparationRow).where(OpeningPreparationRow.preparation_id == identity), locked)

    async def latest(self, character_id, *, locked=True):
        return await self._one(select(OpeningPreparationRow).where(OpeningPreparationRow.character_id == character_id)
            .order_by(OpeningPreparationRow.ordinal.desc()).limit(1), locked)

    async def by_request(self, owner, key):
        return await self._one(select(OpeningPreparationRow).where(
            OpeningPreparationRow.owner == owner, OpeningPreparationRow.request_key == key))

    async def by_run(self, run_id):
        return await self._one(select(OpeningPreparationRow).where(OpeningPreparationRow.run_id == run_id), False)

    async def save(self, record):
        raw = encode(record)
        row = await self.session.get(OpeningPreparationRow, record.preparation_id)
        if row is None:
            row = OpeningPreparationRow(preparation_id=record.preparation_id, owner=record.owner,
                character_id=record.character_id, ordinal=record.ordinal, request_key=record.request_key)
            self.session.add(row)
        elif decode(row.record_canonical).state != "PENDING":
            raise NativeRunAdmissionIntegrityError("immutable opening confirmation")
        row.state, row.run_id = record.state, record.run_id
        row.pending_character_id = record.character_id if record.state == "PENDING" else None
        row.record_canonical = raw
        await self.session.flush()


class DemoOpeningPreparationRepository:
    def __init__(self, store, uow):
        self.store, self.uow = store, uow

    def _records(self):
        return {**self.store._opening_preparations, **self.uow._pending_opening_preparations}

    async def get(self, identity, *, locked=False):
        raw = self._records().get(identity)
        return None if raw is None else decode(raw)

    async def latest(self, character_id, *, locked=True):
        records = [decode(raw) for raw in self._records().values()]
        return max((r for r in records if r.character_id == character_id), key=lambda r: r.ordinal, default=None)

    async def by_request(self, owner, key):
        return next((r for raw in self._records().values() if (r := decode(raw)).owner == owner and r.request_key == key), None)

    async def by_run(self, run_id):
        return next((r for raw in self._records().values() if (r := decode(raw)).run_id == run_id), None)

    async def save(self, record):
        prior = await self.get(record.preparation_id)
        if prior is not None and prior.state != "PENDING":
            raise NativeRunAdmissionIntegrityError("immutable opening confirmation")
        self.uow._pending_opening_preparations[record.preparation_id] = encode(record)
