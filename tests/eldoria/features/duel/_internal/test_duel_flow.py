from __future__ import annotations

import pytest

import eldoria.features.duel._internal.flow as flow_mod
from eldoria.exceptions import duel_exceptions as exc
from eldoria.features.duel import constants
from tests._fakes._db_fakes import FakeConnCM


# ------------------------------------------------------------
# Helpers de test
# ------------------------------------------------------------
class FakeConn:
    pass

def _minimal_duel_row(**overrides):
    base = {
        "id": 1,
        "guild_id": 10,
        "channel_id": 20,
        "player_a_id": 111,
        "player_b_id": 222,
        "status": constants.DUEL_STATUS_CONFIG,
        "stake_xp": 10,
        "game_type": "RPS",
        "payload": None,
        "expires_at": 9999999999,
    }
    base.update(overrides)
    return base

# ------------------------------------------------------------
# new_duel
# ------------------------------------------------------------
def test_new_duel_rejects_same_players(monkeypatch):
    with pytest.raises(exc.SamePlayerDuel):
        flow_mod.new_duel(1, 2, 3, 3)

def test_new_duel_rejects_if_any_player_already_in_duel(monkeypatch):
    monkeypatch.setattr(flow_mod.duel_repo, "get_active_duel_for_user", lambda gid, uid: {"id": 99})
    with pytest.raises(exc.PlayerAlreadyInDuel):
        flow_mod.new_duel(1, 2, 3, 4)

def test_new_duel_creates_and_returns_snapshot(monkeypatch):
    calls = {}

    monkeypatch.setattr(flow_mod.duel_repo, "get_active_duel_for_user", lambda gid, uid: None)
    monkeypatch.setattr(flow_mod, "now_ts", lambda: 1000)
    monkeypatch.setattr(flow_mod, "add_duration", lambda ts, minutes=0, **k: ts + minutes * 60)

    def fake_create(guild_id, channel_id, a, b, created_at, expires_at):
        calls["create"] = (guild_id, channel_id, a, b, created_at, expires_at)
        return 777

    monkeypatch.setattr(flow_mod.duel_repo, "create_duel", fake_create)

    duel_row = _minimal_duel_row(id=777)
    monkeypatch.setattr(flow_mod.helpers, "get_duel_or_raise", lambda duel_id: duel_row)

    def fake_snapshot(*, duel_row, allowed_stakes=None, xp=None):
        calls["snapshot"] = {"duel_row": duel_row, "allowed_stakes": allowed_stakes, "xp": xp}
        return {"snapshot": True, "id": duel_row["id"]}

    monkeypatch.setattr(flow_mod.helpers, "build_snapshot", fake_snapshot)

    out = flow_mod.new_duel(10, 20, 111, 222)

    assert calls["create"] == (10, 20, 111, 222, 1000, 1000 + 600)
    assert out == {"snapshot": True, "id": 777}

# ------------------------------------------------------------
# configure_game_type
# ------------------------------------------------------------
def test_configure_game_type_rejects_invalid_type(monkeypatch):
    duel = _minimal_duel_row(status=constants.DUEL_STATUS_CONFIG)
    monkeypatch.setattr(flow_mod.helpers, "get_duel_or_raise", lambda duel_id: duel)
    monkeypatch.setattr(flow_mod.helpers, "assert_duel_not_expired", lambda d: None)

    with pytest.raises(exc.InvalidGameType):
        flow_mod.configure_game_type(1, "NOT_A_GAME")

def test_configure_game_type_raises_on_update_failure(monkeypatch):
    duel = _minimal_duel_row(status=constants.DUEL_STATUS_CONFIG)
    monkeypatch.setattr(flow_mod.helpers, "get_duel_or_raise", lambda duel_id: duel)
    monkeypatch.setattr(flow_mod.helpers, "assert_duel_not_expired", lambda d: None)

    valid_game = next(iter(constants.GAME_TYPES))
    monkeypatch.setattr(flow_mod.duel_repo, "update_duel_if_status", lambda *a, **k: False)

    with pytest.raises(exc.ConfigurationError):
        flow_mod.configure_game_type(1, valid_game)

