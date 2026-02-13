from __future__ import annotations

import pytest

from eldoria.ui.duels import render as M


class _Guild:
    pass


@pytest.mark.asyncio
async def test_render_duel_message_raises_when_game_type_missing(monkeypatch):
    snapshot = {"duel": {}}
    guild = _Guild()

    with pytest.raises(ValueError) as e:
        await M.render_duel_message(snapshot=snapshot, guild=guild, bot=object())
    assert "snapshot.duel.game_type manquant" in str(e.value)


@pytest.mark.asyncio
async def test_render_duel_message_calls_renderer(monkeypatch):
    called: list[dict] = []

    async def fake_renderer(snapshot, guild, bot):
        called.append({"snapshot": snapshot, "guild": guild, "bot": bot})
        return ("embed", ["files"], "view")

    monkeypatch.setattr(M, "require_renderer", lambda key: fake_renderer)

    snapshot = {"duel": {"game_type": "rps"}}
    guild = _Guild()
    bot = object()

    out = await M.render_duel_message(snapshot=snapshot, guild=guild, bot=bot)
    assert out == ("embed", ["files"], "view")
    assert called and called[-1]["snapshot"] == snapshot
    assert called[-1]["guild"] is guild
    assert called[-1]["bot"] is bot


@pytest.mark.asyncio
async def test_render_duel_message_syncs_roles_when_xp_changed_and_user_ids_present(monkeypatch):
    sync_calls: list[dict] = []

    async def fake_sync(guild, user_ids):
        sync_calls.append({"guild": guild, "user_ids": user_ids})

    async def fake_renderer(snapshot, guild, bot):
        return ("embed", ["files"], None)

    monkeypatch.setattr(M, "sync_xp_roles_for_users", fake_sync)
    monkeypatch.setattr(M, "require_renderer", lambda key: fake_renderer)

    snapshot = {
        "duel": {"game_type": "rps"},
        "effects": {"xp_changed": True, "sync_roles_user_ids": [1, 2, 3]},
    }
    guild = _Guild()

    await M.render_duel_message(snapshot=snapshot, guild=guild, bot=object())

    assert sync_calls == [{"guild": guild, "user_ids": [1, 2, 3]}]


@pytest.mark.asyncio
async def test_render_duel_message_does_not_sync_when_user_ids_empty(monkeypatch):
    sync_calls: list[dict] = []

    async def fake_sync(guild, user_ids):
        sync_calls.append({"guild": guild, "user_ids": user_ids})

    async def fake_renderer(snapshot, guild, bot):
        return ("embed", ["files"], None)

    monkeypatch.setattr(M, "sync_xp_roles_for_users", fake_sync)
    monkeypatch.setattr(M, "require_renderer", lambda key: fake_renderer)

    snapshot = {
        "duel": {"game_type": "rps"},
        "effects": {"xp_changed": True, "sync_roles_user_ids": []},
    }
    guild = _Guild()

    await M.render_duel_message(snapshot=snapshot, guild=guild, bot=object())

    assert sync_calls == []


@pytest.mark.asyncio
async def test_render_duel_message_swallows_sync_errors(monkeypatch):
    async def fake_sync(guild, user_ids):
        raise RuntimeError("discord refused")

    async def fake_renderer(snapshot, guild, bot):
        return ("embed", ["files"], None)

    monkeypatch.setattr(M, "sync_xp_roles_for_users", fake_sync)
    monkeypatch.setattr(M, "require_renderer", lambda key: fake_renderer)

    snapshot = {
        "duel": {"game_type": "rps"},
        "effects": {"xp_changed": True, "sync_roles_user_ids": [1]},
    }
    guild = _Guild()

    # ne doit pas lever
    out = await M.render_duel_message(snapshot=snapshot, guild=guild, bot=object())
    assert out == ("embed", ["files"], None)
