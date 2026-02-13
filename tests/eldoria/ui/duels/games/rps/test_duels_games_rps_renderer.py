from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.duels.games.rps import renderer as M


class FakeMember:
    def __init__(self, mid: int, name: str):
        self.id = mid
        self.display_name = name
        self.mention = f"<@{mid}>"


class FakeGuild:
    pass


@pytest.fixture
def members():
    a = FakeMember(1, "Alice")
    b = FakeMember(2, "Bob")
    return a, b


def test_move_label_none_is_question_mark():
    assert M._move_label(None) == "?"


def test_move_label_known_move_uses_emoji(monkeypatch):
    # on force un mapping simple
    monkeypatch.setattr(M, "MOVE_EMOJI", {"ROCK": "🪨 Pierre"})
    assert M._move_label("ROCK") == "🪨 Pierre"


def test_move_label_unknown_move_returns_unknown_icon(monkeypatch):
    monkeypatch.setattr(M, "MOVE_EMOJI", {})
    assert M._move_label("???") == "❔"


def test_result_label_draw(monkeypatch, members):
    a, b = members
    monkeypatch.setattr(M.constants, "DUEL_RESULT_DRAW", "DRAW")
    assert M._result_label("DRAW", a, b) == "🤝 Égalité"


def test_result_label_win_a(monkeypatch, members):
    a, b = members
    monkeypatch.setattr(M.constants, "DUEL_RESULT_WIN_A", "WIN_A")
    monkeypatch.setattr(M.constants, "DUEL_RESULT_DRAW", "DRAW")
    monkeypatch.setattr(M.constants, "DUEL_RESULT_WIN_B", "WIN_B")
    assert M._result_label("WIN_A", a, b) == "🏆 Victoire de **Alice**"


def test_result_label_win_b(monkeypatch, members):
    a, b = members
    monkeypatch.setattr(M.constants, "DUEL_RESULT_WIN_B", "WIN_B")
    monkeypatch.setattr(M.constants, "DUEL_RESULT_DRAW", "DRAW")
    monkeypatch.setattr(M.constants, "DUEL_RESULT_WIN_A", "WIN_A")
    assert M._result_label("WIN_B", a, b) == "🏆 Victoire de **Bob**"


def test_result_label_unknown(monkeypatch, members):
    a, b = members
    monkeypatch.setattr(M.constants, "DUEL_RESULT_DRAW", "DRAW")
    monkeypatch.setattr(M.constants, "DUEL_RESULT_WIN_A", "WIN_A")
    monkeypatch.setattr(M.constants, "DUEL_RESULT_WIN_B", "WIN_B")
    assert M._result_label("WTF", a, b) == "Résultat: WTF"


@pytest.mark.asyncio
async def test_render_rps_waiting_state_builds_base_embed_and_view(monkeypatch, members):
    a, b = members
    guild = FakeGuild()

    # constants + rps constants
    monkeypatch.setattr(M.rps, "RPS_DICT_STATE", "state")
    monkeypatch.setattr(M.rps, "RPS_STATE_WAITING", "WAITING")
    monkeypatch.setattr(M.rps, "RPS_STATE_FINISHED", "FINISHED")

    # member lookup
    async def fake_get_member(g, uid):
        return a if uid == 1 else b

    monkeypatch.setattr(M, "get_member_by_id_or_raise", fake_get_member)

    # base embed
    async def fake_base_embed(*, player_a, player_b, stake_xp, expires_at, game_type):
        embed = discord.Embed(title="BASE")
        files = ["FILES"]
        return embed, files

    monkeypatch.setattr(M, "build_game_base_embed", fake_base_embed)

    # view instance
    monkeypatch.setattr(M, "RpsView", lambda *, bot, duel_id: ("RPS_VIEW", bot, duel_id))

    snapshot = {
        "duel": {"id": 99, "player_a": 1, "player_b": 2, "stake_xp": 10, "expires_at": 123, "game_type": "rps"},
        "game": {"state": "WAITING", "a_played": True, "b_played": False},
    }

    embed, files, view = await M.render_rps(snapshot, guild, bot="BOT")

    assert isinstance(embed, discord.Embed)
    assert embed.title == "BASE"
    assert files == ["FILES"]
    assert view == ("RPS_VIEW", "BOT", 99)

    # field état + footer
    assert len(embed.fields) == 1
    assert embed.fields[0]["name"] == "État"
    assert "Alice a joué: ✅" in embed.fields[0]["value"]
    assert "Bob a joué: ⌛" in embed.fields[0]["value"]
    assert embed.footer == {"text": "Choisis ton coup avec les boutons ci-dessous (caché jusqu'à la fin)."}


