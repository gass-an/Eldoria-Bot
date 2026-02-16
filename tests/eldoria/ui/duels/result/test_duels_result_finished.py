from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.duels.result import finished as M
from tests._fakes.discord_entities import FakeDisplayMember as FakeMember



@pytest.mark.asyncio
async def test_build_game_result_base_embed_builds_embed_and_files(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_VALIDATION", 1234)

    called = {"game_type": None}
    def fake_get_game_text(gt):
        called["game_type"] = gt
        return ("RPS", "desc")

    monkeypatch.setattr(M, "get_game_text", fake_get_game_text)

    decorated = {"called": False}
    def fake_decorate(embed, thumb_url):
        decorated["called"] = True
        return embed

    monkeypatch.setattr(M, "decorate_thumb_only", fake_decorate)
    monkeypatch.setattr(M, "common_thumb", lambda thumb_url: ["FILE"])

    a = FakeMember("Alice")
    b = FakeMember("Bob")

    embed, files = await M.build_game_result_base_embed(
        player_a=a,
        player_b=b,
        stake_xp=50,
        game_type="rps",
    )

    assert isinstance(embed, discord.Embed)
    assert embed.title == "RPS"
    assert "**Alice** vs **Bob**" in embed.description
    assert "Mise : **50 XP**" in embed.description
    assert embed.colour == 1234

    assert called["game_type"] == "rps"
    assert decorated["called"] is True
    assert files == ["FILE"]


@pytest.mark.asyncio
async def test_build_game_result_base_embed_stake_zero(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_VALIDATION", 1)
    monkeypatch.setattr(M, "get_game_text", lambda gt: ("Coin", "desc"))
    monkeypatch.setattr(M, "decorate_thumb_only", lambda embed, thumb_url: embed)
    monkeypatch.setattr(M, "common_thumb", lambda thumb_url: [])

    a = FakeMember("A")
    b = FakeMember("B")

    embed, files = await M.build_game_result_base_embed(
        player_a=a,
        player_b=b,
        stake_xp=0,
        game_type="coin",
    )

    assert embed.title == "Coin"
    assert "Mise : **0 XP**" in embed.description
    assert files == []


@pytest.mark.asyncio
async def test_build_game_result_base_embed_calls_get_game_text(monkeypatch):
    called = {}

    def fake_get_game_text(gt):
        called["gt"] = gt
        return ("NAME", "DESC")

    monkeypatch.setattr(M, "get_game_text", fake_get_game_text)
    monkeypatch.setattr(M, "EMBED_COLOUR_VALIDATION", 1)
    monkeypatch.setattr(M, "decorate_thumb_only", lambda embed, thumb_url: embed)
    monkeypatch.setattr(M, "common_thumb", lambda thumb_url: [])

    a = FakeMember("A")
    b = FakeMember("B")

    await M.build_game_result_base_embed(
        player_a=a,
        player_b=b,
        stake_xp=10,
        game_type="my_game",
    )

    assert called["gt"] == "my_game"