from __future__ import annotations

import eldoria.features.duel.duel_service as service_mod


def test_new_duel_delegates(monkeypatch):
    svc = service_mod.DuelService()

    called = {}

    def fake_new_duel(guild_id, channel_id, player_a_id, player_b_id):
        called["args"] = (guild_id, channel_id, player_a_id, player_b_id)
        return {"ok": "new"}

    monkeypatch.setattr(service_mod.flow, "new_duel", fake_new_duel)

    out = svc.new_duel(1, 2, 3, 4)

    assert called["args"] == (1, 2, 3, 4)
    assert out == {"ok": "new"}


def test_configure_game_type_delegates(monkeypatch):
    svc = service_mod.DuelService()

    def fake_configure(duel_id, game_type):
        return {"duel_id": duel_id, "game_type": game_type}

    monkeypatch.setattr(service_mod.flow, "configure_game_type", fake_configure)

    assert svc.configure_game_type(10, "RPS") == {"duel_id": 10, "game_type": "RPS"}


def test_configure_stake_xp_delegates(monkeypatch):
    svc = service_mod.DuelService()

    monkeypatch.setattr(service_mod.flow, "configure_stake_xp", lambda duel_id, stake_xp: {"id": duel_id, "stake": stake_xp})

    assert svc.configure_stake_xp(10, 50) == {"id": 10, "stake": 50}


def test_send_invite_delegates(monkeypatch):
    svc = service_mod.DuelService()

    monkeypatch.setattr(service_mod.flow, "send_invite", lambda duel_id, message_id: {"id": duel_id, "msg": message_id})

    assert svc.send_invite(10, 999) == {"id": 10, "msg": 999}


def test_accept_duel_delegates(monkeypatch):
    svc = service_mod.DuelService()

    monkeypatch.setattr(service_mod.flow, "accept_duel", lambda duel_id, user_id: {"id": duel_id, "user": user_id, "status": "ACCEPTED"})

    assert svc.accept_duel(10, 42) == {"id": 10, "user": 42, "status": "ACCEPTED"}


def test_refuse_duel_delegates(monkeypatch):
    svc = service_mod.DuelService()

    monkeypatch.setattr(service_mod.flow, "refuse_duel", lambda duel_id, user_id: {"id": duel_id, "user": user_id, "status": "CANCELLED"})

    assert svc.refuse_duel(10, 42) == {"id": 10, "user": 42, "status": "CANCELLED"}


def test_play_game_action_delegates(monkeypatch):
    svc = service_mod.DuelService()

    action = {"move": "rock"}
    monkeypatch.setattr(service_mod.gameplay, "play_game_action", lambda duel_id, user_id, action: {"id": duel_id, "user": user_id, "action": action})

    assert svc.play_game_action(10, 42, action) == {"id": 10, "user": 42, "action": action}


def test_cancel_expired_duels_delegates(monkeypatch):
    svc = service_mod.DuelService()

    monkeypatch.setattr(service_mod.maintenance, "cancel_expired_duels", lambda: [{"id": 1}, {"id": 2}])

    assert svc.cancel_expired_duels() == [{"id": 1}, {"id": 2}]


def test_cleanup_old_duels_delegates(monkeypatch):
    svc = service_mod.DuelService()

    called = {"now_ts": None}

    def fake_cleanup(now_ts):
        called["now_ts"] = now_ts
        return None

    monkeypatch.setattr(service_mod.maintenance, "cleanup_old_duels", fake_cleanup)

    assert svc.cleanup_old_duels(1234567890) is None
    assert called["now_ts"] == 1234567890


def test_get_allowed_stakes_delegates(monkeypatch):
    svc = service_mod.DuelService()

    monkeypatch.setattr(service_mod.helpers, "get_allowed_stakes", lambda duel_id: [10, 20])

    assert svc.get_allowed_stakes(10) == [10, 20]
