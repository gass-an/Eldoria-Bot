from __future__ import annotations

import eldoria.features.duel._internal.maintenance as m_mod
from eldoria.exceptions.duel_exceptions import DuelAlreadyHandled
from eldoria.features.duel import constants


class FakeConn:
    pass

# pytest = pytest  # silence unused import

class FakeConnCtx:
    def __init__(self, conn=None):
        self.conn = conn or FakeConn()

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False


def _duel_row(**overrides):
    base = {
        "duel_id": 1,
        "guild_id": 10,
        "channel_id": 20,
        "message_id": 30,
        "player_a_id": 111,
        "player_b_id": 222,
        "stake_xp": 10,
        "game_type": "RPS",
        "status": constants.DUEL_STATUS_CONFIG,
    }
    base.update(overrides)
    return base


# ------------------------------------------------------------
# cancel_expired_duels - expiration "normale"
# ------------------------------------------------------------
def test_cancel_expired_duels_returns_empty_when_none(monkeypatch):
    monkeypatch.setattr(m_mod, "now_ts", lambda: 1000)
    monkeypatch.setattr(m_mod.duel_repo, "list_expired_duels", lambda ts: [])
    assert m_mod.cancel_expired_duels() == []


def test_cancel_expired_duels_skips_when_transition_fails(monkeypatch):
    monkeypatch.setattr(m_mod, "now_ts", lambda: 1000)
    duel = _duel_row(status=constants.DUEL_STATUS_CONFIG)
    monkeypatch.setattr(m_mod.duel_repo, "list_expired_duels", lambda ts: [duel])

    # transaction
    conn = FakeConn()
    monkeypatch.setattr(m_mod, "get_conn", lambda: FakeConnCtx(conn))

    monkeypatch.setattr(m_mod.duel_repo, "transition_status", lambda *a, **k: False)

    # ne doit pas appeler update/modify
    called = {"update": 0, "modify": 0}
    monkeypatch.setattr(m_mod.duel_repo, "update_duel_if_status", lambda *a, **k: called.__setitem__("update", called["update"] + 1))
    monkeypatch.setattr(m_mod.helpers, "modify_xp_for_players", lambda *a, **k: called.__setitem__("modify", called["modify"] + 1))

    out = m_mod.cancel_expired_duels()
    assert out == []
    assert called["update"] == 0
    assert called["modify"] == 0


def test_cancel_expired_duels_expires_config_without_refund(monkeypatch):
    monkeypatch.setattr(m_mod, "now_ts", lambda: 1000)
    duel = _duel_row(status=constants.DUEL_STATUS_CONFIG)
    monkeypatch.setattr(m_mod.duel_repo, "list_expired_duels", lambda ts: [duel])

    conn = FakeConn()
    monkeypatch.setattr(m_mod, "get_conn", lambda: FakeConnCtx(conn))

    monkeypatch.setattr(m_mod.duel_repo, "transition_status", lambda *a, **k: True)
    monkeypatch.setattr(m_mod.duel_repo, "update_duel_if_status", lambda *a, **k: True)

    refund_called = {"n": 0}
    monkeypatch.setattr(m_mod.helpers, "modify_xp_for_players", lambda *a, **k: refund_called.__setitem__("n", refund_called["n"] + 1))

    out = m_mod.cancel_expired_duels()

    assert len(out) == 1
    assert out[0]["previous_status"] == constants.DUEL_STATUS_CONFIG
    assert out[0]["xp_changed"] is False
    assert refund_called["n"] == 0


def test_cancel_expired_duels_expires_invited_without_refund(monkeypatch):
    monkeypatch.setattr(m_mod, "now_ts", lambda: 1000)
    duel = _duel_row(status=constants.DUEL_STATUS_INVITED)
    monkeypatch.setattr(m_mod.duel_repo, "list_expired_duels", lambda ts: [duel])

    conn = FakeConn()
    monkeypatch.setattr(m_mod, "get_conn", lambda: FakeConnCtx(conn))

    monkeypatch.setattr(m_mod.duel_repo, "transition_status", lambda *a, **k: True)
    monkeypatch.setattr(m_mod.duel_repo, "update_duel_if_status", lambda *a, **k: True)

    refund_called = {"n": 0}
    monkeypatch.setattr(m_mod.helpers, "modify_xp_for_players", lambda *a, **k: refund_called.__setitem__("n", refund_called["n"] + 1))

    out = m_mod.cancel_expired_duels()

    assert len(out) == 1
    assert out[0]["previous_status"] == constants.DUEL_STATUS_INVITED
    assert out[0]["xp_changed"] is False
    assert refund_called["n"] == 0


def test_cancel_expired_duels_expires_active_and_refunds(monkeypatch):
    monkeypatch.setattr(m_mod, "now_ts", lambda: 1000)
    duel = _duel_row(status=constants.DUEL_STATUS_ACTIVE, stake_xp=10)
    monkeypatch.setattr(m_mod.duel_repo, "list_expired_duels", lambda ts: [duel])

    conn = FakeConn()
    monkeypatch.setattr(m_mod, "get_conn", lambda: FakeConnCtx(conn))

    monkeypatch.setattr(m_mod.duel_repo, "transition_status", lambda *a, **k: True)
    monkeypatch.setattr(m_mod.duel_repo, "update_duel_if_status", lambda *a, **k: True)

    refund_calls = {}
    monkeypatch.setattr(
        m_mod.helpers,
        "modify_xp_for_players",
        lambda gid, a, b, stake, conn=None: refund_calls.setdefault("args", (gid, a, b, stake, conn)),
    )

    out = m_mod.cancel_expired_duels()

    assert len(out) == 1
    assert out[0]["previous_status"] == constants.DUEL_STATUS_ACTIVE
    assert out[0]["xp_changed"] is True
    assert refund_calls["args"] == (10, 111, 222, 10, conn)


