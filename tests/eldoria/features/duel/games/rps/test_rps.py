from __future__ import annotations

import json

import pytest

import eldoria.features.duel.games.rps.rps as rps_mod
from eldoria.exceptions import duel as exc
from eldoria.features.duel import constants
from eldoria.features.duel.games.rps import rps_constants as rps


def _duel_row(**overrides):
    base = {
        "duel_id": 1,
        "guild_id": 10,
        "channel_id": 20,
        "message_id": 30,
        "player_a_id": 111,
        "player_b_id": 222,
        "stake_xp": 10,
        "game_type": constants.GAME_RPS,
        "status": constants.DUEL_STATUS_ACTIVE,
        "expires_at": None,
        "payload": None,
    }
    base.update(overrides)
    return base


# ------------------------------------------------------------
# helpers: load_rps_payload
# ------------------------------------------------------------

def test_load_rps_payload_returns_defaults_when_payload_missing():
    duel = _duel_row(payload=None)
    payload = rps_mod.load_rps_payload(duel)

    assert payload[rps.RPS_PAYLOAD_VERSION] == 1
    assert payload[rps.RPS_PAYLOAD_A_MOVE] is None
    assert payload[rps.RPS_PAYLOAD_B_MOVE] is None


def test_load_rps_payload_raises_when_payload_invalid_json():
    from eldoria.exceptions.duel import PayloadError

    duel = _duel_row(payload="{not json")
    with pytest.raises(PayloadError):
        rps_mod.load_rps_payload(duel)

def test_load_rps_payload_parses_valid_json():
    duel = _duel_row(payload=json.dumps({rps.RPS_PAYLOAD_A_MOVE: rps.RPS_MOVE_ROCK, rps.RPS_PAYLOAD_B_MOVE: None}))
    payload = rps_mod.load_rps_payload(duel)

    assert payload[rps.RPS_PAYLOAD_A_MOVE] == rps.RPS_MOVE_ROCK
    assert payload[rps.RPS_PAYLOAD_B_MOVE] is None


# ------------------------------------------------------------
# helpers: who_is_moving / assert_duel_playable
# ------------------------------------------------------------

def test_who_is_moving_raises_if_user_not_in_duel():
    duel = _duel_row(player_a_id=1, player_b_id=2)
    with pytest.raises(exc.NotAuthorizedPlayer):
        rps_mod.who_is_moving(duel, 999)


def test_who_is_moving_returns_correct_slot():
    duel = _duel_row(player_a_id=111, player_b_id=222)
    assert rps_mod.who_is_moving(duel, 111) == rps.RPS_PAYLOAD_A_MOVE
    assert rps_mod.who_is_moving(duel, 222) == rps.RPS_PAYLOAD_B_MOVE


def test_assert_duel_playable_raises_when_not_active():
    duel = _duel_row(status=constants.DUEL_STATUS_INVITED)
    with pytest.raises(exc.DuelNotActive):
        rps_mod.assert_duel_playable(duel, 111)


def test_assert_duel_playable_raises_when_wrong_game_type():
    duel = _duel_row(game_type="SOME_OTHER")
    with pytest.raises(exc.WrongGameType):
        rps_mod.assert_duel_playable(duel, 111)


def test_assert_duel_playable_raises_when_user_not_in_duel():
    duel = _duel_row(player_a_id=1, player_b_id=2)
    with pytest.raises(exc.NotAuthorizedPlayer):
        rps_mod.assert_duel_playable(duel, 999)


# ------------------------------------------------------------
# compute_rps_result
# ------------------------------------------------------------

