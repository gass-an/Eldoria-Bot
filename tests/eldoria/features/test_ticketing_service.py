from __future__ import annotations

from eldoria.features.ticketing import ticketing_service as mod


def test_allocate_ticket_number_delegates_to_repo(monkeypatch):
    monkeypatch.setattr(mod.ticketing_repo, "tk_allocate_ticket_number", lambda guild_id: 42)

    assert mod.TicketingService().allocate_ticket_number(123) == 42


def test_record_ticket_delegates_to_repo(monkeypatch):
    calls = []
    monkeypatch.setattr(
        mod.ticketing_repo,
        "tk_record_ticket",
        lambda *args: calls.append(args),
    )

    mod.TicketingService().record_ticket(1, 2, 3, 4, 5)

    assert calls == [(1, 2, 3, 4, 5)]
