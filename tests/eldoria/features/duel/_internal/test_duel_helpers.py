from __future__ import annotations

import json

import pytest

import eldoria.features.duel._internal.helpers as helpers_mod
from eldoria.exceptions import duel_exceptions as exc
from eldoria.features.duel import constants


# ------------------------------------------------------------
# Utilitaires tests
# ------------------------------------------------------------
class FakeConn:
    pass


class FakeConnCtx:
    def __init__(self, conn=None):
        self.conn = conn or FakeConn()

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False


def _duel_row(**overrides):
    """
    helpers.py utilise des clés plutôt "duel_id" (pas "id").
    On fournit donc les champs attendus.
    """
    base = {
        "duel_id": 1,
        "guild_id": 10,
        "channel_id": 20,
        "message_id": 30,
        "player_a_id": 111,
        "player_b_id": 222,
        "status": constants.DUEL_STATUS_ACTIVE,
        "game_type": "RPS",
        "stake_xp": constants.STAKE_XP_DEFAULTS[0] if constants.STAKE_XP_DEFAULTS else 10,
        "expires_at": 9999999999,
        "payload": None,
    }
    base.update(overrides)
    return base


# ------------------------------------------------------------
# load_payload_any / dump_payload
# ------------------------------------------------------------
def test_load_payload_any_returns_empty_when_none_payload():
    duel = _duel_row(payload=None)
    assert helpers_mod.load_payload_any(duel) == {}


def test_load_payload_any_returns_empty_on_invalid_json():
    duel = _duel_row(payload="{not json")
    assert helpers_mod.load_payload_any(duel) == {}


def test_load_payload_any_parses_dict():
    duel = _duel_row(payload=json.dumps({"a": 1, "b": "x"}))
    assert helpers_mod.load_payload_any(duel) == {"a": 1, "b": "x"}


def test_dump_payload_is_compact():
    out = helpers_mod.dump_payload({"a": 1, "b": {"c": 2}})
    assert out == '{"a":1,"b":{"c":2}}'


# ------------------------------------------------------------
# _get_allowed_stakes_from_duel / get_allowed_stakes
# ------------------------------------------------------------
def test_get_allowed_stakes_from_duel_returns_empty_when_no_duel():
    assert helpers_mod._get_allowed_stakes_from_duel(None) == []  # type: ignore[arg-type]


def test_get_allowed_stakes_from_duel_filters_by_both_players_xp(monkeypatch):
    duel = _duel_row(guild_id=10, player_a_id=111, player_b_id=222)

    # A a beaucoup, B a peu -> stakes <= B
    def fake_xp_get_member(gid, uid, conn=None):
        return (1000,) if uid == 111 else (50,)

    monkeypatch.setattr(helpers_mod, "xp_get_member", fake_xp_get_member)

    allowed = helpers_mod._get_allowed_stakes_from_duel(duel)
    assert all(stake <= 50 for stake in allowed)
    # au moins 1 stake possible si defaults contient des petites valeurs
    assert isinstance(allowed, list)


def test_get_allowed_stakes_calls_repo_and_delegates(monkeypatch):
    duel = _duel_row()

    monkeypatch.setattr(helpers_mod, "get_duel_by_id", lambda duel_id: duel)
    monkeypatch.setattr(helpers_mod, "_get_allowed_stakes_from_duel", lambda d: [10, 20])

    assert helpers_mod.get_allowed_stakes(123) == [10, 20]


# ------------------------------------------------------------
# is_configuration_available
# ------------------------------------------------------------
def test_is_configuration_available_false_when_no_duel(monkeypatch):
    monkeypatch.setattr(helpers_mod, "get_duel_by_id", lambda duel_id: None)
    assert helpers_mod.is_configuration_available(1) is False


def test_is_configuration_available_false_when_wrong_status(monkeypatch):
    duel = _duel_row(status=constants.DUEL_STATUS_INVITED, game_type=next(iter(constants.GAME_TYPES)), stake_xp=constants.STAKE_XP_DEFAULTS[0])
    monkeypatch.setattr(helpers_mod, "get_duel_by_id", lambda duel_id: duel)
    monkeypatch.setattr(helpers_mod, "_get_allowed_stakes_from_duel", lambda d: [duel["stake_xp"]])

    assert helpers_mod.is_configuration_available(1) is False


def test_is_configuration_available_true(monkeypatch):
    game_type = next(iter(constants.GAME_TYPES))
    stake = constants.STAKE_XP_DEFAULTS[0] if constants.STAKE_XP_DEFAULTS else 10

    duel = _duel_row(status=constants.DUEL_STATUS_CONFIG, game_type=game_type, stake_xp=stake)
    monkeypatch.setattr(helpers_mod, "get_duel_by_id", lambda duel_id: duel)
    monkeypatch.setattr(helpers_mod, "_get_allowed_stakes_from_duel", lambda d: [stake])

    assert helpers_mod.is_configuration_available(1) is True


