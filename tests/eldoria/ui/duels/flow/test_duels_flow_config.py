from __future__ import annotations

from types import SimpleNamespace

import discord  # type: ignore
import pytest

from eldoria.ui.duels.flow import config as M
from tests._fakes import (
    FakeBot,
    FakeChannel,
    FakeDuelError,
    FakeDuelService,
    FakeGuild,
    FakeInteraction,
    FakeMember,
    FakeMessage,
    FakeUser,
)


def _make_channel_and_messages(*, first_message_id: int = 1000):
    """Channel minimal qui renvoie un message éditable (sans classes locales)."""

    sent: list[dict] = []
    next_mid = first_message_id

    async def send(*, content: str):
        nonlocal next_mid
        edits: list[dict] = []

        async def edit(*, content: str, embed=None, files=None, view=None):
            edits.append({"content": content, "embed": embed, "files": files, "view": view})

        msg = SimpleNamespace(id=next_mid, content=content, edits=edits, edit=edit)
        next_mid += 1
        sent.append({"content": content, "message": msg})
        return msg

    channel = SimpleNamespace(sent=sent, send=send)
    return channel

# -----------------------------
# build_config_stake_duels_embed
# -----------------------------
@pytest.mark.asyncio
async def test_build_config_stake_duels_embed_builds_embed_and_files(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1234)

    decorated = {"called": False}

    def fake_decorate(embed, thumb_url):
        decorated["called"] = True
        return embed

    monkeypatch.setattr(M, "decorate_thumb_only", fake_decorate)
    monkeypatch.setattr(M, "common_thumb", lambda thumb_url: ["F"])

    embed, files = await M.build_config_stake_duels_embed(expires_at=999)

    assert isinstance(embed, discord.Embed)
    assert embed.title == "Configuration du pari en XP"
    assert "La configuration expire <t:999:R>" in embed.description
    assert embed.colour == 1234
    assert embed.footer == {"text": "Choisi le pari ci-dessous."}
    assert decorated["called"] is True
    assert files == ["F"]

# -----------------------------
# StakeXpView __init__
# -----------------------------
def test_stake_xp_view_builds_buttons_disabled_based_on_allowed_stakes(monkeypatch):
    monkeypatch.setattr(M, "STAKE_XP_DEFAULTS", [10, 20, 30])

    duel = FakeDuelService()
    duel.allowed_stakes = {10, 30}
    bot = FakeBot(duel)

    view = M.StakeXpView(bot=bot, duel_id=777)

    assert len(view.children) == 3
    labels = [b.label for b in view.children]
    disabled = [b.disabled for b in view.children]

    assert labels == ["10", "20", "30"]
    assert disabled == [False, True, False]

# -----------------------------
# StakeXpView callback: succès
# -----------------------------
@pytest.mark.asyncio
async def test_stake_xp_view_click_success_flow(monkeypatch):
    monkeypatch.setattr(M, "STAKE_XP_DEFAULTS", [10])

    monkeypatch.setattr(M, "DuelError", FakeDuelError)
    monkeypatch.setattr(M, "duel_error_message", lambda e: f"ERR:{e}")

    duel = FakeDuelService()
    duel.allowed_stakes = {10}
    bot = FakeBot(duel)

    channel = _make_channel_and_messages()

    async def fake_get_channel(*, bot, channel_id):
        return channel

    monkeypatch.setattr(M, "get_text_or_thread_channel", fake_get_channel)

    guild = SimpleNamespace()
    monkeypatch.setattr(M, "require_guild", lambda *, interaction: guild)

    player_a = FakeMember(1, display_name="Alice")
    player_b = FakeMember(2, display_name="Bob")

    async def fake_get_member(g, uid):
        return player_a if uid == 1 else player_b

    monkeypatch.setattr(M, "get_member_by_id_or_raise", fake_get_member)

    async def fake_build_invite(player_a, player_b, xp_dict, stake_xp, expires_at, game_type):
        assert xp_dict == duel.snapshot_invite["xp"]
        assert stake_xp == duel.snapshot_invite["duel"]["stake_xp"]
        assert expires_at == duel.snapshot_invite["duel"]["expires_at"]
        assert game_type == duel.snapshot_invite["duel"]["game_type"]
        return ("INVITE_EMBED", ["INV_FILES"])

    monkeypatch.setattr(M, "build_invite_duels_embed", fake_build_invite)

    monkeypatch.setattr(M, "InviteView", lambda *, duel_id, bot: ("INVITE_VIEW", duel_id, bot))

    inter = FakeInteraction(user=FakeUser(42))
    inter.guild = guild
    inter.channel = None
    inter.message = None

    view = M.StakeXpView(bot=bot, duel_id=777)
    button = view.children[0]

    await button.callback(inter)  # type: ignore[misc]

    assert inter.response.deferred is True
    assert duel.configure_calls == [{"duel_id": 777, "stake_xp": 10}]

    assert len(channel.sent) == 1
    sent = channel.sent[0]
    assert sent["content"] == "<@2>. Quelqu'un vous provoque en duel !"
    msg = sent["message"]

    assert duel.send_invite_calls == [{"duel_id": 777, "message_id": msg.id}]

    assert msg.edits == [
        {
            "content": "||<@1> vs <@2>||",
            "embed": "INVITE_EMBED",
            "files": ["INV_FILES"],
            "view": ("INVITE_VIEW", 777, bot),
        }
    ]

    assert inter.original_edits
    assert inter.original_edits[-1]["content"] == "Invitation envoyée !"
    assert inter.original_edits[-1]["view"] is None