@pytest.mark.asyncio
async def test_render_rps_none_state_treated_like_waiting(monkeypatch, members):
    a, b = members
    guild = FakeGuild()

    monkeypatch.setattr(M.rps, "RPS_DICT_STATE", "state")
    monkeypatch.setattr(M.rps, "RPS_STATE_WAITING", "WAITING")
    monkeypatch.setattr(M.rps, "RPS_STATE_FINISHED", "FINISHED")

    async def fake_get_member(g, uid):
        return a if uid == 1 else b

    monkeypatch.setattr(M, "get_member_by_id_or_raise", fake_get_member)

    async def fake_base_embed(**kwargs):
        return (discord.Embed(title="BASE"), ["FILES"])

    monkeypatch.setattr(M, "build_game_base_embed", fake_base_embed)
    monkeypatch.setattr(M, "RpsView", lambda *, bot, duel_id: ("RPS_VIEW", duel_id))

    snapshot = {
        "duel": {"id": 99, "player_a": 1, "player_b": 2, "stake_xp": 10, "expires_at": 123, "game_type": "rps"},
        "game": {},  # state missing => None
    }

    embed, files, view = await M.render_rps(snapshot, guild, bot="BOT")
    assert embed.title == "BASE"
    assert view == ("RPS_VIEW", 99)


@pytest.mark.asyncio
async def test_render_rps_finished_state_builds_result_embed_and_no_view(monkeypatch, members):
    a, b = members
    guild = FakeGuild()

    monkeypatch.setattr(M.rps, "RPS_DICT_STATE", "state")
    monkeypatch.setattr(M.rps, "RPS_STATE_WAITING", "WAITING")
    monkeypatch.setattr(M.rps, "RPS_STATE_FINISHED", "FINISHED")
    monkeypatch.setattr(M.rps, "RPS_DICT_RESULT", "result")
    monkeypatch.setattr(M.rps, "RPS_PAYLOAD_A_MOVE", "a_move")
    monkeypatch.setattr(M.rps, "RPS_PAYLOAD_B_MOVE", "b_move")
    monkeypatch.setattr(M.rps, "RPS_MOVE_ROCK", "ROCK")
    monkeypatch.setattr(M.rps, "RPS_MOVE_PAPER", "PAPER")
    monkeypatch.setattr(M.rps, "RPS_MOVE_SCISSORS", "SCISSORS")

    monkeypatch.setattr(M.constants, "DUEL_RESULT_DRAW", "DRAW")
    monkeypatch.setattr(M.constants, "DUEL_RESULT_WIN_A", "WIN_A")
    monkeypatch.setattr(M.constants, "DUEL_RESULT_WIN_B", "WIN_B")

    async def fake_get_member(g, uid):
        return a if uid == 1 else b

    monkeypatch.setattr(M, "get_member_by_id_or_raise", fake_get_member)

    async def fake_result_base(*, player_a, player_b, stake_xp, game_type):
        embed = discord.Embed(title="RES")
        return embed, ["FILES"]

    monkeypatch.setattr(M, "build_game_result_base_embed", fake_result_base)

    # stable move emojis
    monkeypatch.setattr(M, "MOVE_EMOJI", {"ROCK": "🪨 Pierre", "PAPER": "📄 Papier", "SCISSORS": "✂️ Ciseaux"})

    snapshot = {
        "duel": {"id": 99, "player_a": 1, "player_b": 2, "stake_xp": 10, "expires_at": 123, "game_type": "rps"},
        "game": {"state": "FINISHED", "result": "WIN_A", "a_move": "ROCK", "b_move": "PAPER"},
        "xp": {1: 11, 2: 22},
    }

    embed, files, view = await M.render_rps(snapshot, guild, bot="BOT")

    assert embed.title == "RES"
    assert files == ["FILES"]
    assert view is None

    # Résultat + Coups + empty spacer + XP => 4 fields
    assert len(embed.fields) == 4
    assert embed.fields[0]["name"] == "Résultat"
    assert "🏆 Victoire de **Alice**" in embed.fields[0]["value"]

    assert embed.fields[1]["name"] == "Coups joués"
    assert "Alice : 🪨 Pierre" in embed.fields[1]["value"]
    assert "Bob : 📄 Papier" in embed.fields[1]["value"]
    assert embed.footer == {"text": "Duel terminé."}

    assert embed.fields[2] == {"name": "", "value": "", "inline": True}

    assert embed.fields[3]["name"] == "XP après duel"
    assert "Alice: **11**" in embed.fields[3]["value"]
    assert "Bob: **22**" in embed.fields[3]["value"]