# ------------------------------------------------------------
# modify_xp_for_players / get_xp_for_players
# ------------------------------------------------------------
def test_modify_xp_for_players_calls_xp_add_xp_twice(monkeypatch):
    calls = []

    def fake_xp_add(gid, uid, delta, conn=None):
        calls.append((gid, uid, delta, conn))
        return 123 if uid == 111 else 456

    monkeypatch.setattr(helpers_mod, "xp_add_xp", fake_xp_add)

    conn = FakeConn()
    out = helpers_mod.modify_xp_for_players(10, 111, 222, 5, conn=conn)

    assert out == {111: 123, 222: 456}
    assert calls == [(10, 111, 5, conn), (10, 222, 5, conn)]


def test_get_xp_for_players_reads_xp_get_member(monkeypatch):
    def fake_get_member(gid, uid, conn=None):
        return (100,) if uid == 111 else (200,)

    monkeypatch.setattr(helpers_mod, "xp_get_member", fake_get_member)

    out = helpers_mod.get_xp_for_players(10, 111, 222)
    assert out == {111: 100, 222: 200}


# ------------------------------------------------------------
# assert_duel_not_expired / get_duel_or_raise
# ------------------------------------------------------------
def test_assert_duel_not_expired_raises_when_expired(monkeypatch):
    monkeypatch.setattr(helpers_mod, "now_ts", lambda: 1000)

    duel = _duel_row(expires_at=999, duel_id=1)  # expires_at <= now
    with pytest.raises(exc.ExpiredDuel):
        helpers_mod.assert_duel_not_expired(duel)


def test_assert_duel_not_expired_ok_when_no_expires_at(monkeypatch):
    monkeypatch.setattr(helpers_mod, "now_ts", lambda: 1000)
    duel = _duel_row(expires_at=None)
    helpers_mod.assert_duel_not_expired(duel)  # no raise


def test_get_duel_or_raise_raises_when_not_found(monkeypatch):
    monkeypatch.setattr(helpers_mod, "get_duel_by_id", lambda duel_id: None)
    with pytest.raises(exc.DuelNotFound):
        helpers_mod.get_duel_or_raise(1)


def test_get_duel_or_raise_returns_row(monkeypatch):
    duel = _duel_row(duel_id=123)
    monkeypatch.setattr(helpers_mod, "get_duel_by_id", lambda duel_id: duel)
    assert helpers_mod.get_duel_or_raise(123) is duel


# ------------------------------------------------------------
# build_snapshot
# ------------------------------------------------------------
def test_build_snapshot_minimal_shape():
    duel = _duel_row(
        duel_id=1,
        channel_id=2,
        message_id=3,
        status="S",
        player_a_id=10,
        player_b_id=11,
        game_type="RPS",
        stake_xp=50,
        expires_at=999,
    )

    snap = helpers_mod.build_snapshot(duel)

    assert snap["duel"]["id"] == 1
    assert snap["duel"]["channel_id"] == 2
    assert snap["duel"]["message_id"] == 3
    assert snap["duel"]["status"] == "S"
    assert snap["duel"]["player_a"] == 10
    assert snap["duel"]["player_b"] == 11
    assert snap["duel"]["game_type"] == "RPS"
    assert snap["duel"]["stake_xp"] == 50
    assert snap["duel"]["expires_at"] == 999

    assert "ui" not in snap
    assert "xp" not in snap
    assert "game" not in snap
    assert "effects" not in snap


def test_build_snapshot_optional_sections():
    duel = _duel_row()

    snap = helpers_mod.build_snapshot(
        duel,
        allowed_stakes=[10, 20],
        xp={111: 1, 222: 2},
        game_infos={"state": "WAITING"},
        effects={"xp_changed": True},
    )

    assert snap["ui"] == {"allowed_stakes": [10, 20]}
    assert snap["xp"] == {111: 1, 222: 2}
    assert snap["game"] == {"state": "WAITING"}
    assert snap["effects"] == {"xp_changed": True}


# ------------------------------------------------------------
# finish_duel
# ------------------------------------------------------------
def test_finish_duel_rejects_invalid_result(monkeypatch):
    duel = _duel_row(status=constants.DUEL_STATUS_ACTIVE)
    monkeypatch.setattr(helpers_mod, "get_duel_or_raise", lambda duel_id: duel)
    monkeypatch.setattr(helpers_mod, "assert_duel_not_expired", lambda d: None)

    with pytest.raises(exc.InvalidResult):
        helpers_mod.finish_duel(1, "NOT_A_RESULT")


def test_finish_duel_rejects_when_not_active(monkeypatch):
    duel = _duel_row(status=constants.DUEL_STATUS_CONFIG)
    monkeypatch.setattr(helpers_mod, "get_duel_or_raise", lambda duel_id: duel)
    monkeypatch.setattr(helpers_mod, "assert_duel_not_expired", lambda d: None)

    with pytest.raises(exc.DuelNotFinishable):
        helpers_mod.finish_duel(1, constants.DUEL_RESULT_DRAW)


