from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.duels import common as M


class FakeMember:
    def __init__(self, name: str):
        self.display_name = name


@pytest.mark.asyncio
async def test_build_game_base_embed_with_expiration(monkeypatch):
    # --- Arrange
    monkeypatch.setattr(M, "get_game_text", lambda gt: ("RPS", "Pierre Feuille Ciseaux"))
    monkeypatch.setattr(M, "EMBED_COLOUR_VALIDATION", 12345)

    decorated = {"called": False}
    def fake_decorate(embed, thumb_url):
        decorated["called"] = True
        return embed

    monkeypatch.setattr(M, "decorate_thumb_only", fake_decorate)
    monkeypatch.setattr(M, "common_thumb", lambda thumb_url: ["FILE"])

    player_a = FakeMember("Alice")
    player_b = FakeMember("Bob")

    # --- Act
    embed, files = await M.build_game_base_embed(
        player_a=player_a,
        player_b=player_b,
        stake_xp=50,
        expires_at=1234567890,
        game_type="rps",
    )

    # --- Assert
    assert isinstance(embed, discord.Embed)
    assert files == ["FILE"]
    assert decorated["called"] is True

    assert embed.title == "RPS"
    assert "Ce duel expire <t:1234567890:R>" in embed.description
    assert "**Alice** vs **Bob**" in embed.description
    assert "Mise : **50 XP**" in embed.description
    assert "> Pierre Feuille Ciseaux" in embed.description
    assert embed.colour == 12345


@pytest.mark.asyncio
async def test_build_game_base_embed_without_expiration(monkeypatch):
    monkeypatch.setattr(M, "get_game_text", lambda gt: ("RPS", "Desc"))
    monkeypatch.setattr(M, "EMBED_COLOUR_VALIDATION", 999)

    monkeypatch.setattr(M, "decorate_thumb_only", lambda embed, thumb_url: embed)
    monkeypatch.setattr(M, "common_thumb", lambda thumb_url: [])

    player_a = FakeMember("A")
    player_b = FakeMember("B")

    embed, files = await M.build_game_base_embed(
        player_a=player_a,
        player_b=player_b,
        stake_xp=10,
        expires_at=0,
        game_type="rps",
    )

    assert "Ce duel expire" not in embed.description
    assert "**A** vs **B**" in embed.description
    assert files == []
    assert embed.colour == 999


@pytest.mark.asyncio
async def test_build_game_base_embed_calls_get_game_text_with_game_type(monkeypatch):
    called = {}

    def fake_get_game_text(gt):
        called["game_type"] = gt
        return ("NAME", "DESC")

    monkeypatch.setattr(M, "get_game_text", fake_get_game_text)
    monkeypatch.setattr(M, "EMBED_COLOUR_VALIDATION", 1)
    monkeypatch.setattr(M, "decorate_thumb_only", lambda embed, thumb_url: embed)
    monkeypatch.setattr(M, "common_thumb", lambda thumb_url: [])

    player_a = FakeMember("A")
    player_b = FakeMember("B")

    await M.build_game_base_embed(
        player_a=player_a,
        player_b=player_b,
        stake_xp=1,
        expires_at=0,
        game_type="my_game",
    )

    assert called["game_type"] == "my_game"


@pytest.mark.asyncio
async def test_build_game_base_embed_returns_files_from_common_thumb(monkeypatch):
    monkeypatch.setattr(M, "get_game_text", lambda gt: ("T", "D"))
    monkeypatch.setattr(M, "EMBED_COLOUR_VALIDATION", 1)
    monkeypatch.setattr(M, "decorate_thumb_only", lambda embed, thumb_url: embed)

    monkeypatch.setattr(M, "common_thumb", lambda thumb_url: ["F1", "F2"])

    player_a = FakeMember("A")
    player_b = FakeMember("B")

    _, files = await M.build_game_base_embed(
        player_a=player_a,
        player_b=player_b,
        stake_xp=5,
        expires_at=0,
        game_type="x",
    )

    assert files == ["F1", "F2"]
