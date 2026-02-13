from __future__ import annotations

import pytest

from eldoria.ui.duels import apply as M


class FakeMember:
    def __init__(self, user_id: int):
        self.id = user_id
        self.mention = f"<@{user_id}>"


class FakeGuild:
    def __init__(self, members: dict[int, FakeMember] | None = None):
        self._members = members or {}

    def get_member(self, uid: int):
        return self._members.get(uid)


class FakeChannel:
    def __init__(self):
        self.sent: list[str] = []

    async def send(self, content: str):
        self.sent.append(content)


class FakeMessage:
    def __init__(self, content: str | None = None):
        self.content = content
        self.edits: list[dict] = []

    async def edit(self, *, content: str, embed=None, view=None):
        self.edits.append({"content": content, "embed": embed, "view": view})


class FakeInteraction:
    def __init__(self, *, guild, channel, message):
        self.guild = guild
        self.channel = channel
        self.message = message


@pytest.mark.asyncio
async def test_apply_duel_snapshot_returns_if_no_guild(monkeypatch):
    inter = FakeInteraction(guild=None, channel=FakeChannel(), message=FakeMessage("x"))

    # doit juste return sans edit ni send
    await M.apply_duel_snapshot(interaction=inter, snapshot={}, bot=object())
    assert inter.message.edits == []
    assert inter.channel.sent == []


@pytest.mark.asyncio
async def test_apply_duel_snapshot_edits_message_with_rendered_embed_and_view(monkeypatch):
    guild = FakeGuild()
    channel = FakeChannel()
    msg = FakeMessage(None)  # force fallback to ""

    inter = FakeInteraction(guild=guild, channel=channel, message=msg)

    async def fake_render_duel_message(*, snapshot, guild, bot):
        return ("EMBED", ["FILES"], "VIEW")

    # patch import local: eldoria.ui.duels.render.render_duel_message
    import eldoria.ui.duels.render as render_mod
    monkeypatch.setattr(render_mod, "render_duel_message", fake_render_duel_message)

    await M.apply_duel_snapshot(interaction=inter, snapshot={"duel": {}}, bot=object())

    assert msg.edits == [{"content": "", "embed": "EMBED", "view": "VIEW"}]
    # pas de level_changes => pas de send
    assert channel.sent == []


@pytest.mark.asyncio
async def test_apply_duel_snapshot_announces_level_up_and_down(monkeypatch):
    guild = FakeGuild(members={1: FakeMember(1), 2: FakeMember(2)})
    channel = FakeChannel()
    msg = FakeMessage("hello")

    inter = FakeInteraction(guild=guild, channel=channel, message=msg)

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

    sent = channel.sent[0].split("\n")
    assert sent[0] == "🎉 GG <@1> : tu atteins le rang  LVL3 grâce au duel !"
    assert sent[1] == "📉 Hélas, <@2> redescend au rang **LVL4** à cause du duel."


@pytest.mark.asyncio
async def test_apply_duel_snapshot_skips_invalid_changes_and_missing_member(monkeypatch):
    guild = FakeGuild(members={1: FakeMember(1)})
    channel = FakeChannel()
    msg = FakeMessage("hello")
    inter = FakeInteraction(guild=guild, channel=channel, message=msg)

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
    assert channel.sent[0] == "🎉 GG <@1> : tu atteins le rang  LVL2 grâce au duel !"


@pytest.mark.asyncio
async def test_apply_duel_snapshot_returns_if_no_channel(monkeypatch):
    guild = FakeGuild(members={1: FakeMember(1)})
    msg = FakeMessage("hello")
    inter = FakeInteraction(guild=guild, channel=None, message=msg)

    async def fake_render_duel_message(*, snapshot, guild, bot):
        return ("EMBED", [], None)

    import eldoria.ui.duels.render as render_mod
    monkeypatch.setattr(render_mod, "render_duel_message", fake_render_duel_message)

    snapshot = {"effects": {"level_changes": [{"user_id": 1, "old_level": 1, "new_level": 2}]}}
    await M.apply_duel_snapshot(interaction=inter, snapshot=snapshot, bot=object())

    # edit ok, mais pas d'annonce
    assert msg.edits
