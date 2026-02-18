from __future__ import annotations

import json

import pytest

import eldoria.features.duel._internal.gameplay as gameplay_mod
from eldoria.exceptions import duel as exc


def _duel_row(**overrides):
    base = {
        "id": 1,
        "guild_id": 10,
        "player_a_id": 111,
        "player_b_id": 222,
        "game_type": "RPS",
        "payload": None,
    }
    base.update(overrides)
    return base


# ------------------------------------------------------------
# play_game_action
# ------------------------------------------------------------

def test_play_game_action_raises_when_no_game_type(monkeypatch):
    duel = _duel_row(game_type=None)
    monkeypatch.setattr(gameplay_mod.helpers, "get_duel_or_raise", lambda duel_id: duel)

    with pytest.raises(exc.WrongGameType):
        gameplay_mod.play_game_action(1, 111, {"move": "rock"})


def test_play_game_action_returns_snapshot_when_not_finished(monkeypatch):
    duel = _duel_row(game_type="RPS")
    monkeypatch.setattr(gameplay_mod.helpers, "get_duel_or_raise", lambda duel_id: duel)

    class FakeGame:
        def play(self, duel_id, user_id, action):
            return {"game": {"state": "WAITING"}}

    monkeypatch.setattr(gameplay_mod, "require_game", lambda key: FakeGame())

    finish_called = {"n": 0}
    monkeypatch.setattr(gameplay_mod.helpers, "finish_duel", lambda duel_id, result: finish_called.__setitem__("n", finish_called["n"] + 1))

    snapshot = gameplay_mod.play_game_action(1, 111, {"move": "rock"})

    assert snapshot == {"game": {"state": "WAITING"}}
    assert finish_called["n"] == 0


def test_play_game_action_finished_invalid_result_raises(monkeypatch):
    duel = _duel_row(game_type="RPS")
    monkeypatch.setattr(gameplay_mod.helpers, "get_duel_or_raise", lambda duel_id: duel)

    class FakeGame:
        def play(self, duel_id, user_id, action):
            return {"game": {"state": "FINISHED", "result": 123}}  # pas str

    monkeypatch.setattr(gameplay_mod, "require_game", lambda key: FakeGame())

    with pytest.raises(exc.InvalidResult):
        gameplay_mod.play_game_action(1, 111, {"move": "rock"})


def test_play_game_action_finished_calls_finish_and_returns_enriched_snapshot(monkeypatch):
    # 1er read duel (avant finish)
    duel1 = _duel_row(
        id=1,
        guild_id=10,
        player_a_id=111,
        player_b_id=222,
        game_type="RPS",
        payload=None,
    )

    # 2e read duel (après finish) : payload avec baseline
    payload = {"xp_baseline": {"player_a_before_xp": 100, "player_b_before_xp": 200}}
    duel2 = _duel_row(
        id=1,
        guild_id=10,
        player_a_id=111,
        player_b_id=222,
        game_type="RPS",
        payload=json.dumps(payload),
    )

    seq = {"i": 0}
    def fake_get_duel(duel_id):
        seq["i"] += 1
        return duel1 if seq["i"] == 1 else duel2

    monkeypatch.setattr(gameplay_mod.helpers, "get_duel_or_raise", fake_get_duel)

    class FakeGame:
        def play(self, duel_id, user_id, action):
            return {"game": {"state": "FINISHED", "result": "A_WIN"}}

    monkeypatch.setattr(gameplay_mod, "require_game", lambda key: FakeGame())

    finish_called = {"args": None}
    monkeypatch.setattr(gameplay_mod.helpers, "finish_duel", lambda duel_id, result: finish_called.__setitem__("args", (duel_id, result)))

    # XP après fin
    monkeypatch.setattr(gameplay_mod.helpers, "get_xp_for_players", lambda gid, a, b: {a: 150, b: 200})

    # Levels + compute_level : simuler un level-up seulement pour A
    monkeypatch.setattr(gameplay_mod, "xp_get_levels", lambda gid: [0, 100, 200, 500])

    def fake_compute_level(xp, levels):
        # 100 -> lvl1 ; 150 -> lvl2 (change)
        # 200 -> lvl3 ; 200 -> lvl3 (pas de change)
        if xp == 100:
            return 1
        if xp == 150:
            return 2
        if xp == 200:
            return 3
        return 0

    monkeypatch.setattr(gameplay_mod, "compute_level", fake_compute_level)

    monkeypatch.setattr(gameplay_mod, "xp_get_role_ids", lambda gid: {1: 1001, 2: 1002})

    # build_snapshot : on capture les params
    captured = {}
    def fake_build_snapshot(*, duel_row, xp=None, game_infos=None, effects=None, **kwargs):
        captured["duel_row"] = duel_row
        captured["xp"] = xp
        captured["game_infos"] = game_infos
        captured["effects"] = effects
        return {"ok": True}

    monkeypatch.setattr(gameplay_mod.helpers, "build_snapshot", fake_build_snapshot)

    out = gameplay_mod.play_game_action(1, 111, {"move": "rock"})

    assert out == {"ok": True}
    assert finish_called["args"] == (1, "A_WIN")
    assert captured["duel_row"] is duel2
    assert captured["xp"] == {111: 150, 222: 200}
    assert captured["game_infos"]["state"] == "FINISHED"
    assert captured["effects"]["xp_changed"] is True
    assert captured["effects"]["sync_roles_user_ids"] == [111, 222]
    assert captured["effects"]["xp_role_ids"] == {1: 1001, 2: 1002}

    # finished_now True => level_changes présent
    assert "level_changes" in captured["effects"]
    assert captured["effects"]["level_changes"] == [
        {"user_id": 111, "old_level": 1, "new_level": 2}
    ]