@pytest.mark.parametrize(
    "a,b,expected",
    [
        (rps.RPS_MOVE_ROCK, rps.RPS_MOVE_ROCK, constants.DUEL_RESULT_DRAW),
        (rps.RPS_MOVE_PAPER, rps.RPS_MOVE_PAPER, constants.DUEL_RESULT_DRAW),
        (rps.RPS_MOVE_SCISSORS, rps.RPS_MOVE_SCISSORS, constants.DUEL_RESULT_DRAW),
    ],
)
def test_compute_rps_result_draw(a, b, expected):
    assert rps_mod.compute_rps_result(a, b) == expected


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (rps.RPS_MOVE_ROCK, rps.RPS_MOVE_SCISSORS, constants.DUEL_RESULT_WIN_A),
        (rps.RPS_MOVE_PAPER, rps.RPS_MOVE_ROCK, constants.DUEL_RESULT_WIN_A),
        (rps.RPS_MOVE_SCISSORS, rps.RPS_MOVE_PAPER, constants.DUEL_RESULT_WIN_A),

        (rps.RPS_MOVE_SCISSORS, rps.RPS_MOVE_ROCK, constants.DUEL_RESULT_WIN_B),
        (rps.RPS_MOVE_ROCK, rps.RPS_MOVE_PAPER, constants.DUEL_RESULT_WIN_B),
        (rps.RPS_MOVE_PAPER, rps.RPS_MOVE_SCISSORS, constants.DUEL_RESULT_WIN_B),
    ],
)
def test_compute_rps_result_win_loss(a, b, expected):
    assert rps_mod.compute_rps_result(a, b) == expected


def test_compute_rps_result_raises_on_invalid_move():
    with pytest.raises(exc.InvalidMove):
        rps_mod.compute_rps_result("lizard", rps.RPS_MOVE_ROCK)


# ------------------------------------------------------------
# _persist_move_cas (CAS)
# ------------------------------------------------------------

def test_persist_move_cas_succeeds_first_try(monkeypatch):
    duel = _duel_row(payload=None)

    monkeypatch.setattr(rps_mod.helpers, "get_duel_or_raise", lambda duel_id: duel)
    monkeypatch.setattr(rps_mod.helpers, "dump_payload", lambda payload: json.dumps(payload, separators=(",", ":")))

    calls = {"n": 0}
    def cas(duel_id, old, new):
        calls["n"] += 1
        return True

    monkeypatch.setattr(rps_mod, "update_payload_if_unchanged", cas)

    rps_mod._persist_move_cas(1, rps.RPS_PAYLOAD_A_MOVE, rps.RPS_MOVE_ROCK)
    assert calls["n"] == 1


def test_persist_move_cas_retries_then_succeeds(monkeypatch):
    duel1 = _duel_row(payload=None)
    duel2 = _duel_row(payload=None)

    seq = {"i": 0}
    def get_duel(_):
        seq["i"] += 1
        return duel1 if seq["i"] == 1 else duel2

    monkeypatch.setattr(rps_mod.helpers, "get_duel_or_raise", get_duel)
    monkeypatch.setattr(rps_mod.helpers, "dump_payload", lambda payload: json.dumps(payload, separators=(",", ":")))

    calls = {"n": 0}
    def cas(duel_id, old, new):
        calls["n"] += 1
        return calls["n"] == 2  # échoue 1 fois, puis ok

    monkeypatch.setattr(rps_mod, "update_payload_if_unchanged", cas)

    rps_mod._persist_move_cas(1, rps.RPS_PAYLOAD_A_MOVE, rps.RPS_MOVE_ROCK)
    assert calls["n"] == 2


def test_persist_move_cas_fails_twice_then_raises(monkeypatch):
    duel = _duel_row(payload=None)
    monkeypatch.setattr(rps_mod.helpers, "get_duel_or_raise", lambda duel_id: duel)
    monkeypatch.setattr(rps_mod.helpers, "dump_payload", lambda payload: json.dumps(payload, separators=(",", ":")))

    monkeypatch.setattr(rps_mod, "update_payload_if_unchanged", lambda duel_id, old, new: False)

    with pytest.raises(exc.PayloadError):
        rps_mod._persist_move_cas(1, rps.RPS_PAYLOAD_A_MOVE, rps.RPS_MOVE_ROCK)


def test_apply_move_or_raise_prevents_second_move():
    payload = {rps.RPS_PAYLOAD_A_MOVE: rps.RPS_MOVE_ROCK}
    with pytest.raises(exc.AlreadyPlayed):
        rps_mod._apply_move_or_raise(payload, rps.RPS_PAYLOAD_A_MOVE, rps.RPS_MOVE_PAPER)


# ------------------------------------------------------------
# RPSGame.play / is_complete / resolve
# ------------------------------------------------------------

