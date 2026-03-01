from __future__ import annotations

from types import SimpleNamespace

import discord  # type: ignore
import pytest

from eldoria.ui.duels.flow import invite as M
from tests._fakes import (
    FakeBot,
    FakeDuelError,
    FakeDuelService,
    FakeFetchMessageChannel,
    FakeInteraction,
    FakeMember,
    FakeMessage,
    FakeUser,
)


def _make_message(*, content: str = "", mid: int = 999):
    edits: list[dict] = []

    async def edit(*, content: str, embed=None, view=None, files=None):
        edits.append({"content": content, "embed": embed, "view": view, "files": files})

    return SimpleNamespace(id=mid, content=content, edits=edits, edit=edit)

# ------------------------------------------------------------
# build_invite_duels_embed
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_build_invite_duels_embed_builds_fields_footer_and_files(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 123)

    # game text
    monkeypatch.setattr(M, "get_game_text", lambda gt: ("RPS", "Pierre feuille ciseaux"))

    decorated = {"called": False}

    def fake_decorate_thumb(embed, thumb_url):
        decorated["called"] = True
        return embed

    monkeypatch.setattr(M, "decorate_thumb_only", fake_decorate_thumb)
    monkeypatch.setattr(M, "common_thumb", lambda thumb_url: ["FILE"])

    a = FakeMember(1, display_name="Alice")
    b = FakeMember(2, display_name="Bob")

    xp = {1: 10, 2: 20}

    embed, files = await M.build_invite_duels_embed(
        a, b, xp, stake_xp=50, expires_at=999, game_type="rps"
    )

    assert isinstance(embed, discord.Embed)
    assert embed.title == "Invitation à un duel"
    assert "Cette invitation expire <t:999:R>" in embed.description
    assert "**Bob** est provoqué" in embed.description
    assert embed.colour == 123

    # fields
    assert len(embed.fields) == 3

    f0 = embed.fields[0]
    assert f0["name"] == "Vos points d'XP actuels:"
    assert "Alice : 10 XP" in f0["value"]
    assert "Bob : 20 XP" in f0["value"]
    assert f0["inline"] is True

    f1 = embed.fields[1]
    assert f1["name"] == "Points d'XP mis en jeu"
    assert f1["value"] == "50 XP"
    assert f1["inline"] is True

    f2 = embed.fields[2]
    assert f2["name"] == "Type de jeu"
    assert "RPS" in f2["value"]
    assert "Pierre feuille ciseaux" in f2["value"]
    assert f2["inline"] is False

    assert embed.footer == {"text": "Bob fais ton choix : Accepter ou Refuser ?"}
    assert decorated["called"] is True
    assert files == ["FILE"]

# ------------------------------------------------------------
# InviteView.accept
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_invite_view_accept_duel_error_sends_ephemeral(monkeypatch):
    monkeypatch.setattr(M, "DuelError", FakeDuelError)
    monkeypatch.setattr(M, "duel_error_message", lambda e: f"ERR:{e}")

    duel = FakeDuelService()
    duel.raise_on_accept = FakeDuelError("nope")
    bot = FakeBot(duel)

    # require_user_id
    monkeypatch.setattr(M, "require_user_id", lambda *, interaction: 42)

    inter = FakeInteraction(user=FakeUser(42))
    # FakeInteraction a déjà response/followup
    view = M.InviteView(bot=bot, duel_id=777)

    await view.accept(None, inter)  # type: ignore[arg-type]

    assert inter.response.deferred is True
    assert duel.accept_calls == [{"duel_id": 777, "user_id": 42}]

    assert inter.followup.sent
    last = inter.followup.sent[-1]
    assert last["content"] == "ERR:nope"
    assert last["ephemeral"] is True

@pytest.mark.asyncio
async def test_invite_view_accept_render_fails_fallback_message(monkeypatch):
    monkeypatch.setattr(M, "DuelError", FakeDuelError)
    monkeypatch.setattr(M, "duel_error_message", lambda e: f"ERR:{e}")

    duel = FakeDuelService()
    bot = FakeBot(duel)

    monkeypatch.setattr(M, "require_user_id", lambda *, interaction: 42)
    guild = SimpleNamespace()
    monkeypatch.setattr(M, "require_guild", lambda *, interaction: guild)

    async def fake_render(*, snapshot, guild, bot):
        raise RuntimeError("no renderer")

    monkeypatch.setattr(M, "render_duel_message", fake_render)

    inter = FakeInteraction(user=FakeUser(42))
    inter.message = _make_message(content="invite content")

    view = M.InviteView(bot=bot, duel_id=777)
    await view.accept(None, inter)  # type: ignore[arg-type]

    assert inter.followup.sent
    last = inter.followup.sent[-1]
    assert "Le duel a été accepté" in (last["content"] or "")
    assert last["ephemeral"] is True

    # message pas édité car render fail
    assert inter.message.edits == []

