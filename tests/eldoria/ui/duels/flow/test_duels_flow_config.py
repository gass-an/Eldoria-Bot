from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.duels.flow import config as M
from tests._fakes._duels_ui_fakes import FakeBot, FakeDuelError
from tests._fakes._pages_fakes import FakeInteraction, FakeUser


# -----------------------------
# Compat: FakeInteraction qui accepte edit_original_response(content=...)
# -----------------------------
class CompatInteraction(FakeInteraction):
    async def edit_original_response(
        self,
        *,
        content=None,
        embeds=None,
        attachments=None,
        view=None,
        embed=None,
        files=None,
    ):
        # On capture tout ce que le code UI peut envoyer.
        self.original_edits.append(
            {
                "content": content,
                "embeds": embeds,
                "attachments": attachments,
                "view": view,
                "embed": embed,
                "files": files,
            }
        )

# -----------------------------
# Fakes "discord-like" helpers
# -----------------------------
class FakeMember:
    def __init__(self, member_id: int, name: str):
        self.id = member_id
        self.display_name = name
        self.mention = f"<@{member_id}>"

class FakeMessage:
    def __init__(self, message_id: int = 999, content: str = ""):
        self.id = message_id
        self.content = content
        self.edits: list[dict] = []

    async def edit(self, *, content: str, embed=None, files=None, view=None):
        self.edits.append({"content": content, "embed": embed, "files": files, "view": view})

class FakeChannel:
    def __init__(self):
        self.sent: list[dict] = []
        self._next_message_id = 1000

    async def send(self, *, content: str):
        msg = FakeMessage(message_id=self._next_message_id, content=content)
        self._next_message_id += 1
        self.sent.append({"content": content, "message": msg})
        return msg

class FakeGuild:
    pass

# -----------------------------
# Fake Duel service + Bot
# -----------------------------
class FakeDuelService:
    def __init__(self, *, allowed_stakes: set[int]):
        self._allowed = allowed_stakes
        self.configure_calls: list[dict] = []
        self.send_invite_calls: list[dict] = []

        self.raise_on_configure: Exception | None = None
        self.raise_on_send_invite: Exception | None = None

        self.snapshot_configure: dict = {"duel": {"channel_id": 123, "player_a": 1, "player_b": 2}}
        self.snapshot_invite: dict = {
            "xp": {"1": 10},
            "duel": {"stake_xp": 10, "expires_at": 111, "game_type": "rps"},
        }

    def get_allowed_stakes(self, duel_id: int):
        return self._allowed

    def configure_stake_xp(self, duel_id: int, *, stake_xp: int):
        self.configure_calls.append({"duel_id": duel_id, "stake_xp": stake_xp})
        if self.raise_on_configure is not None:
            raise self.raise_on_configure
        return self.snapshot_configure

    def send_invite(self, *, duel_id: int, message_id: int):
        self.send_invite_calls.append({"duel_id": duel_id, "message_id": message_id})
        if self.raise_on_send_invite is not None:
            raise self.raise_on_send_invite
        return self.snapshot_invite

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

    duel = FakeDuelService(allowed_stakes={10, 30})
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

    duel = FakeDuelService(allowed_stakes={10})
    bot = FakeBot(duel)

    channel = FakeChannel()

    async def fake_get_channel(*, bot, channel_id):
        return channel

    monkeypatch.setattr(M, "get_text_or_thread_channel", fake_get_channel)

    guild = FakeGuild()
    monkeypatch.setattr(M, "require_guild", lambda *, interaction: guild)

    player_a = FakeMember(1, "Alice")
    player_b = FakeMember(2, "Bob")

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

    inter = CompatInteraction(user=FakeUser(42))
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
    msg: FakeMessage = sent["message"]

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

    duel = FakeDuelService(allowed_stakes={10})
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

    inter = CompatInteraction(user=FakeUser(42))

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

    duel = FakeDuelService(allowed_stakes={10})
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

    inter = CompatInteraction(user=FakeUser(42))

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

    duel = FakeDuelService(allowed_stakes={10})
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

    inter = CompatInteraction(user=FakeUser(42))

    view = M.StakeXpView(bot=bot, duel_id=777)
    button = view.children[0]

    await button.callback(inter)  # type: ignore[misc]

    assert len(channel.sent) == 1
    msg: FakeMessage = channel.sent[0]["message"]
    assert msg.edits == []

    assert inter.original_edits
    assert inter.original_edits[-1]["content"] == "Un des participants n'a pas pu être trouvé."