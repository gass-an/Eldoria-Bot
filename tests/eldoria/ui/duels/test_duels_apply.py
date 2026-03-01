from __future__ import annotations

from types import SimpleNamespace

import pytest

from eldoria.ui.duels import apply as M
from tests._fakes import FakeChannel, FakeGuild, FakeMember, FakeMessage


@pytest.mark.asyncio
async def test_apply_duel_snapshot_returns_if_no_guild(monkeypatch):
    inter = SimpleNamespace(guild=None, channel=FakeChannel(), message=FakeMessage(content="x"))

    # doit juste return sans edit ni send
    await M.apply_duel_snapshot(interaction=inter, snapshot={}, bot=object())
    assert inter.message.edits == []
    assert inter.channel.sent == []


@pytest.mark.asyncio
async def test_apply_duel_snapshot_edits_message_with_rendered_embed_and_view(monkeypatch):
    guild = FakeGuild()
    channel = FakeChannel()
    msg = FakeMessage(content="")
    msg.content = None  # type: ignore[assignment]

    inter = SimpleNamespace(guild=guild, channel=channel, message=msg)

    async def fake_render_duel_message(*, snapshot, guild, bot):
        return ("EMBED", ["FILES"], "VIEW")

    # patch import local: eldoria.ui.duels.render.render_duel_message
    import eldoria.ui.duels.render as render_mod
    monkeypatch.setattr(render_mod, "render_duel_message", fake_render_duel_message)

    await M.apply_duel_snapshot(interaction=inter, snapshot={"duel": {}}, bot=object())

    assert msg.edits == [{"content": "", "embed": "EMBED", "view": "VIEW", "files": None}]
    # pas de level_changes => pas de send
    assert channel.sent == []


@pytest.mark.asyncio
async def test_apply_duel_snapshot_announces_level_up_and_down(monkeypatch):
    guild = FakeGuild()
    guild.add_member(FakeMember(1))
    guild.add_member(FakeMember(2))
    channel = FakeChannel()
    msg = FakeMessage(content="hello")

    inter = SimpleNamespace(guild=guild, channel=channel, message=msg)

    async def fake_render_duel_message(*, snapshot, guild, bot):
        return ("EMBED", [], None)

    import eldoria.ui.duels.render as render_mod
    monkeypatch.setattr(render_mod, "render_duel_message", fake_render_duel_message)

    # level_mention déterministe
    monkeypatch.setattr(M, "level_mention", lambda g, lvl, role_ids: f"LVL{lvl}")

    snapshot = {
        "effects": {
            "level_changes": [
                {"user_id": 1, "old_level": 2, "new_level": 3},
                {"user_id": 2, "old_level": 5, "new_level": 4},
            ],
            "xp_role_ids": {"3": 111, "4": 222},
        }
    }

    await M.apply_duel_snapshot(interaction=inter, snapshot=snapshot, bot=object())

    assert msg.edits  # edit fait
    assert len(channel.sent) == 1

    sent = (channel.sent[0]["content"] or "").split("\n")
    assert sent[0] == "🎉 GG <@1> : tu atteins le rang  LVL3 grâce au duel !"
    assert sent[1] == "📉 Hélas, <@2> redescend au rang **LVL4** à cause du duel."


@pytest.mark.asyncio
async def test_apply_duel_snapshot_skips_invalid_changes_and_missing_member(monkeypatch):
    guild = FakeGuild()
    guild.add_member(FakeMember(1))
    channel = FakeChannel()
    msg = FakeMessage(content="hello")
    inter = SimpleNamespace(guild=guild, channel=channel, message=msg)

    async def fake_render_duel_message(*, snapshot, guild, bot):
        return ("EMBED", [], None)

    import eldoria.ui.duels.render as render_mod
    monkeypatch.setattr(render_mod, "render_duel_message", fake_render_duel_message)

    monkeypatch.setattr(M, "level_mention", lambda g, lvl, role_ids: f"LVL{lvl}")

    snapshot = {
        "effects": {
            "level_changes": [
                {},  # invalid
                {"user_id": None, "old_level": 1, "new_level": 2},  # invalid
                {"user_id": 999, "old_level": 1, "new_level": 2},  # member missing
                {"user_id": 1, "old_level": 1, "new_level": 2},  # valid
            ]
        }
    }

    await M.apply_duel_snapshot(interaction=inter, snapshot=snapshot, bot=object())

    assert len(channel.sent) == 1
    assert channel.sent[0]["content"] == "🎉 GG <@1> : tu atteins le rang  LVL2 grâce au duel !"


@pytest.mark.asyncio
async def test_apply_duel_snapshot_returns_if_no_channel(monkeypatch):
    guild = FakeGuild()
    guild.add_member(FakeMember(1))
    msg = FakeMessage(content="hello")
    inter = SimpleNamespace(guild=guild, channel=None, message=msg)

    async def fake_render_duel_message(*, snapshot, guild, bot):
        return ("EMBED", [], None)

    import eldoria.ui.duels.render as render_mod
    monkeypatch.setattr(render_mod, "render_duel_message", fake_render_duel_message)

    snapshot = {"effects": {"level_changes": [{"user_id": 1, "old_level": 1, "new_level": 2}]}}
    await M.apply_duel_snapshot(interaction=inter, snapshot=snapshot, bot=object())

    # edit ok, mais pas d'annonce
    assert msg.edits