def test_play_game_action_finished_when_already_handled_does_not_add_level_changes(monkeypatch):
    duel1 = _duel_row(game_type="RPS", payload=None)
    duel2 = _duel_row(game_type="RPS", payload=json.dumps({"xp_baseline": {"player_a_before_xp": 1}}))

    seq = {"i": 0}
    monkeypatch.setattr(
        gameplay_mod.helpers,
        "get_duel_or_raise",
        lambda duel_id: duel1 if (seq.__setitem__("i", seq["i"] + 1) or seq["i"] == 1) else duel2,
    )

    class FakeGame:
        def play(self, duel_id, user_id, action):
            return {"game": {"state": "FINISHED", "result": "DRAW"}}

    monkeypatch.setattr(gameplay_mod, "require_game", lambda key: FakeGame())

    # finish_duel -> DuelAlreadyHandled => finished_now False
    def fake_finish(duel_id, result):
        raise exc.DuelAlreadyHandled(duel_id, "ACTIVE")

    monkeypatch.setattr(gameplay_mod.helpers, "finish_duel", fake_finish)

    monkeypatch.setattr(gameplay_mod.helpers, "get_xp_for_players", lambda gid, a, b: {a: 1, b: 1})
    monkeypatch.setattr(gameplay_mod, "xp_get_levels", lambda gid: [0])
    monkeypatch.setattr(gameplay_mod, "compute_level", lambda xp, levels: 0)
    monkeypatch.setattr(gameplay_mod, "xp_get_role_ids", lambda gid: {})

    captured = {}

    def fake_build_snapshot(*, effects=None, **k):
        captured["effects"] = effects
        return {"ok": True}

    monkeypatch.setattr(gameplay_mod.helpers, "build_snapshot", fake_build_snapshot)

    out = gameplay_mod.play_game_action(1, 222, {"move": "paper"})

    assert out == {"ok": True}
    assert captured["effects"]["xp_changed"] is True
    assert "level_changes" not in captured["effects"]  # finished_now False


# ------------------------------------------------------------
# is_duel_complete_for_game
# ------------------------------------------------------------

def test_is_duel_complete_for_game_returns_false_when_no_game_type():
    duel = _duel_row(game_type=None)
    assert gameplay_mod.is_duel_complete_for_game(duel) is False


def test_is_duel_complete_for_game_returns_false_when_game_unknown(monkeypatch):
    duel = _duel_row(game_type="UNKNOWN")
    monkeypatch.setattr(gameplay_mod, "require_game", lambda key: (_ for _ in ()).throw(ValueError("nope")))
    assert gameplay_mod.is_duel_complete_for_game(duel) is False


def test_is_duel_complete_for_game_delegates_to_game(monkeypatch):
    duel = _duel_row(game_type="RPS")

    class FakeGame:
        def is_complete(self, duel_row):
            return True

    monkeypatch.setattr(gameplay_mod, "require_game", lambda key: FakeGame())
    assert gameplay_mod.is_duel_complete_for_game(duel) is True


# ------------------------------------------------------------
# resolve_duel_for_game
# ------------------------------------------------------------

def test_resolve_duel_for_game_raises_when_no_game_type():
    duel = _duel_row(game_type=None)
    with pytest.raises(exc.WrongGameType):
        gameplay_mod.resolve_duel_for_game(duel)


def test_resolve_duel_for_game_raises_when_game_unknown(monkeypatch):
    duel = _duel_row(game_type="UNKNOWN")
    monkeypatch.setattr(gameplay_mod, "require_game", lambda key: (_ for _ in ()).throw(ValueError("nope")))

    with pytest.raises(exc.WrongGameType):
        gameplay_mod.resolve_duel_for_game(duel)


def test_resolve_duel_for_game_delegates_to_game(monkeypatch):
    duel = _duel_row(game_type="RPS")

    class FakeGame:
        def resolve(self, duel_row):
            return "A_WIN"

    monkeypatch.setattr(gameplay_mod, "require_game", lambda key: FakeGame())
    assert gameplay_mod.resolve_duel_for_game(duel) == "A_WIN"
