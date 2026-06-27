from __future__ import annotations

import sqlite3

import pytest

from eldoria.db import connection, schema
from eldoria.db.repo import ticketing_repo


@pytest.fixture
def ticket_db(tmp_path, monkeypatch):
    db_path = tmp_path / "ticketing.db"
    monkeypatch.setattr(connection, "DB_PATH", str(db_path))
    schema.init_db()
    return db_path


def test_ticket_numbers_are_sequential_and_scoped_by_guild(ticket_db):
    assert ticketing_repo.tk_allocate_ticket_number(10) == 1
    assert ticketing_repo.tk_allocate_ticket_number(10) == 2
    assert ticketing_repo.tk_allocate_ticket_number(20) == 1
    assert ticketing_repo.tk_allocate_ticket_number(10) == 3


def test_ticket_numbers_continue_without_padding_limit_after_999(ticket_db):
    with connection.get_conn() as conn:
        conn.execute(
            "INSERT INTO ticket_sequences(guild_id, next_number) VALUES (?, ?)",
            (10, 999),
        )

    assert ticketing_repo.tk_allocate_ticket_number(10) == 999
    assert ticketing_repo.tk_allocate_ticket_number(10) == 1000
    assert f"ticket-{999:03d}" == "ticket-999"
    assert f"ticket-{1000:03d}" == "ticket-1000"


def test_record_ticket_persists_number_and_enforces_uniqueness_per_guild(ticket_db):
    ticketing_repo.tk_record_ticket(10, 1, 100, 1000, 123456)
    ticketing_repo.tk_record_ticket(20, 1, 200, 2000, 123457)

    with connection.get_conn() as conn:
        rows = conn.execute(
            """
            SELECT guild_id, ticket_number, channel_id, owner_id, status, created_at
            FROM tickets ORDER BY guild_id
            """
        ).fetchall()

    assert [tuple(row) for row in rows] == [
        (10, 1, 100, 1000, "OPEN", 123456),
        (20, 1, 200, 2000, "OPEN", 123457),
    ]

    with pytest.raises(sqlite3.IntegrityError):
        ticketing_repo.tk_record_ticket(10, 1, 101, 1001, 123458)
