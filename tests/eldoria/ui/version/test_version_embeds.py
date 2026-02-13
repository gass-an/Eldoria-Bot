from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.version import embeds as M


@pytest.mark.asyncio
async def test_build_version_embed_builds_embed_and_files(monkeypatch):
    # Arrange
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1234)
    monkeypatch.setattr(M, "VERSION", "9.9.9")  # stable

    decorated = {"called": False, "args": None}

    def fake_decorate(embed, thumb_url, banner_url):
        decorated["called"] = True
        decorated["args"] = (embed, thumb_url, banner_url)
        return embed

    monkeypatch.setattr(M, "decorate", fake_decorate)
    monkeypatch.setattr(M, "common_files", lambda t, b: ["F1", "F2"])

    # Act
    embed, files = await M.build_version_embed()

    # Assert
    assert isinstance(embed, discord.Embed)
    assert embed.title == "Eldoria"
    assert embed.description == "La version actuelle de votre bot préféré"
    assert embed.colour == 1234

    assert len(embed.fields) == 2

    assert embed.fields[0] == {
        "name": "Version",
        "value": "v9.9.9",
        "inline": True,
    }
    assert embed.fields[1] == {
        "name": "Statut",
        "value": "Développement stable",
        "inline": True,
    }

    assert embed.footer == {"text": "Développé par Faucon98"}

    assert decorated["called"] is True
    assert decorated["args"][0] is embed
    assert decorated["args"][1] is None
    assert decorated["args"][2] is None

    assert files == ["F1", "F2"]
