from __future__ import annotations

import eldoria.features.role.role_service as role_service_mod


def test_sr_match_delegates_to_repo(monkeypatch):
    svc = role_service_mod.RoleService()

    calls = {}

    def fake_sr_match(guild_id: int, channel_id: int, phrase: str):
        calls["args"] = (guild_id, channel_id, phrase)
        return 999

    monkeypatch.setattr(role_service_mod.secret_roles_repo, "sr_match", fake_sr_match)

    out = svc.sr_match(1, 2, "hello")

    assert out == 999
    assert calls["args"] == (1, 2, "hello")


def test_sr_list_messages_delegates_to_repo(monkeypatch):
    svc = role_service_mod.RoleService()

    def fake_list(guild_id: int, channel_id: int):
        assert (guild_id, channel_id) == (10, 20)
        return ["a", "b"]

    monkeypatch.setattr(role_service_mod.secret_roles_repo, "sr_list_messages", fake_list)

    assert svc.sr_list_messages(10, 20) == ["a", "b"]


def test_sr_upsert_delegates_to_repo(monkeypatch):
    svc = role_service_mod.RoleService()

    calls = {}

    def fake_upsert(guild_id: int, channel_id: int, phrase: str, role_id: int):
        calls["args"] = (guild_id, channel_id, phrase, role_id)
        return None

    monkeypatch.setattr(role_service_mod.secret_roles_repo, "sr_upsert", fake_upsert)

    out = svc.sr_upsert(1, 2, "secret", 777)

    assert out is None
    assert calls["args"] == (1, 2, "secret", 777)


def test_sr_delete_delegates_to_repo(monkeypatch):
    svc = role_service_mod.RoleService()

    calls = {}

    def fake_delete(guild_id: int, channel_id: int, phrase: str):
        calls["args"] = (guild_id, channel_id, phrase)
        return None

    monkeypatch.setattr(role_service_mod.secret_roles_repo, "sr_delete", fake_delete)

    out = svc.sr_delete(1, 2, "secret")

    assert out is None
    assert calls["args"] == (1, 2, "secret")


def test_sr_list_by_guild_grouped_delegates_to_repo(monkeypatch):
    svc = role_service_mod.RoleService()

    expected = [("general", {"hello": 123}), ("rules", {"yo": 456})]

    def fake_grouped(guild_id: int):
        assert guild_id == 42
        return expected

    monkeypatch.setattr(role_service_mod.secret_roles_repo, "sr_list_by_guild_grouped", fake_grouped)

    assert svc.sr_list_by_guild_grouped(42) == expected


def test_rr_upsert_delegates_to_repo(monkeypatch):
    svc = role_service_mod.RoleService()

    calls = {}

    def fake_upsert(guild_id: int, message_id: int, emoji: str, role_id: int):
        calls["args"] = (guild_id, message_id, emoji, role_id)
        return None

    monkeypatch.setattr(role_service_mod.reaction_roles_repo, "rr_upsert", fake_upsert)

    out = svc.rr_upsert(1, 999, "🔥", 1234)

    assert out is None
    assert calls["args"] == (1, 999, "🔥", 1234)


def test_rr_delete_delegates_to_repo(monkeypatch):
    svc = role_service_mod.RoleService()

    calls = {}

    def fake_delete(guild_id: int, message_id: int, emoji: str):
        calls["args"] = (guild_id, message_id, emoji)
        return None

    monkeypatch.setattr(role_service_mod.reaction_roles_repo, "rr_delete", fake_delete)

    out = svc.rr_delete(1, 999, "🔥")

    assert out is None
    assert calls["args"] == (1, 999, "🔥")


def test_rr_delete_message_delegates_to_repo(monkeypatch):
    svc = role_service_mod.RoleService()

    calls = {}

    def fake_delete_message(guild_id: int, message_id: int):
        calls["args"] = (guild_id, message_id)
        return None

    monkeypatch.setattr(role_service_mod.reaction_roles_repo, "rr_delete_message", fake_delete_message)

    out = svc.rr_delete_message(1, 999)

    assert out is None
    assert calls["args"] == (1, 999)


def test_rr_get_role_id_delegates_to_repo(monkeypatch):
    svc = role_service_mod.RoleService()

    def fake_get(guild_id: int, message_id: int, emoji: str):
        assert (guild_id, message_id, emoji) == (5, 6, "✅")
        return 321

    monkeypatch.setattr(role_service_mod.reaction_roles_repo, "rr_get_role_id", fake_get)

    assert svc.rr_get_role_id(5, 6, "✅") == 321


def test_rr_list_by_message_delegates_to_repo(monkeypatch):
    svc = role_service_mod.RoleService()

    expected = {"✅": 1, "❌": 2}

    def fake_list(guild_id: int, message_id: int):
        assert (guild_id, message_id) == (7, 8)
        return expected

    monkeypatch.setattr(role_service_mod.reaction_roles_repo, "rr_list_by_message", fake_list)

    assert svc.rr_list_by_message(7, 8) == expected


def test_rr_list_by_guild_grouped_delegates_to_repo(monkeypatch):
    svc = role_service_mod.RoleService()

    expected = [("msg:123", {"✅": 1}), ("msg:456", {"🔥": 2})]

    def fake_grouped(guild_id: int):
        assert guild_id == 99
        return expected

    monkeypatch.setattr(role_service_mod.reaction_roles_repo, "rr_list_by_guild_grouped", fake_grouped)

    assert svc.rr_list_by_guild_grouped(99) == expected