def test_configure_game_type_success_returns_snapshot_with_allowed_stakes(monkeypatch):
    duel_before = _minimal_duel_row(id=1, status=constants.DUEL_STATUS_CONFIG)
    duel_after = _minimal_duel_row(id=1, status=constants.DUEL_STATUS_CONFIG, game_type="RPS")

    seq = {"i": 0}

    def fake_get_duel(duel_id):
        seq["i"] += 1
        return duel_before if seq["i"] == 1 else duel_after

    monkeypatch.setattr(flow_mod.helpers, "get_duel_or_raise", fake_get_duel)
    monkeypatch.setattr(flow_mod.helpers, "assert_duel_not_expired", lambda d: None)

    valid_game = "RPS" if "RPS" in constants.GAME_TYPES else next(iter(constants.GAME_TYPES))
    monkeypatch.setattr(flow_mod.duel_repo, "update_duel_if_status", lambda *a, **k: True)

    monkeypatch.setattr(flow_mod.helpers, "_get_allowed_stakes_from_duel", lambda d: [10, 20])

    monkeypatch.setattr(
        flow_mod.helpers,
        "build_snapshot",
        lambda *, duel_row, allowed_stakes=None, xp=None: {"id": duel_row["id"], "allowed_stakes": allowed_stakes},
    )

    out = flow_mod.configure_game_type(1, valid_game)
    assert out["id"] == 1
    assert out["allowed_stakes"] == [10, 20]

# ------------------------------------------------------------
# configure_stake_xp
# ------------------------------------------------------------
def test_configure_stake_xp_rejects_invalid_stake(monkeypatch):
    duel = _minimal_duel_row(status=constants.DUEL_STATUS_CONFIG)
    monkeypatch.setattr(flow_mod.helpers, "get_duel_or_raise", lambda duel_id: duel)
    monkeypatch.setattr(flow_mod.helpers, "assert_duel_not_expired", lambda d: None)

    with pytest.raises(exc.InvalidStake):
        flow_mod.configure_stake_xp(1, 999999)

def test_configure_stake_xp_rejects_not_allowed(monkeypatch):
    duel = _minimal_duel_row(status=constants.DUEL_STATUS_CONFIG)
    monkeypatch.setattr(flow_mod.helpers, "get_duel_or_raise", lambda duel_id: duel)
    monkeypatch.setattr(flow_mod.helpers, "assert_duel_not_expired", lambda d: None)

    stake = constants.STAKE_XP_DEFAULTS[0]
    monkeypatch.setattr(flow_mod.helpers, "get_allowed_stakes", lambda duel_id: [])

    with pytest.raises(exc.InsufficientXp):
        flow_mod.configure_stake_xp(1, stake)

def test_configure_stake_xp_success(monkeypatch):
    duel_before = _minimal_duel_row(id=1, status=constants.DUEL_STATUS_CONFIG)
    duel_after = _minimal_duel_row(id=1, status=constants.DUEL_STATUS_CONFIG, stake_xp=constants.STAKE_XP_DEFAULTS[0])

    seq = {"i": 0}

    def fake_get_duel(duel_id):
        seq["i"] += 1
        return duel_before if seq["i"] == 1 else duel_after

    monkeypatch.setattr(flow_mod.helpers, "get_duel_or_raise", fake_get_duel)
    monkeypatch.setattr(flow_mod.helpers, "assert_duel_not_expired", lambda d: None)

    stake = constants.STAKE_XP_DEFAULTS[0]
    monkeypatch.setattr(flow_mod.helpers, "get_allowed_stakes", lambda duel_id: [stake])
    monkeypatch.setattr(flow_mod.duel_repo, "update_duel_if_status", lambda *a, **k: True)
    monkeypatch.setattr(flow_mod.helpers, "build_snapshot", lambda *, duel_row, **k: {"id": duel_row["id"], "stake": duel_row["stake_xp"]})

    out = flow_mod.configure_stake_xp(1, stake)
    assert out == {"id": 1, "stake": stake}

# ------------------------------------------------------------
# send_invite
# ------------------------------------------------------------
def test_send_invite_rejects_incomplete_configuration(monkeypatch):
    duel = _minimal_duel_row(id=1, status=constants.DUEL_STATUS_CONFIG)
    monkeypatch.setattr(flow_mod.helpers, "get_duel_or_raise", lambda duel_id: duel)
    monkeypatch.setattr(flow_mod.helpers, "assert_duel_not_expired", lambda d: None)
    monkeypatch.setattr(flow_mod.helpers, "is_configuration_available", lambda duel_id: False)

    with pytest.raises(exc.ConfigurationIncomplete):
        flow_mod.send_invite(1, message_id=123)

def test_send_invite_rejects_missing_message_id(monkeypatch):
    duel = _minimal_duel_row(id=1, status=constants.DUEL_STATUS_CONFIG)
    monkeypatch.setattr(flow_mod.helpers, "get_duel_or_raise", lambda duel_id: duel)
    monkeypatch.setattr(flow_mod.helpers, "assert_duel_not_expired", lambda d: None)
    monkeypatch.setattr(flow_mod.helpers, "is_configuration_available", lambda duel_id: True)

    with pytest.raises(exc.MissingMessageId):
        flow_mod.send_invite(1, message_id=0)

