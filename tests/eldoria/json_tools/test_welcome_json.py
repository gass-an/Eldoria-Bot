# tests/json_tools/test_welcomeJson.py
import io
import json
import builtins

import eldoria.json_tools.welcome_json as welcome_mod
from eldoria.json_tools.welcome_json import load_welcome_json, getWelcomeMessage


def test_load_welcome_json_file_not_found(monkeypatch):
    def _open(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(builtins, "open", _open)
    assert load_welcome_json() == {}


def test_load_welcome_json_valid(monkeypatch):
    data = {"packs": []}

    def _open(*args, **kwargs):
        return io.StringIO(json.dumps(data))

    monkeypatch.setattr(builtins, "open", _open)
    assert load_welcome_json() == data


def test_getWelcomeMessage_fallback_when_no_pool(monkeypatch):
    # Force load_welcome_json à renvoyer un format vide
    monkeypatch.setattr(welcome_mod, "load_welcome_json", lambda: {})

    title, msg, emojis = getWelcomeMessage(
        123,
        user="Bob",
        server="Eldoria",
        recent_limit=10,
    )

    assert title == "👋 Bienvenue"
    assert msg == "👋 Bienvenue Bob !"
    assert emojis == ["👋"]


def test_getWelcomeMessage_avoids_recent_keys_and_formats_placeholders(monkeypatch):
    # JSON de test : 1 pack avec 2 messages
    welcome_data = {
        "packs": [
            {
                "title": "Bienvenue",
                "messages": {
                    "w01": "Salut {user} sur {server}",
                    "w02": "Hello {user}, bienvenue sur {server}",
                },
                "emojis": ["👋", "🔥", "✨"],
            }
        ]
    }

    monkeypatch.setattr(welcome_mod, "load_welcome_json", lambda: welcome_data)

    # DB mocks
    recorded = []

    def fake_recent(guild_id, limit=10):
        assert guild_id == 123
        assert limit == 10
        return ["w01"]  # w01 est récent → on veut forcer w02

    def fake_record(guild_id, key, keep=10):
        recorded.append((guild_id, key, keep))

    monkeypatch.setattr(welcome_mod.database_manager, "wm_get_recent_message_keys", fake_recent)
    monkeypatch.setattr(welcome_mod.database_manager, "wm_record_welcome_message", fake_record)

    # random mocks
    def fake_choice(seq):
        # seq doit contenir uniquement la clé non-récente
        assert seq == ["w02"]
        return "w02"

    def fake_sample(population, k):
        # le code prend min(len(emojis), 2)
        assert k == 2
        return population[:k]

    monkeypatch.setattr(welcome_mod.random, "choice", fake_choice)
    monkeypatch.setattr(welcome_mod.random, "sample", fake_sample)

    title, msg, emojis = getWelcomeMessage(
        123,
        user="Alice",
        server="Eldoria",
        recent_limit=10,
    )

    assert title == "Bienvenue"
    assert msg == "Hello Alice, bienvenue sur Eldoria"
    assert emojis == ["👋", "🔥"]
    assert recorded == [(123, "w02", 10)]


def test_getWelcomeMessage_all_recent_allows_repeat(monkeypatch):
    welcome_data = {
        "packs": [
            {
                "title": "Bienvenue",
                "messages": {"w01": "Yo {user}", "w02": "Coucou {user}"},
                "emojis": ["👋"],
            }
        ]
    }
    monkeypatch.setattr(welcome_mod, "load_welcome_json", lambda: welcome_data)

    # Tout est "recent" → il doit retomber sur l'ensemble complet (autorise répétition)
    monkeypatch.setattr(
        welcome_mod.database_manager,
        "wm_get_recent_message_keys",
        lambda guild_id, limit=10: ["w01", "w02"],
    )

    recorded = []
    monkeypatch.setattr(
        welcome_mod.database_manager,
        "wm_record_welcome_message",
        lambda guild_id, key, keep=10: recorded.append((guild_id, key, keep)),
    )

    def fake_choice(seq):
        # Comme tout est recent, seq doit contenir les 2 clés
        assert set(seq) == {"w01", "w02"}
        return seq[0]

    monkeypatch.setattr(welcome_mod.random, "choice", fake_choice)
    monkeypatch.setattr(welcome_mod.random, "sample", lambda pop, k: pop[:k])

    title, msg, emojis = getWelcomeMessage(
        999,
        user="Zed",
        server="Srv",
        recent_limit=10,
    )

    assert title == "Bienvenue"
    assert "Zed" in msg
    assert recorded and recorded[0][0] == 999
