import eldoria.features.welcome._internal.welcome_getter as getter_mod

# ------------------------------------------------------------
# Cas normal : tout s'enchaîne correctement
# ------------------------------------------------------------

def test_get_welcome_message_full_flow(monkeypatch):
    calls = {}

    # 1) JSON loader
    monkeypatch.setattr(
        getter_mod,
        "load_welcome_json",
        lambda: {"messages": ["dummy"]},
    )

    # 2) DB recent keys
    def fake_recent(guild_id: int, *, limit: int):
        calls["recent"] = (guild_id, limit)
        return ["k2", "k1"]

    monkeypatch.setattr(
        getter_mod.welcome_message_repo,
        "wm_get_recent_message_keys",
        fake_recent,
    )

    # 3) picker
    def fake_picker(*, data, user, server, recent_keys, recent_limit):
        calls["picker"] = (data, user, server, recent_keys, recent_limit)
        return ("Title", "Message", ["🎉"], "k3")

    monkeypatch.setattr(getter_mod, "pick_welcome_message", fake_picker)

    # 4) record
    def fake_record(guild_id, key, *, keep):
        calls["record"] = (guild_id, key, keep)

    monkeypatch.setattr(
        getter_mod.welcome_message_repo,
        "wm_record_welcome_message",
        fake_record,
    )

    out = getter_mod.get_welcome_message(
        1,
        user="Bob",
        server="Eldoria",
        recent_limit=5,
    )

    assert out == ("Title", "Message", ["🎉"])

    assert calls["recent"] == (1, 5)
    assert calls["picker"][1:] == ("Bob", "Eldoria", ["k2", "k1"], 5)
    assert calls["record"] == (1, "k3", 5)


# ------------------------------------------------------------
# recent_limit = 0 => pas de lecture DB
# ------------------------------------------------------------

def test_get_welcome_message_no_recent_lookup_when_limit_zero(monkeypatch):
    monkeypatch.setattr(getter_mod, "load_welcome_json", lambda: {})

    # Si appelé => fail
    monkeypatch.setattr(
        getter_mod.welcome_message_repo,
        "wm_get_recent_message_keys",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not be called")),
    )

    monkeypatch.setattr(
        getter_mod,
        "pick_welcome_message",
        lambda **kwargs: ("T", "M", [], "k1"),
    )

    monkeypatch.setattr(
        getter_mod.welcome_message_repo,
        "wm_record_welcome_message",
        lambda *a, **k: None,
    )

    out = getter_mod.get_welcome_message(
        1,
        user="Bob",
        server="Eldoria",
        recent_limit=0,
    )

    assert out == ("T", "M", [])


# ------------------------------------------------------------
# chosen_key = None => ne persiste pas
# ------------------------------------------------------------

def test_get_welcome_message_does_not_record_when_key_none(monkeypatch):
    monkeypatch.setattr(getter_mod, "load_welcome_json", lambda: {})
    monkeypatch.setattr(
        getter_mod.welcome_message_repo,
        "wm_get_recent_message_keys",
        lambda *a, **k: [],
    )

    monkeypatch.setattr(
        getter_mod,
        "pick_welcome_message",
        lambda **kwargs: ("T", "M", [], None),
    )

    monkeypatch.setattr(
        getter_mod.welcome_message_repo,
        "wm_record_welcome_message",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not record")),
    )

    out = getter_mod.get_welcome_message(
        1,
        user="Bob",
        server="Eldoria",
    )

    assert out == ("T", "M", [])


# ------------------------------------------------------------
# chosen_key = "fallback" => ne persiste pas
# ------------------------------------------------------------

def test_get_welcome_message_does_not_record_fallback(monkeypatch):
    monkeypatch.setattr(getter_mod, "load_welcome_json", lambda: {})
    monkeypatch.setattr(
        getter_mod.welcome_message_repo,
        "wm_get_recent_message_keys",
        lambda *a, **k: [],
    )

    monkeypatch.setattr(
        getter_mod,
        "pick_welcome_message",
        lambda **kwargs: ("T", "M", [], "fallback"),
    )

    monkeypatch.setattr(
        getter_mod.welcome_message_repo,
        "wm_record_welcome_message",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not record")),
    )

    out = getter_mod.get_welcome_message(
        1,
        user="Bob",
        server="Eldoria",
    )

    assert out == ("T", "M", [])
