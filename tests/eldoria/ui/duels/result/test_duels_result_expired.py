from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.duels.result import expired as M


class FakeMember:
    def __init__(self, name: str):
        self.display_name = name


@pytest.mark.asyncio
async def test_build_expired_duels_embed_with_game_type_and_invited_reason_and_no_stake(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_ERROR", 999)
    monkeypatch.setattr(M, "get_game_text", lambda gt: ("RPS", "desc"))

    decorated = {"called": False}

    def fake_decorate(embed, thumb_url):
        decorated["called"] = True
        return embed

    monkeypatch.setattr(M, "decorate_thumb_only", fake_decorate)
    monkeypatch.setattr(M, "common_thumb", lambda thumb_url: ["FILE"])

    a = FakeMember("Alice")
    b = FakeMember("Bob")

    embed, files = await M.build_expired_duels_embed(
        player_a=a,
        player_b=b,
        previous_status="invited",  # lower -> upper
        stake_xp=0,
        game_type="rps",
    )

    assert isinstance(embed, discord.Embed)
    assert embed.title == "⏰ Duel expiré — RPS"
    assert "**Alice** vs **Bob**" in embed.description
    assert "L'invitation n'a pas été acceptée à temps." in embed.description
    assert embed.colour == 999

    # stake=0 => pas de fields
    assert embed.fields == []

    assert embed.footer == {"text": "Le duel est terminé."}
    assert decorated["called"] is True
    assert files == ["FILE"]


@pytest.mark.asyncio
async def test_build_expired_duels_embed_without_game_type_defaults_title_and_config_reason(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_ERROR", 1)
    monkeypatch.setattr(M, "decorate_thumb_only", lambda embed, thumb_url: embed)
    monkeypatch.setattr(M, "common_thumb", lambda thumb_url: [])

    a = FakeMember("A")
    b = FakeMember("B")

    embed, files = await M.build_expired_duels_embed(
        player_a=a,
        player_b=b,
        previous_status="",  # => else branch
        stake_xp=0,
        game_type="",
    )

    assert embed.title == "⏰ Duel expiré"
    assert "Le duel n'a pas été configuré à temps." in embed.description
    assert embed.fields == []
    assert files == []


@pytest.mark.asyncio
async def test_build_expired_duels_embed_active_with_stake_adds_refund_yes(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_ERROR", 2)
    monkeypatch.setattr(M, "get_game_text", lambda gt: ("Coin", "desc"))
    monkeypatch.setattr(M, "decorate_thumb_only", lambda embed, thumb_url: embed)
    monkeypatch.setattr(M, "common_thumb", lambda thumb_url: ["F"])

    a = FakeMember("Alice")
    b = FakeMember("Bob")

    embed, files = await M.build_expired_duels_embed(
        player_a=a,
        player_b=b,
        previous_status="ACTIVE",
        stake_xp=50,
        game_type="coin",
    )

    assert embed.title == "⏰ Duel expiré — Coin"
    assert "Le duel n'a pas été terminé à temps." in embed.description

    # stake>0 => 2 fields
    assert len(embed.fields) == 2
    assert embed.fields[0] == {"name": "Mise", "value": "50 XP", "inline": True}
    assert embed.fields[1] == {"name": "Remboursement", "value": "✅ Mise remboursée", "inline": True}

    assert files == ["F"]


@pytest.mark.asyncio
async def test_build_expired_duels_embed_invited_with_stake_adds_refund_none_taken(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_ERROR", 2)
    monkeypatch.setattr(M, "get_game_text", lambda gt: ("Coin", "desc"))
    monkeypatch.setattr(M, "decorate_thumb_only", lambda embed, thumb_url: embed)
    monkeypatch.setattr(M, "common_thumb", lambda thumb_url: ["F"])

    a = FakeMember("Alice")
    b = FakeMember("Bob")

    embed, _ = await M.build_expired_duels_embed(
        player_a=a,
        player_b=b,
        previous_status="INVITED",
        stake_xp=20,
        game_type="coin",
    )

    assert len(embed.fields) == 2
    assert embed.fields[0]["value"] == "20 XP"
    assert embed.fields[1] == {"name": "Remboursement", "value": "ℹ️ Aucune mise prélevée", "inline": True}


@pytest.mark.asyncio
async def test_build_expired_duels_embed_stake_xp_none_treated_as_zero(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_ERROR", 3)
    monkeypatch.setattr(M, "decorate_thumb_only", lambda embed, thumb_url: embed)
    monkeypatch.setattr(M, "common_thumb", lambda thumb_url: [])

    a = FakeMember("Alice")
    b = FakeMember("Bob")

    embed, _ = await M.build_expired_duels_embed(
        player_a=a,
        player_b=b,
        previous_status=None,  # type: ignore[arg-type]
        stake_xp=None,         # type: ignore[arg-type]
        game_type="",
    )

    assert embed.title == "⏰ Duel expiré"
    assert embed.fields == []
    assert "Le duel n'a pas été configuré à temps." in embed.description