@pytest.mark.asyncio
async def test_invite_view_accept_success_edits_invite_message(monkeypatch):
    monkeypatch.setattr(M, "DuelError", FakeDuelError)
    monkeypatch.setattr(M, "duel_error_message", lambda e: f"ERR:{e}")

    duel = FakeDuelService()
    bot = FakeBot(duel)

    monkeypatch.setattr(M, "require_user_id", lambda *, interaction: 42)
    guild = SimpleNamespace()
    monkeypatch.setattr(M, "require_guild", lambda *, interaction: guild)

    async def fake_render(*, snapshot, guild, bot):
        return ("EMBED", [], "VIEW")

    monkeypatch.setattr(M, "render_duel_message", fake_render)

    inter = FakeInteraction(user=FakeUser(42))
    inter.message = _make_message(content="hello")

    view = M.InviteView(bot=bot, duel_id=777)
    await view.accept(None, inter)  # type: ignore[arg-type]

    assert inter.response.deferred is True
    assert duel.accept_calls == [{"duel_id": 777, "user_id": 42}]

    assert inter.message.edits == [{"content": "hello", "embed": "EMBED", "view": "VIEW", "files": None}]

# ------------------------------------------------------------
# InviteView.refuse
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_invite_view_refuse_duel_error_sends_ephemeral(monkeypatch):
    monkeypatch.setattr(M, "DuelError", FakeDuelError)
    monkeypatch.setattr(M, "duel_error_message", lambda e: f"ERR:{e}")

    duel = FakeDuelService()
    duel.raise_on_refuse = FakeDuelError("nope")
    bot = FakeBot(duel)

    monkeypatch.setattr(M, "require_user_id", lambda *, interaction: 42)

    inter = FakeInteraction(user=FakeUser(42))
    view = M.InviteView(bot=bot, duel_id=777)

    await view.refuse(None, inter)  # type: ignore[arg-type]

    assert inter.response.deferred is True
    assert duel.refuse_calls == [{"duel_id": 777, "user_id": 42}]

    assert inter.followup.sent
    last = inter.followup.sent[-1]
    assert last["content"] == "ERR:nope"
    assert last["ephemeral"] is True

@pytest.mark.asyncio
async def test_invite_view_refuse_member_lookup_value_error(monkeypatch):
    monkeypatch.setattr(M, "DuelError", FakeDuelError)
    monkeypatch.setattr(M, "duel_error_message", lambda e: f"ERR:{e}")

    duel = FakeDuelService()
    bot = FakeBot(duel)

    monkeypatch.setattr(M, "require_user_id", lambda *, interaction: 42)
    guild = SimpleNamespace()
    monkeypatch.setattr(M, "require_guild", lambda *, interaction: guild)

    async def fake_get_member(guild, uid):
        raise ValueError("missing")

    monkeypatch.setattr(M, "get_member_by_id_or_raise", fake_get_member)

    # ne doit pas continuer
    monkeypatch.setattr(
        M,
        "build_refuse_duels_embed",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not call")),
    )

    inter = FakeInteraction(user=FakeUser(42))
    view = M.InviteView(bot=bot, duel_id=777)

    await view.refuse(None, inter)  # type: ignore[arg-type]

    assert inter.original_edits
    assert inter.original_edits[-1]["content"] == "Un des participants n'a pas pu être trouvé."
    assert inter.original_edits[-1]["view"] is None

@pytest.mark.asyncio
async def test_invite_view_refuse_success_fetches_message_and_edits(monkeypatch):
    monkeypatch.setattr(M, "DuelError", FakeDuelError)
    monkeypatch.setattr(M, "duel_error_message", lambda e: f"ERR:{e}")

    duel = FakeDuelService()
    duel.snapshot_refuse = {
        "duel": {"player_b": 2, "message_id": 444, "channel_id": 555}
    }
    bot = FakeBot(duel)

    monkeypatch.setattr(M, "require_user_id", lambda *, interaction: 42)
    guild = SimpleNamespace()
    monkeypatch.setattr(M, "require_guild", lambda *, interaction: guild)

    # member lookup ok
    b = FakeMember(2, display_name="Bob")

    async def fake_get_member(guild, uid):
        assert uid == 2
        return b

    monkeypatch.setattr(M, "get_member_by_id_or_raise", fake_get_member)

    # refuse embed
    async def fake_build_refuse(*, player_b):
        assert player_b is b
        return ("REFUSE_EMBED", [])

    monkeypatch.setattr(M, "build_refuse_duels_embed", fake_build_refuse)

    # channel fetch
    channel = FakeFetchMessageChannel(message=FakeMessage(content="invite", message_id=1234))

    async def fake_get_channel(*, bot, channel_id):
        assert channel_id == 555
        return channel

    monkeypatch.setattr(M, "get_text_or_thread_channel", fake_get_channel)

    inter = FakeInteraction(user=FakeUser(42))
    view = M.InviteView(bot=bot, duel_id=777)

    await view.refuse(None, inter)  # type: ignore[arg-type]

    assert duel.refuse_calls == [{"duel_id": 777, "user_id": 42}]
    assert channel.fetched == [444]

    # message édité
    assert channel.message.edits == [{"content": "", "embed": "REFUSE_EMBED", "view": None, "files": None}]