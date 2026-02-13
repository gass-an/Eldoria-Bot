import pytest

import eldoria.features.welcome._internal.welcome_picker as picker_mod


def test_pick_welcome_message_returns_fallback_when_pool_empty(monkeypatch):
    # packs absent / invalide => pool vide => fallback
    data = {"packs": []}

    title, msg, emojis, key = picker_mod.pick_welcome_message(
        data=data,
        user="Bob",
        server="Eldoria",
        recent_keys=[],
        recent_limit=10,
    )

    assert title == "👋 Bienvenue"
    assert msg == "👋 Bienvenue Bob !"
    assert emojis == ["👋"]
    assert key == "fallback"


def test_pick_welcome_message_builds_pool_from_valid_packs_and_replaces_placeholders(monkeypatch):
    data = {
        "packs": [
            {
                "title": "Bienvenue !",
                "messages": {
                    "k1": "Salut {user} sur {server}",
                },
                "emojis": ["🎉", "👋", "   ", 123],
            }
        ]
    }

    # deterministic choice + sample
    monkeypatch.setattr(picker_mod.random, "choice", lambda seq: "k1")
    monkeypatch.setattr(picker_mod.random, "sample", lambda seq, k: seq[:k])

    title, msg, emojis, key = picker_mod.pick_welcome_message(
        data=data,
        user="Bob",
        server="Eldoria",
        recent_keys=[],
        recent_limit=10,
    )

    assert title == "Bienvenue !"
    assert msg == "Salut Bob sur Eldoria"
    assert key == "k1"
    # max 2, filtrés et non vides
    assert emojis == ["🎉", "👋"]


def test_pick_welcome_message_filters_invalid_pack_shapes(monkeypatch):
    # packs contient tout et n'importe quoi, seul le pack valide compte
    data = {
        "packs": [
            "not a dict",
            {"title": "", "messages": {"k": "x"}},  # title vide -> ignore
            {"title": "Ok", "messages": {}},        # messages vide -> ignore
            {"title": "Valid", "messages": {"k1": "Yo {user}"}, "emojis": []},
        ]
    }

    monkeypatch.setattr(picker_mod.random, "choice", lambda seq: "k1")
    # emojis vide => fallback emoji ["👋"], donc sample ne doit pas être appelé
    monkeypatch.setattr(
        picker_mod.random,
        "sample",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not sample")),
    )

    title, msg, emojis, key = picker_mod.pick_welcome_message(
        data=data,
        user="Bob",
        server="Eldoria",
        recent_keys=[],
        recent_limit=10,
    )

    assert title == "Valid"
    assert msg == "Yo Bob"
    assert emojis == ["👋"]
    assert key == "k1"


def test_pick_welcome_message_excludes_recent_keys_when_possible(monkeypatch):
    data = {
        "packs": [
            {
                "title": "T",
                "messages": {"k1": "M1", "k2": "M2", "k3": "M3"},
                "emojis": ["🎉", "🔥"],
            }
        ]
    }

    captured = {}

    def fake_choice(seq):
        # on vérifie que les keys récentes sont exclues
        captured["available"] = list(seq)
        return seq[0]

    monkeypatch.setattr(picker_mod.random, "choice", fake_choice)
    monkeypatch.setattr(picker_mod.random, "sample", lambda seq, k: seq[:k])

    title, msg, emojis, key = picker_mod.pick_welcome_message(
        data=data,
        user="Bob",
        server="Eldoria",
        recent_keys=["k1", "k2"],   # récents
        recent_limit=2,
    )

    assert set(captured["available"]) == {"k3"}  # k1,k2 exclus
    assert key == "k3"
    assert title == "T"
    assert msg == "M3"
    assert emojis == ["🎉", "🔥"]


def test_pick_welcome_message_when_all_keys_recent_falls_back_to_full_pool(monkeypatch):
    data = {
        "packs": [
            {
                "title": "T",
                "messages": {"k1": "M1", "k2": "M2"},
                "emojis": ["🎉", "🔥"],
            }
        ]
    }

    captured = {}

    def fake_choice(seq):
        captured["available"] = list(seq)
        return "k2"

    monkeypatch.setattr(picker_mod.random, "choice", fake_choice)
    monkeypatch.setattr(picker_mod.random, "sample", lambda seq, k: seq[:k])

    title, msg, emojis, key = picker_mod.pick_welcome_message(
        data=data,
        user="Bob",
        server="Eldoria",
        recent_keys=["k1", "k2"],
        recent_limit=10,
    )

    # tous récents => on retombe sur le pool complet
    assert set(captured["available"]) == {"k1", "k2"}
    assert key == "k2"
    assert msg == "M2"


@pytest.mark.parametrize("recent_limit", [-5, -1])
def test_pick_welcome_message_negative_recent_limit_treated_as_zero(monkeypatch, recent_limit):
    data = {
        "packs": [
            {
                "title": "T",
                "messages": {"k1": "M1", "k2": "M2"},
                "emojis": ["🎉", "🔥"],
            }
        ]
    }

    captured = {}

    def fake_choice(seq):
        captured["available"] = list(seq)
        return "k1"

    monkeypatch.setattr(picker_mod.random, "choice", fake_choice)
    monkeypatch.setattr(picker_mod.random, "sample", lambda seq, k: seq[:k])

    title, msg, emojis, key = picker_mod.pick_welcome_message(
        data=data,
        user="Bob",
        server="Eldoria",
        recent_keys=["k1"],   # ne doit PAS exclure (limit => 0)
        recent_limit=recent_limit,
    )

    assert set(captured["available"]) == {"k1", "k2"}
    assert key == "k1"


def test_pick_welcome_message_limits_emojis_to_two(monkeypatch):
    data = {
        "packs": [
            {
                "title": "T",
                "messages": {"k1": "Hello"},
                "emojis": ["1", "2", "3", "4"],
            }
        ]
    }

    monkeypatch.setattr(picker_mod.random, "choice", lambda seq: "k1")

    captured = {}
    def fake_sample(seq, k):
        captured["k"] = k
        # renvoie exactement k éléments
        return seq[:k]

    monkeypatch.setattr(picker_mod.random, "sample", fake_sample)

    title, msg, emojis, key = picker_mod.pick_welcome_message(
        data=data,
        user="Bob",
        server="Eldoria",
        recent_keys=[],
        recent_limit=10,
    )

    assert captured["k"] == 2
    assert emojis == ["1", "2"]
    assert msg == "Hello"
    assert key == "k1"