def test_play_returns_waiting_when_other_has_not_played(monkeypatch):
    duel_after = _duel_row(payload=json.dumps({rps.RPS_PAYLOAD_A_MOVE: rps.RPS_MOVE_ROCK, rps.RPS_PAYLOAD_B_MOVE: None}))

    # 1er get_duel (avant persist) + 2e get_duel (après persist)
    seq = {"i": 0}
    def get_duel(_):
        seq["i"] += 1
        return _duel_row(payload=None) if seq["i"] == 1 else duel_after

    monkeypatch.setattr(rps_mod.helpers, "get_duel_or_raise", get_duel)
    monkeypatch.setattr(rps_mod.helpers, "assert_duel_not_expired", lambda duel: None)

    # On bypass le CAS (on teste la logique "waiting")
    monkeypatch.setattr(rps_mod, "_persist_move_cas", lambda duel_id, slot, move: None)

    captured = {}
    def build_snapshot(*, duel_row, game_infos=None, **kwargs):
        captured["duel_row"] = duel_row
        captured["game_infos"] = game_infos
        return {"ok": True, "game": game_infos}

    monkeypatch.setattr(rps_mod.helpers, "build_snapshot", build_snapshot)

    out = rps_mod.RPSGame.play(1, 111, {"move": rps.RPS_MOVE_ROCK})

    assert out["ok"] is True
    assert out["game"][rps.RPS_DICT_STATE] == rps.RPS_STATE_WAITING
    assert out["game"]["a_played"] is True
    assert out["game"]["b_played"] is False


def test_play_returns_finished_when_both_played(monkeypatch):
    duel_after = _duel_row(
        payload=json.dumps({rps.RPS_PAYLOAD_A_MOVE: rps.RPS_MOVE_ROCK, rps.RPS_PAYLOAD_B_MOVE: rps.RPS_MOVE_SCISSORS})
    )

    seq = {"i": 0}
    def get_duel(_):
        seq["i"] += 1
        return _duel_row(payload=None) if seq["i"] == 1 else duel_after

    monkeypatch.setattr(rps_mod.helpers, "get_duel_or_raise", get_duel)
    monkeypatch.setattr(rps_mod.helpers, "assert_duel_not_expired", lambda duel: None)
    monkeypatch.setattr(rps_mod, "_persist_move_cas", lambda duel_id, slot, move: None)

    monkeypatch.setattr(rps_mod.helpers, "build_snapshot", lambda *, game_infos=None, **k: {"game": game_infos})

    out = rps_mod.RPSGame.play(1, 111, {"move": rps.RPS_MOVE_ROCK})

    assert out["game"][rps.RPS_DICT_STATE] == rps.RPS_STATE_FINISHED
    assert out["game"][rps.RPS_DICT_RESULT] == constants.DUEL_RESULT_WIN_A
    assert out["game"][rps.RPS_PAYLOAD_A_MOVE] == rps.RPS_MOVE_ROCK
    assert out["game"][rps.RPS_PAYLOAD_B_MOVE] == rps.RPS_MOVE_SCISSORS


def test_play_raises_on_invalid_action_move(monkeypatch):
    monkeypatch.setattr(rps_mod.helpers, "get_duel_or_raise", lambda duel_id: _duel_row())
    monkeypatch.setattr(rps_mod.helpers, "assert_duel_not_expired", lambda duel: None)

    with pytest.raises(exc.InvalidMove):
        rps_mod.RPSGame.play(1, 111, {"move": "invalid"})


def test_is_complete_true_when_both_moves_present():
    duel = _duel_row(payload=json.dumps({rps.RPS_PAYLOAD_A_MOVE: rps.RPS_MOVE_ROCK, rps.RPS_PAYLOAD_B_MOVE: rps.RPS_MOVE_PAPER}))
    assert rps_mod.RPSGame.is_complete(duel) is True


def test_is_complete_false_when_missing_one_move():
    duel = _duel_row(payload=json.dumps({rps.RPS_PAYLOAD_A_MOVE: rps.RPS_MOVE_ROCK, rps.RPS_PAYLOAD_B_MOVE: None}))
    assert rps_mod.RPSGame.is_complete(duel) is False


def test_resolve_raises_when_incomplete_payload():
    duel = _duel_row(payload=json.dumps({rps.RPS_PAYLOAD_A_MOVE: rps.RPS_MOVE_ROCK, rps.RPS_PAYLOAD_B_MOVE: None}))
    with pytest.raises(exc.PayloadError):
        rps_mod.RPSGame.resolve(duel)
