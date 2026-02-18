from __future__ import annotations

import pytest

from eldoria.ui.duels import render as M


class _Guild:
    pass


@pytest.mark.asyncio
async def test_render_duel_message_raises_when_game_type_missing(monkeypatch):
    from eldoria.exceptions.duel import InvalidSnapshot

    snapshot = {"duel": {}}
    guild = _Guild()

    with pytest.raises(InvalidSnapshot):
        await M.render_duel_message(snapshot=snapshot, guild=guild, bot=object())


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