def test_finish_duel_transitions_and_pays_draw(monkeypatch):
    duel = _duel_row(
        duel_id=1,
        status=constants.DUEL_STATUS_ACTIVE,
        guild_id=10,
        player_a_id=111,
        player_b_id=222,
        stake_xp=10,
    )

    monkeypatch.setattr(helpers_mod, "get_duel_or_raise", lambda duel_id: duel)
    monkeypatch.setattr(helpers_mod, "assert_duel_not_expired", lambda d: None)

    conn = FakeConn()
    monkeypatch.setattr(helpers_mod, "get_conn", lambda: FakeConnCtx(conn))

    # transition ok
    monkeypatch.setattr(helpers_mod, "transition_status", lambda *a, **k: True)

    # draw -> modify_xp_for_players(+stake)
    calls = {"modify": None, "update": None}
    monkeypatch.setattr(
        helpers_mod,
        "modify_xp_for_players",
        lambda gid, a, b, delta, conn=None: calls.__setitem__("modify", (gid, a, b, delta, conn)) or {},
    )

    monkeypatch.setattr(helpers_mod, "now_ts", lambda: 12345)

    def fake_update(duel_id, required_status, finished_at, conn=None, **k):
        calls["update"] = (duel_id, required_status, finished_at, conn)
        return True

    monkeypatch.setattr(helpers_mod, "update_duel_if_status", fake_update)

    helpers_mod.finish_duel(1, constants.DUEL_RESULT_DRAW)

    assert calls["modify"] == (10, 111, 222, 10, conn)
    assert calls["update"] == (1, constants.DUEL_STATUS_FINISHED, 12345, conn)


def test_finish_duel_transitions_and_pays_win_a(monkeypatch):
    duel = _duel_row(
        duel_id=1,
        status=constants.DUEL_STATUS_ACTIVE,
        guild_id=10,
        player_a_id=111,
        player_b_id=222,
        stake_xp=10,
    )

    monkeypatch.setattr(helpers_mod, "get_duel_or_raise", lambda duel_id: duel)
    monkeypatch.setattr(helpers_mod, "assert_duel_not_expired", lambda d: None)

    conn = FakeConn()
    monkeypatch.setattr(helpers_mod, "get_conn", lambda: FakeConnCtx(conn))
    monkeypatch.setattr(helpers_mod, "transition_status", lambda *a, **k: True)

    pay_calls = []
    monkeypatch.setattr(helpers_mod, "xp_add_xp", lambda gid, uid, delta, conn=None: pay_calls.append((gid, uid, delta, conn)) or 0)

    monkeypatch.setattr(helpers_mod, "now_ts", lambda: 1)
    monkeypatch.setattr(helpers_mod, "update_duel_if_status", lambda *a, **k: True)

    helpers_mod.finish_duel(1, constants.DUEL_RESULT_WIN_A)

    assert pay_calls == [(10, 111, 20, conn)]


def test_finish_duel_raises_duel_already_handled_when_transition_fails(monkeypatch):
    duel = _duel_row(status=constants.DUEL_STATUS_ACTIVE)
    monkeypatch.setattr(helpers_mod, "get_duel_or_raise", lambda duel_id: duel)
    monkeypatch.setattr(helpers_mod, "assert_duel_not_expired", lambda d: None)

    conn = FakeConn()
    monkeypatch.setattr(helpers_mod, "get_conn", lambda: FakeConnCtx(conn))

    monkeypatch.setattr(helpers_mod, "transition_status", lambda *a, **k: False)

    with pytest.raises(exc.DuelAlreadyHandled):
        helpers_mod.finish_duel(1, constants.DUEL_RESULT_DRAW)


def test_finish_duel_raises_duel_not_finished_when_update_fails(monkeypatch):
    duel = _duel_row(status=constants.DUEL_STATUS_ACTIVE, stake_xp=10)
    monkeypatch.setattr(helpers_mod, "get_duel_or_raise", lambda duel_id: duel)
    monkeypatch.setattr(helpers_mod, "assert_duel_not_expired", lambda d: None)

    conn = FakeConn()
    monkeypatch.setattr(helpers_mod, "get_conn", lambda: FakeConnCtx(conn))

    monkeypatch.setattr(helpers_mod, "transition_status", lambda *a, **k: True)
    monkeypatch.setattr(helpers_mod, "modify_xp_for_players", lambda *a, **k: {})
    monkeypatch.setattr(helpers_mod, "now_ts", lambda: 1)

    monkeypatch.setattr(helpers_mod, "update_duel_if_status", lambda *a, **k: False)

    with pytest.raises(exc.DuelNotFinished):
        helpers_mod.finish_duel(1, constants.DUEL_RESULT_DRAW)
