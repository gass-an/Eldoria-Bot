import eldoria.features.welcome.welcome_service as svc_mod

# --------------------------
# Config
# --------------------------

def test_ensure_defaults_delegates_to_repo(monkeypatch):
    calls = {}

    def fake_ensure_defaults(guild_id: int, *, enabled: bool = False, channel_id: int = 0):
        calls["args"] = (guild_id, enabled, channel_id)
        return None

    monkeypatch.setattr(svc_mod.welcome_message_repo, "wm_ensure_defaults", fake_ensure_defaults)

    svc = svc_mod.WelcomeService()
    assert svc.ensure_defaults(1) is None
    assert calls["args"] == (1, False, 0)

    assert svc.ensure_defaults(2, enabled=True, channel_id=123) is None
    assert calls["args"] == (2, True, 123)


def test_get_config_delegates_to_repo(monkeypatch):
    calls = {}
    expected = {"enabled": True, "channel_id": 999}

    def fake_get_config(guild_id: int):
        calls["args"] = (guild_id,)
        return expected

    monkeypatch.setattr(svc_mod.welcome_message_repo, "wm_get_config", fake_get_config)

    svc = svc_mod.WelcomeService()
    assert svc.get_config(10) == expected
    assert calls["args"] == (10,)


def test_set_config_delegates_to_repo(monkeypatch):
    calls = {}

    def fake_set_config(guild_id: int, *, enabled=None, channel_id=None):
        calls["args"] = (guild_id, enabled, channel_id)
        return None

    monkeypatch.setattr(svc_mod.welcome_message_repo, "wm_set_config", fake_set_config)

    svc = svc_mod.WelcomeService()
    assert svc.set_config(1, enabled=True) is None
    assert calls["args"] == (1, True, None)

    assert svc.set_config(2, channel_id=123) is None
    assert calls["args"] == (2, None, 123)

    assert svc.set_config(3, enabled=False, channel_id=456) is None
    assert calls["args"] == (3, False, 456)


def test_set_enabled_delegates_to_repo(monkeypatch):
    calls = {}

    def fake_set_enabled(guild_id: int, enabled: bool):
        calls["args"] = (guild_id, enabled)
        return None

    monkeypatch.setattr(svc_mod.welcome_message_repo, "wm_set_enabled", fake_set_enabled)

    svc = svc_mod.WelcomeService()
    assert svc.set_enabled(1, True) is None
    assert calls["args"] == (1, True)


def test_set_channel_id_delegates_to_repo(monkeypatch):
    calls = {}

    def fake_set_channel_id(guild_id: int, channel_id: int):
        calls["args"] = (guild_id, channel_id)
        return None

    monkeypatch.setattr(svc_mod.welcome_message_repo, "wm_set_channel_id", fake_set_channel_id)

    svc = svc_mod.WelcomeService()
    assert svc.set_channel_id(1, 999) is None
    assert calls["args"] == (1, 999)


def test_is_enabled_delegates_to_repo(monkeypatch):
    calls = {}

    def fake_is_enabled(guild_id: int):
        calls["args"] = (guild_id,)
        return True

    monkeypatch.setattr(svc_mod.welcome_message_repo, "wm_is_enabled", fake_is_enabled)

    svc = svc_mod.WelcomeService()
    assert svc.is_enabled(1) is True
    assert calls["args"] == (1,)


def test_get_channel_id_delegates_to_repo(monkeypatch):
    calls = {}

    def fake_get_channel_id(guild_id: int):
        calls["args"] = (guild_id,)
        return 123

    monkeypatch.setattr(svc_mod.welcome_message_repo, "wm_get_channel_id", fake_get_channel_id)

    svc = svc_mod.WelcomeService()
    assert svc.get_channel_id(1) == 123
    assert calls["args"] == (1,)


def test_delete_config_delegates_to_repo(monkeypatch):
    calls = {}

    def fake_delete_config(guild_id: int):
        calls["args"] = (guild_id,)
        return None

    monkeypatch.setattr(svc_mod.welcome_message_repo, "wm_delete_config", fake_delete_config)

    svc = svc_mod.WelcomeService()
    assert svc.delete_config(1) is None
    assert calls["args"] == (1,)


# --------------------------
# Historique anti-répétition
# --------------------------

def test_get_recent_message_keys_delegates_to_repo(monkeypatch):
    calls = {}
    expected = ["k3", "k2", "k1"]

    def fake_get_recent(guild_id: int, *, limit: int = 10):
        calls["args"] = (guild_id, limit)
        return expected

    monkeypatch.setattr(
        svc_mod.welcome_message_repo,
        "wm_get_recent_message_keys",
        fake_get_recent,
    )

    svc = svc_mod.WelcomeService()
    assert svc.get_recent_message_keys(1) == expected
    assert calls["args"] == (1, 10)

    assert svc.get_recent_message_keys(2, limit=5) == expected
    assert calls["args"] == (2, 5)


def test_record_welcome_message_delegates_to_repo(monkeypatch):
    calls = {}

    def fake_record(guild_id: int, message_key: str, *, used_at=None, keep: int = 10):
        calls["args"] = (guild_id, message_key, used_at, keep)
        return None

    monkeypatch.setattr(
        svc_mod.welcome_message_repo,
        "wm_record_welcome_message",
        fake_record,
    )

    svc = svc_mod.WelcomeService()
    assert svc.record_welcome_message(1, "k1") is None
    assert calls["args"] == (1, "k1", None, 10)

    assert svc.record_welcome_message(2, "k2", used_at=123456, keep=3) is None
    assert calls["args"] == (2, "k2", 123456, 3)


# --------------------------
# Message welcome (getter)
# --------------------------

def test_get_welcome_message_delegates_to_getter(monkeypatch):
    calls = {}
    expected = ("Title", "Body", ["k1", "k0"])

    def fake_get_welcome_message(*, guild_id: int, user: str, server: str, recent_limit: int = 10):
        calls["args"] = (guild_id, user, server, recent_limit)
        return expected

    monkeypatch.setattr(svc_mod.welcome_getter, "get_welcome_message", fake_get_welcome_message)

    svc = svc_mod.WelcomeService()
    out = svc.get_welcome_message(1, user="Bob", server="Eldoria", recent_limit=7)

    assert out == expected
    assert calls["args"] == (1, "Bob", "Eldoria", 7)