# -----------------------------
# StakeXpView callback: erreurs
# -----------------------------
@pytest.mark.asyncio
async def test_stake_xp_view_click_configure_raises_duel_error(monkeypatch):
    monkeypatch.setattr(M, "STAKE_XP_DEFAULTS", [10])
    monkeypatch.setattr(M, "DuelError", FakeDuelError)
    monkeypatch.setattr(M, "duel_error_message", lambda e: f"ERR:{e}")

    duel = FakeDuelService()
    duel.raise_on_configure = FakeDuelError("bad stake")
    bot = FakeBot(duel)

    monkeypatch.setattr(
        M,
        "get_text_or_thread_channel",
        lambda **k: (_ for _ in ()).throw(AssertionError("should not call")),
    )
    monkeypatch.setattr(
        M,
        "require_guild",
        lambda **k: (_ for _ in ()).throw(AssertionError("should not call")),
    )

    inter = FakeInteraction(user=FakeUser(42))

    view = M.StakeXpView(bot=bot, duel_id=777)
    button = view.children[0]

    await button.callback(inter)  # type: ignore[misc]

    assert duel.configure_calls == [{"duel_id": 777, "stake_xp": 10}]
    assert inter.original_edits
    assert inter.original_edits[-1]["content"] == "ERR:bad stake"
    assert inter.original_edits[-1]["view"] is None

@pytest.mark.asyncio
async def test_stake_xp_view_click_send_invite_raises_duel_error(monkeypatch):
    monkeypatch.setattr(M, "STAKE_XP_DEFAULTS", [10])
    monkeypatch.setattr(M, "DuelError", FakeDuelError)
    monkeypatch.setattr(M, "duel_error_message", lambda e: f"ERR:{e}")

    duel = FakeDuelService()
    duel.raise_on_send_invite = FakeDuelError("invite fail")
    bot = FakeBot(duel)

    channel = FakeChannel()

    async def fake_get_channel(*, bot, channel_id):
        return channel

    monkeypatch.setattr(M, "get_text_or_thread_channel", fake_get_channel)

    guild = FakeGuild()
    monkeypatch.setattr(M, "require_guild", lambda *, interaction: guild)

    monkeypatch.setattr(
        M,
        "build_invite_duels_embed",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not call")),
    )

    inter = FakeInteraction(user=FakeUser(42))

    view = M.StakeXpView(bot=bot, duel_id=777)
    button = view.children[0]

    await button.callback(inter)  # type: ignore[misc]

    assert len(channel.sent) == 1
    msg: FakeMessage = channel.sent[0]["message"]
    assert msg.edits == []

    assert inter.original_edits
    assert inter.original_edits[-1]["content"] == "ERR:invite fail"

@pytest.mark.asyncio
async def test_stake_xp_view_click_member_lookup_value_error(monkeypatch):
    monkeypatch.setattr(M, "STAKE_XP_DEFAULTS", [10])
    monkeypatch.setattr(M, "DuelError", FakeDuelError)
    monkeypatch.setattr(M, "duel_error_message", lambda e: f"ERR:{e}")

    duel = FakeDuelService()
    bot = FakeBot(duel)

    channel = FakeChannel()

    async def fake_get_channel(*, bot, channel_id):
        return channel

    monkeypatch.setattr(M, "get_text_or_thread_channel", fake_get_channel)

    guild = FakeGuild()
    monkeypatch.setattr(M, "require_guild", lambda *, interaction: guild)

    async def fake_get_member_raises(g, uid):
        raise ValueError("not found")

    monkeypatch.setattr(M, "get_member_by_id_or_raise", fake_get_member_raises)

    monkeypatch.setattr(
        M,
        "build_invite_duels_embed",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not call")),
    )

    inter = FakeInteraction(user=FakeUser(42))

    view = M.StakeXpView(bot=bot, duel_id=777)
    button = view.children[0]

    await button.callback(inter)  # type: ignore[misc]

    assert len(channel.sent) == 1
    msg: FakeMessage = channel.sent[0]["message"]
    assert msg.edits == []

    assert inter.original_edits
    assert inter.original_edits[-1]["content"] == "Un des participants n'a pas pu être trouvé."