def test_send_invite_success(monkeypatch):
    duel_before = _minimal_duel_row(id=1, status=constants.DUEL_STATUS_CONFIG, guild_id=10, player_a_id=111, player_b_id=222)
    duel_after = _minimal_duel_row(id=1, status=constants.DUEL_STATUS_INVITED, guild_id=10, player_a_id=111, player_b_id=222)

    seq = {"i": 0}

    def fake_get_duel(duel_id):
        seq["i"] += 1
        return duel_before if seq["i"] == 1 else duel_after

    monkeypatch.setattr(flow_mod.helpers, "get_duel_or_raise", fake_get_duel)
    monkeypatch.setattr(flow_mod.helpers, "assert_duel_not_expired", lambda d: None)
    monkeypatch.setattr(flow_mod.helpers, "is_configuration_available", lambda duel_id: True)

    monkeypatch.setattr(flow_mod.duel_repo, "update_duel_if_status", lambda *a, **k: True)
    monkeypatch.setattr(flow_mod, "now_ts", lambda: 1000)
    monkeypatch.setattr(flow_mod, "add_duration", lambda ts, minutes=0, **k: ts + minutes * 60)
    monkeypatch.setattr(flow_mod.duel_repo, "transition_status", lambda *a, **k: True)

    monkeypatch.setattr(flow_mod.helpers, "get_xp_for_players", lambda gid, a, b: {"a": 10, "b": 20})
    monkeypatch.setattr(
        flow_mod.helpers,
        "build_snapshot",
        lambda *, duel_row, xp=None, **k: {"id": duel_row["id"], "status": duel_row["status"], "xp": xp},
    )

    out = flow_mod.send_invite(1, message_id=999)
    assert out["status"] == constants.DUEL_STATUS_INVITED
    assert out["xp"] == {"a": 10, "b": 20}

# ------------------------------------------------------------
# accept_duel
# ------------------------------------------------------------
def test_accept_duel_rejects_not_player_b(monkeypatch):
    duel = _minimal_duel_row(id=1, status=constants.DUEL_STATUS_INVITED, player_b_id=222)
    monkeypatch.setattr(flow_mod.helpers, "get_duel_or_raise", lambda duel_id: duel)
    monkeypatch.setattr(flow_mod.helpers, "assert_duel_not_expired", lambda d: None)

    with pytest.raises(exc.NotAuthorizedPlayer):
        flow_mod.accept_duel(1, user_id=999)

def test_accept_duel_rejects_wrong_status(monkeypatch):
    duel = _minimal_duel_row(id=1, status=constants.DUEL_STATUS_CONFIG, player_b_id=222)
    monkeypatch.setattr(flow_mod.helpers, "get_duel_or_raise", lambda duel_id: duel)
    monkeypatch.setattr(flow_mod.helpers, "assert_duel_not_expired", lambda d: None)

    with pytest.raises(exc.DuelNotAcceptable):
        flow_mod.accept_duel(1, user_id=222)

def test_accept_duel_rejects_insufficient_xp(monkeypatch):
    duel = _minimal_duel_row(id=1, status=constants.DUEL_STATUS_INVITED, player_b_id=222, stake_xp=10)
    monkeypatch.setattr(flow_mod.helpers, "get_duel_or_raise", lambda duel_id: duel)
    monkeypatch.setattr(flow_mod.helpers, "assert_duel_not_expired", lambda d: None)
    monkeypatch.setattr(flow_mod.helpers, "_get_allowed_stakes_from_duel", lambda d: [])  # 10 pas autorisé

    with pytest.raises(exc.InsufficientXp):
        flow_mod.accept_duel(1, user_id=222)

