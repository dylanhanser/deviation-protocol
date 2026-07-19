import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine



@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_8_connection_uses_test_schema_and_utc(
    mysql_engine: AsyncEngine,
) -> None:
    async with mysql_engine.connect() as connection:
        row = (
            await connection.execute(
                text(
                    "SELECT VERSION(), DATABASE(), @@session.time_zone, "
                    "@@transaction_isolation"
                )
            )
        ).one()

    assert int(str(row[0]).split(".", 1)[0]) >= 8
    assert row[1] == "deviation_protocol_test"
    assert row[2] == "+00:00"
    assert str(row[3]).upper() == "REPEATABLE-READ"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_migrated_mysql_schema_is_present(mysql_engine: AsyncEngine) -> None:
    async with mysql_engine.connect() as connection:
        revision = (
            await connection.execute(text("SELECT version_num FROM alembic_version"))
        ).scalar_one()
        tables = (
            await connection.execute(
                text(
                    "SELECT TABLE_NAME, ENGINE, TABLE_COLLATION "
                    "FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = DATABASE()"
                )
            )
        ).all()
        json_columns = set(
            (
                await connection.execute(
                    text(
                        "SELECT TABLE_NAME, COLUMN_NAME "
                        "FROM information_schema.COLUMNS "
                        "WHERE TABLE_SCHEMA = DATABASE() AND DATA_TYPE = 'json'"
                    )
                )
            ).all()
        )
        foreign_keys = set(
            (
                await connection.execute(
                    text(
                        "SELECT TABLE_NAME, REFERENCED_TABLE_NAME, DELETE_RULE "
                        "FROM information_schema.REFERENTIAL_CONSTRAINTS "
                        "WHERE CONSTRAINT_SCHEMA = DATABASE()"
                    )
                )
            ).all()
        )
        indexes = set(
            (
                await connection.execute(
                    text(
                        "SELECT TABLE_NAME, INDEX_NAME "
                        "FROM information_schema.STATISTICS "
                        "WHERE TABLE_SCHEMA = DATABASE()"
                    )
                )
            ).all()
        )
        narrative_columns = {
            row[0]: row[1:]
            for row in (
                await connection.execute(
                    text(
                        "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, "
                        "CHARACTER_MAXIMUM_LENGTH "
                        "FROM information_schema.COLUMNS "
                        "WHERE TABLE_SCHEMA = DATABASE() "
                        "AND TABLE_NAME = 'narrative_jobs'"
                    )
                )
            ).all()
        }
        narrative_index_rows = (
            await connection.execute(
                text(
                    "SELECT INDEX_NAME, SEQ_IN_INDEX, COLUMN_NAME, NON_UNIQUE "
                    "FROM information_schema.STATISTICS "
                    "WHERE TABLE_SCHEMA = DATABASE() "
                    "AND TABLE_NAME = 'narrative_jobs' "
                    "ORDER BY INDEX_NAME, SEQ_IN_INDEX"
                )
            )
        ).all()

    assert revision == "20260719_0003"
    table_details = {row[0]: (row[1], row[2]) for row in tables}
    expected_tables = {
        "alembic_version",
        "domain_events",
        "game_sessions",
        "game_snapshots",
        "turn_requests",
        "narrative_jobs",
    }
    assert set(table_details) == expected_tables
    assert all(engine == "InnoDB" for engine, _ in table_details.values())
    assert all(collation.startswith("utf8mb4_") for _, collation in table_details.values())
    assert json_columns == {
        ("domain_events", "payload_json"),
        ("game_snapshots", "state_json"),
        ("turn_requests", "request_json"),
        ("turn_requests", "response_json"),
        ("narrative_jobs", "narrative_request_json"),
        ("narrative_jobs", "validated_proposal_json"),
    }
    assert foreign_keys == {
        ("domain_events", "game_sessions", "CASCADE"),
        ("game_snapshots", "game_sessions", "CASCADE"),
        ("turn_requests", "game_sessions", "CASCADE"),
        ("narrative_jobs", "game_sessions", "CASCADE"),
    }
    assert {
        ("domain_events", "uq_domain_events_session_sequence"),
        ("turn_requests", "uq_turn_requests_session_client_request"),
        ("game_sessions", "uq_game_sessions_player_creation_request"),
        ("game_sessions", "ix_game_sessions_scenario"),
        ("turn_requests", "ix_turn_requests_signature"),
        ("narrative_jobs", "uq_narrative_jobs_session_client_request"),
        ("narrative_jobs", "ix_narrative_jobs_session_status"),
        ("narrative_jobs", "ix_narrative_jobs_status_lease"),
        ("narrative_jobs", "ix_narrative_jobs_session_turn"),
    } <= indexes
    assert len(narrative_columns) == 27
    assert narrative_columns["job_id"] == ("varchar", "NO", None, 64)
    assert narrative_columns["session_id"] == ("varchar", "NO", None, 64)
    assert narrative_columns["narrative_request_json"] == (
        "json",
        "NO",
        None,
        None,
    )
    assert narrative_columns["validated_proposal_json"] == (
        "json",
        "YES",
        None,
        None,
    )
    assert narrative_columns["attempt_count"] == ("int", "NO", "0", None)
    assert narrative_columns["lease_expires_at"][:2] == ("datetime", "YES")
    assert narrative_columns["accepted_narrative_text"][:2] == ("text", "YES")
    grouped_indexes: dict[str, tuple[tuple[str, int], ...]] = {}
    for index_name in {row[0] for row in narrative_index_rows}:
        grouped_indexes[index_name] = tuple(
            (row[2], row[3]) for row in narrative_index_rows if row[0] == index_name
        )
    assert grouped_indexes == {
        "PRIMARY": (("job_id", 0),),
        "uq_narrative_jobs_session_client_request": (
            ("session_id", 0),
            ("client_request_id", 0),
        ),
        "ix_narrative_jobs_session_status": (
            ("session_id", 1),
            ("status", 1),
        ),
        "ix_narrative_jobs_status_lease": (
            ("status", 1),
            ("lease_expires_at", 1),
        ),
        "ix_narrative_jobs_session_turn": (
            ("session_id", 1),
            ("turn_id", 1),
        ),
    }
