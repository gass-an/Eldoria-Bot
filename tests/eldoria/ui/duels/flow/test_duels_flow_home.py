from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.duels.flow import home as M
from tests._fakes._duels_ui_fakes import FakeBot, FakeDuelError
from tests._fakes._pages_fakes import FakeInteraction, FakeUser


# ------------------------------------------------------------
# CompatInteraction (edit_original_response(content=...))
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# Fakes Duel/Bot
# ------------------------------------------------------------
class FakeDuelService:
    def __init__(self):
        self.configure_calls: list[dict] = []
        self.raise_on_configure: Exception | None = None
        self.snapshot = {"duel": {"expires_at": 123}}

    def configure_game_type(self, duel_id: int, gk: str):
        self.configure_calls.append({"duel_id": duel_id, "gk": gk})
        if self.raise_on_configure is not None:
            raise self.raise_on_configure
        return self.snapshot

# ------------------------------------------------------------
# build_home_duels_embed
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_build_home_duels_embed_builds_embed_fields_footer_and_files(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 111)

    # Données JSON
    duel_data = {
        "title": "Duel",
        "description": "Choisis ton jeu",
        "games": {
            "rps": {"name": "RPS", "description": "Pierre feuille ciseaux"},
            "coin": {"name": "Coin", "description": "Pile ou face"},
        },
    }
    monkeypatch.setattr(M, "get_duel_embed_data", lambda: duel_data)

    decorated = {"called": False}

    def fake_decorate(embed, thumb_url, banner_url):
        decorated["called"] = True
        return embed

    monkeypatch.setattr(M, "decorate", fake_decorate)
    monkeypatch.setattr(M, "common_files", lambda t, b: ["F1", "F2"])

    embed, files = await M.build_home_duels_embed(expires_at=999)

    assert isinstance(embed, discord.Embed)
    assert embed.title == "Duel"
    assert "La configuration expire <t:999:R>" in embed.description
    assert "> Choisis ton jeu" in embed.description
    assert embed.colour == 111

    # 2 fields
    assert len(embed.fields) == 2
    assert embed.fields[0]["name"] == "RPS"
    assert "> Pierre feuille ciseaux" in embed.fields[0]["value"]
    assert embed.fields[0]["inline"] is False

    assert embed.fields[1]["name"] == "Coin"
    assert "> Pile ou face" in embed.fields[1]["value"]
    assert embed.fields[1]["inline"] is False

    assert embed.footer == {"text": "Choisi le jeu ci-dessous."}
    assert decorated["called"] is True
    assert files == ["F1", "F2"]

# ------------------------------------------------------------
# HomeView init (boutons + label tronqué)
# ------------------------------------------------------------
def test_home_view_creates_buttons_from_games_and_truncates_label(monkeypatch):
    # game name > 80 chars => doit être tronqué
    long_name = "X" * 200

    duel_data = {
        "games": {
            "rps": {"name": "RPS"},
            "long": {"name": long_name},
            "no_name": {"description": "no name"},  # fallback label = game_key
        }
    }
    monkeypatch.setattr(M, "get_duel_embed_data", lambda: duel_data)

    duel = FakeDuelService()
    bot = FakeBot(duel)

    view = M.HomeView(bot=bot, duel_id=777)

    assert len(view.children) == 3
    labels = [b.label for b in view.children]

    assert labels[0] == "RPS"
    assert labels[1] == ("X" * 80)  # tronqué à 80
    assert labels[2] == "no_name"  # fallback sur game_key

# ------------------------------------------------------------
# HomeView click success
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_home_view_click_success_builds_stake_embed_and_edits_original(monkeypatch):
    monkeypatch.setattr(M, "DuelError", FakeDuelError)
    monkeypatch.setattr(M, "duel_error_message", lambda e: f"ERR:{e}")

    duel_data = {
        "games": {
            "rps": {"name": "RPS"},
            "coin": {"name": "Coin"},
        }
    }
    monkeypatch.setattr(M, "get_duel_embed_data", lambda: duel_data)

    duel = FakeDuelService()
    duel.snapshot = {"duel": {"expires_at": 555}}
    bot = FakeBot(duel)

    # build_config_stake_duels_embed async
    async def fake_build_config(expires_at: int):
        assert expires_at == 555
        return ("STAKE_EMBED", ["STAKE_FILES"])

    monkeypatch.setattr(M, "build_config_stake_duels_embed", fake_build_config)

    # StakeXpView instanciée dans edit_original_response
    monkeypatch.setattr(M, "StakeXpView", lambda *, duel_id, bot: ("STAKE_VIEW", duel_id, bot))

    inter = CompatInteraction(user=FakeUser(42))

    view = M.HomeView(bot=bot, duel_id=777)

    # bouton 0 => game_key "rps"
    btn0 = view.children[0]
    await btn0.callback(inter)  # type: ignore[misc]

    assert inter.response.deferred is True
    assert duel.configure_calls == [{"duel_id": 777, "gk": "rps"}]

    assert inter.original_edits
    last = inter.original_edits[-1]
    assert last["embed"] == "STAKE_EMBED"
    assert last["files"] == ["STAKE_FILES"]
    assert last["view"] == ("STAKE_VIEW", 777, bot)

# ------------------------------------------------------------
# HomeView click DuelError
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_home_view_click_duel_error_shows_error_message(monkeypatch):
    monkeypatch.setattr(M, "DuelError", FakeDuelError)
    monkeypatch.setattr(M, "duel_error_message", lambda e: f"ERR:{e}")

    duel_data = {"games": {"rps": {"name": "RPS"}}}
    monkeypatch.setattr(M, "get_duel_embed_data", lambda: duel_data)

    duel = FakeDuelService()
    duel.raise_on_configure = FakeDuelError("nope")
    bot = FakeBot(duel)

    # ne doit pas aller plus loin
    monkeypatch.setattr(
        M,
        "build_config_stake_duels_embed",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not call")),
    )

    inter = CompatInteraction(user=FakeUser(42))
    view = M.HomeView(bot=bot, duel_id=777)
    btn = view.children[0]

    await btn.callback(inter)  # type: ignore[misc]

    assert inter.response.deferred is True
    assert duel.configure_calls == [{"duel_id": 777, "gk": "rps"}]

    assert inter.original_edits
    last = inter.original_edits[-1]
    assert last["content"] == "ERR:nope"
    assert last["view"] is None