def test_accept_duel_success_sets_baseline_and_debits_xp(monkeypatch):
    duel_before = _minimal_duel_row(
        id=1,
        status=constants.DUEL_STATUS_INVITED,
        guild_id=10,
        player_a_id=111,
        player_b_id=222,
        stake_xp=10,
        payload=None,
    )
    duel_after = _minimal_duel_row(id=1, status=constants.DUEL_STATUS_ACTIVE)

    seq = {"i": 0}

    def fake_get_duel(duel_id):
        seq["i"] += 1
        return duel_before if seq["i"] == 1 else duel_after

    monkeypatch.setattr(flow_mod.helpers, "get_duel_or_raise", fake_get_duel)
    monkeypatch.setattr(flow_mod.helpers, "assert_duel_not_expired", lambda d: None)
    monkeypatch.setattr(flow_mod.helpers, "_get_allowed_stakes_from_duel", lambda d: [10])

    monkeypatch.setattr(flow_mod, "now_ts", lambda: 1000)
    monkeypatch.setattr(flow_mod, "add_duration", lambda ts, minutes=0, **k: ts + minutes * 60)

    # Conn transaction
    conn = FakeConn()
    monkeypatch.setattr(flow_mod, "get_conn", lambda: FakeConnCM(conn))

    # Transition status OK
    transition_calls = {}
    def fake_transition(*a, **k):
        transition_calls["k"] = k
        return True

    monkeypatch.setattr(flow_mod.duel_repo, "transition_status", fake_transition)

    # Payload baseline absent => xp_get_member appelé
    monkeypatch.setattr(flow_mod.helpers, "load_payload_any", lambda duel: {})  # no xp_baseline
    monkeypatch.setattr(flow_mod, "xp_get_member", lambda gid, uid, conn=None: (1000 if uid == 111 else 500,))

    monkeypatch.setattr(flow_mod.helpers, "dump_payload", lambda payload: "NEW_PAYLOAD_JSON")

    upd_payload_calls = {}
    monkeypatch.setattr(
        flow_mod.duel_repo,
        "update_payload_if_unchanged",
        lambda duel_id, old_json, new_json, conn=None: upd_payload_calls.setdefault(
            "args", (duel_id, old_json, new_json, conn)
        ),
    )

    # debit xp
    debit_calls = {}
    monkeypatch.setattr(
        flow_mod.helpers,
        "modify_xp_for_players",
        lambda gid, a, b, delta, conn=None: debit_calls.setdefault("args", (gid, a, b, delta, conn)),
    )

    monkeypatch.setattr(flow_mod.helpers, "build_snapshot", lambda *, duel_row, **k: {"id": duel_row["id"], "status": duel_row["status"]})

    out = flow_mod.accept_duel(1, user_id=222)

    assert out == {"id": 1, "status": constants.DUEL_STATUS_ACTIVE}
    assert transition_calls["k"]["conn"] is conn
    assert upd_payload_calls["args"][0] == 1
    assert debit_calls["args"] == (10, 111, 222, -10, conn)

# ------------------------------------------------------------
# refuse_duel
# ------------------------------------------------------------
def test_refuse_duel_rejects_not_player_b(monkeypatch):
    duel = _minimal_duel_row(id=1, status=constants.DUEL_STATUS_INVITED, player_b_id=222)
    monkeypatch.setattr(flow_mod.helpers, "get_duel_or_raise", lambda duel_id: duel)
    monkeypatch.setattr(flow_mod.helpers, "assert_duel_not_expired", lambda d: None)

    with pytest.raises(exc.NotAuthorizedPlayer):
        flow_mod.refuse_duel(1, user_id=999)

def test_refuse_duel_rejects_wrong_status(monkeypatch):
    duel = _minimal_duel_row(id=1, status=constants.DUEL_STATUS_CONFIG, player_b_id=222)
    monkeypatch.setattr(flow_mod.helpers, "get_duel_or_raise", lambda duel_id: duel)
    monkeypatch.setattr(flow_mod.helpers, "assert_duel_not_expired", lambda d: None)

    with pytest.raises(exc.DuelNotAcceptable):
        flow_mod.refuse_duel(1, user_id=222)

def test_refuse_duel_success_transitions_and_sets_finished_at(monkeypatch):
    duel_before = _minimal_duel_row(id=1, status=constants.DUEL_STATUS_INVITED, player_b_id=222)
    duel_after = _minimal_duel_row(id=1, status=constants.DUEL_STATUS_CANCELLED, player_b_id=222)

    seq = {"i": 0}

    def fake_get_duel(duel_id):
        seq["i"] += 1
        return duel_before if seq["i"] == 1 else duel_after

    monkeypatch.setattr(flow_mod.helpers, "get_duel_or_raise", fake_get_duel)
    monkeypatch.setattr(flow_mod.helpers, "assert_duel_not_expired", lambda d: None)

    conn = FakeConn()
    monkeypatch.setattr(flow_mod, "get_conn", lambda: FakeConnCM(conn))

    monkeypatch.setattr(flow_mod.duel_repo, "transition_status", lambda *a, **k: True)

    finished_calls = {}
    monkeypatch.setattr(flow_mod, "now_ts", lambda: 12345)
    monkeypatch.setattr(
        flow_mod.duel_repo,
        "update_duel_if_status",
        lambda duel_id, required_status, finished_at, conn=None, **k: finished_calls.setdefault(
            "args", (duel_id, required_status, finished_at, conn)
        ),
    )

    monkeypatch.setattr(flow_mod.helpers, "build_snapshot", lambda *, duel_row, **k: {"id": duel_row["id"], "status": duel_row["status"]})

    out = flow_mod.refuse_duel(1, user_id=222)

    assert out == {"id": 1, "status": constants.DUEL_STATUS_CANCELLED}
    assert finished_calls["args"] == (1, constants.DUEL_STATUS_CANCELLED, 12345, conn)