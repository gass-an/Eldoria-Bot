from __future__ import annotations

import pytest

from eldoria.ui.duels.games.rps import view as M
from tests._fakes import FakeBot, FakeDuelError, FakeDuelService, FakeInteraction, FakeUser


@pytest.mark.asyncio
async def test_play_success_calls_apply_snapshot(monkeypatch):
    monkeypatch.setattr(M, "DuelError", FakeDuelError)
    monkeypatch.setattr(M, "duel_error_message", lambda e: f"ERR:{e}")
    monkeypatch.setattr(M, "require_user_id", lambda *, interaction: 42)

    applied: list[dict] = []

    async def fake_apply(*, interaction, snapshot, bot):
        applied.append({"interaction": interaction, "snapshot": snapshot, "bot": bot})

    monkeypatch.setattr(M, "apply_duel_snapshot", fake_apply)

    duel = FakeDuelService()
    bot = FakeBot(duel)

    v = M.RpsView(bot=bot, duel_id=777)

    inter = FakeInteraction(user=FakeUser(42))

    await v._play(inter, move="ROCK")

    assert inter.response.deferred is True
    assert duel.play_game_action_calls == [
        {"duel_id": 777, "user_id": 42, "action": {"move": "ROCK"}}
    ]
    assert applied and applied[0]["snapshot"] == duel.snapshot_play_game_action

@pytest.mark.asyncio
async def test_play_duel_error_sends_ephemeral_and_does_not_apply(monkeypatch):
    monkeypatch.setattr(M, "DuelError", FakeDuelError)
    monkeypatch.setattr(M, "duel_error_message", lambda e: f"ERR:{e}")
    monkeypatch.setattr(M, "require_user_id", lambda *, interaction: 42)

    async def fake_apply(*, interaction, snapshot, bot):
        raise AssertionError("should not call")

    monkeypatch.setattr(M, "apply_duel_snapshot", fake_apply)

    duel = FakeDuelService()
    duel.raise_on_play_game_action = FakeDuelError("nope")
    bot = FakeBot(duel)

    v = M.RpsView(bot=bot, duel_id=777)
    inter = FakeInteraction(user=FakeUser(42))

    await v._play(inter, move="ROCK")

    assert inter.followup.sent
    last = inter.followup.sent[-1]
    assert last["content"] == "ERR:nope"
    assert last["ephemeral"] is True

@pytest.mark.asyncio
async def test_rock_calls_play_with_rock(monkeypatch):
    monkeypatch.setattr(M, "RPS_MOVE_ROCK", "ROCK")

    calls: list[str] = []

    async def fake_play(interaction, move):
        calls.append(move)

    duel = FakeDuelService()
    bot = FakeBot(duel)
    v = M.RpsView(bot=bot, duel_id=1)

    monkeypatch.setattr(v, "_play", fake_play)

    await v.rock(None, FakeInteraction(user=FakeUser(1)))  # type: ignore[arg-type]
    assert calls == ["ROCK"]

@pytest.mark.asyncio
async def test_paper_calls_play_with_paper(monkeypatch):
    monkeypatch.setattr(M, "RPS_MOVE_PAPER", "PAPER")

    calls: list[str] = []

    async def fake_play(interaction, move):
        calls.append(move)

    duel = FakeDuelService()
    bot = FakeBot(duel)
    v = M.RpsView(bot=bot, duel_id=1)

    monkeypatch.setattr(v, "_play", fake_play)

    await v.paper(None, FakeInteraction(user=FakeUser(1)))  # type: ignore[arg-type]
    assert calls == ["PAPER"]

@pytest.mark.asyncio
async def test_scissors_calls_play_with_scissors(monkeypatch):
    monkeypatch.setattr(M, "RPS_MOVE_SCISSORS", "SCISSORS")

    calls: list[str] = []

    async def fake_play(interaction, move):
        calls.append(move)

    duel = FakeDuelService()
    bot = FakeBot(duel)
    v = M.RpsView(bot=bot, duel_id=1)

    monkeypatch.setattr(v, "_play", fake_play)

    await v.scissors(None, FakeInteraction(user=FakeUser(1)))  # type: ignore[arg-type]
    assert calls == ["SCISSORS"]