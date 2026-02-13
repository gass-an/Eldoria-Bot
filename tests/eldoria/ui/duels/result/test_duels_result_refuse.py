from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.duels.result import refuse as M


class FakeMember:
    def __init__(self, name: str):
        self.display_name = name


@pytest.mark.asyncio
async def test_build_refuse_duels_embed_builds_embed_and_files(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_ERROR", 999)

    decorated = {"called": False}

    def fake_decorate(embed, thumb_url):
        decorated["called"] = True
        return embed

    monkeypatch.setattr(M, "decorate_thumb_only", fake_decorate)
    monkeypatch.setattr(M, "common_thumb", lambda thumb_url: ["FILE"])

    member = FakeMember("Bob")

    embed, files = await M.build_refuse_duels_embed(player_b=member)

    assert isinstance(embed, discord.Embed)

    assert embed.title == "Invitation à un duel"
    assert "L'invitation à été refusée par Bob." in embed.description
    assert "L'XP n'a pas été modifié." in embed.description

    assert embed.colour == 999
    assert embed.footer == {"text": "Peut-être une prochaine fois."}

    # aucun field ajouté
    assert embed.fields == []

    assert decorated["called"] is True
    assert files == ["FILE"]


@pytest.mark.asyncio
async def test_build_refuse_duels_embed_with_empty_display_name(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_ERROR", 1)
    monkeypatch.setattr(M, "decorate_thumb_only", lambda embed, thumb_url: embed)
    monkeypatch.setattr(M, "common_thumb", lambda thumb_url: [])

    member = FakeMember("")

    embed, files = await M.build_refuse_duels_embed(player_b=member)

    # description fonctionne même si display_name vide
    assert "L'invitation à été refusée par ." in embed.description
    assert files == []