# ------------------------------------------------------------
# cancel_expired_duels - cas spécial ACTIVE "terminable" => auto-finish
# ------------------------------------------------------------

def test_cancel_expired_duels_active_complete_auto_finishes(monkeypatch):
    monkeypatch.setattr(m_mod, "now_ts", lambda: 1000)

    duel = _duel_row(status=constants.DUEL_STATUS_ACTIVE, duel_id=1, message_id=30)
    monkeypatch.setattr(m_mod.duel_repo, "list_expired_duels", lambda ts: [duel])

    fresh = _duel_row(status=constants.DUEL_STATUS_ACTIVE, duel_id=1, message_id=30)
    monkeypatch.setattr(m_mod.helpers, "get_duel_or_raise", lambda duel_id: fresh)

    monkeypatch.setattr(m_mod, "is_duel_complete_for_game", lambda d: True)
    monkeypatch.setattr(m_mod, "resolve_duel_for_game", lambda d: constants.DUEL_RESULT_WIN_A)

    finish_calls = {}
    def fake_finish(duel_id, result, ignore_expired=False):
        finish_calls["args"] = (duel_id, result, ignore_expired)
        return True

    monkeypatch.setattr(m_mod.helpers, "finish_duel", fake_finish)

    # NE DOIT PAS passer par transition_status dans le cas auto-finish réussi
    conn = FakeConn()
    monkeypatch.setattr(m_mod, "get_conn", lambda: FakeConnCtx(conn))
    monkeypatch.setattr(m_mod.duel_repo, "transition_status", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not transition")))
    monkeypatch.setattr(m_mod.duel_repo, "update_duel_if_status", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not update")))

    out = m_mod.cancel_expired_duels()

    assert finish_calls["args"] == (1, constants.DUEL_RESULT_WIN_A, True)
    assert len(out) == 1
    item = out[0]
    assert item["duel_id"] == 1
    assert item["previous_status"] == constants.DUEL_STATUS_ACTIVE
    assert item["xp_changed"] is True
    assert item["auto_finished"] is True
    assert item["sync_roles_user_ids"] == [fresh["player_a_id"], fresh["player_b_id"]]


def test_cancel_expired_duels_active_complete_but_finish_already_handled_results_in_no_output(monkeypatch):
    monkeypatch.setattr(m_mod, "now_ts", lambda: 1000)

    duel = _duel_row(status=constants.DUEL_STATUS_ACTIVE, duel_id=1)
    monkeypatch.setattr(m_mod.duel_repo, "list_expired_duels", lambda ts: [duel])

    fresh = _duel_row(status=constants.DUEL_STATUS_ACTIVE, duel_id=1)
    monkeypatch.setattr(m_mod.helpers, "get_duel_or_raise", lambda duel_id: fresh)

    monkeypatch.setattr(m_mod, "is_duel_complete_for_game", lambda d: True)
    monkeypatch.setattr(m_mod, "resolve_duel_for_game", lambda d: constants.DUEL_RESULT_DRAW)

    def fake_finish(duel_id, result, ignore_expired=False):
        raise DuelAlreadyHandled(duel_id, constants.DUEL_STATUS_ACTIVE)

    monkeypatch.setattr(m_mod.helpers, "finish_duel", fake_finish)

    # Ces appels ne doivent PAS arriver (car continue)
    monkeypatch.setattr(m_mod, "get_conn", lambda: (_ for _ in ()).throw(AssertionError("should not open conn")))
    monkeypatch.setattr(m_mod.duel_repo, "transition_status", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not transition")))
    monkeypatch.setattr(m_mod.duel_repo, "update_duel_if_status", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not update")))

    refund_called = {"n": 0}
    monkeypatch.setattr(
        m_mod.helpers,
        "modify_xp_for_players",
        lambda *a, **k: refund_called.__setitem__("n", refund_called["n"] + 1),
    )

    out = m_mod.cancel_expired_duels()

    assert out == []
    assert refund_called["n"] == 0


# ------------------------------------------------------------
# cleanup_old_duels
# ------------------------------------------------------------

def test_cleanup_old_duels_calls_repo_with_cutoffs(monkeypatch):
    calls = {}

    def fake_cleanup_duels(*, cutoff_short, cutoff_finished):
        calls["cutoff_short"] = cutoff_short
        calls["cutoff_finished"] = cutoff_finished

    monkeypatch.setattr(m_mod.duel_repo, "cleanup_duels", fake_cleanup_duels)

    now = 10_000_000
    m_mod.cleanup_old_duels(now)

    assert calls["cutoff_short"] == now - (constants.KEEP_EXPIRED_DAYS * 86400)
    assert calls["cutoff_finished"] == now - (constants.KEEP_FINISHED_DAYS * 86400)