@pytest.mark.asyncio
async def test_render_rps_finished_state_without_xp_dict_skips_xp_field(monkeypatch, members):
    a, b = members
    guild = FakeGuild()

    monkeypatch.setattr(M.rps, "RPS_DICT_STATE", "state")
    monkeypatch.setattr(M.rps, "RPS_STATE_WAITING", "WAITING")
    monkeypatch.setattr(M.rps, "RPS_STATE_FINISHED", "FINISHED")
    monkeypatch.setattr(M.rps, "RPS_DICT_RESULT", "result")

    monkeypatch.setattr(M.constants, "DUEL_RESULT_DRAW", "DRAW")
    monkeypatch.setattr(M.constants, "DUEL_RESULT_WIN_A", "WIN_A")
    monkeypatch.setattr(M.constants, "DUEL_RESULT_WIN_B", "WIN_B")

    async def fake_get_member(g, uid):
        return a if uid == 1 else b

    monkeypatch.setattr(M, "get_member_by_id_or_raise", fake_get_member)

    async def fake_result_base(**kwargs):
        return (discord.Embed(title="RES"), ["FILES"])

    monkeypatch.setattr(M, "build_game_result_base_embed", fake_result_base)

    snapshot = {
        "duel": {"id": 99, "player_a": 1, "player_b": 2, "stake_xp": 10, "expires_at": 123, "game_type": "rps"},
        "game": {"state": "FINISHED", "result": "DRAW"},
        "xp": "not_a_dict",
    }

    embed, _, _ = await M.render_rps(snapshot, guild, bot="BOT")

    # Résultat + Coups + spacer (pas XP) => 3 fields
    assert len(embed.fields) == 3
    assert embed.fields[0]["name"] == "Résultat"


@pytest.mark.asyncio
async def test_render_rps_unknown_state_fallback_adds_field_and_returns_view(monkeypatch, members):
    a, b = members
    guild = FakeGuild()

    monkeypatch.setattr(M.rps, "RPS_DICT_STATE", "state")
    monkeypatch.setattr(M.rps, "RPS_STATE_WAITING", "WAITING")
    monkeypatch.setattr(M.rps, "RPS_STATE_FINISHED", "FINISHED")

    async def fake_get_member(g, uid):
        return a if uid == 1 else b

    monkeypatch.setattr(M, "get_member_by_id_or_raise", fake_get_member)

    # base embed utilisé au début du render, donc doit exister même si état inconnu
    async def fake_base_embed(**kwargs):
        return (discord.Embed(title="BASE"), ["FILES"])

    monkeypatch.setattr(M, "build_game_base_embed", fake_base_embed)
    monkeypatch.setattr(M, "RpsView", lambda *, bot, duel_id: ("RPS_VIEW", duel_id))

    snapshot = {
        "duel": {"id": 99, "player_a": 1, "player_b": 2, "stake_xp": 10, "expires_at": 123, "game_type": "rps"},
        "game": {"state": "WAT"},
    }

    embed, files, view = await M.render_rps(snapshot, guild, bot="BOT")

    assert embed.title == "BASE"
    assert files == ["FILES"]
    assert view == ("RPS_VIEW", 99)

    assert embed.fields  # au moins 1
    assert embed.fields[-1]["name"] == "État"
    assert "État inconnu:" in embed.fields[-1]["value"]
