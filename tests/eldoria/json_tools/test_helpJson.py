# tests/json_tools/test_helpJson.py
import io
import json
import builtins

from eldoria.json_tools.helpJson import load_help_json, load_help_config


def test_load_help_json_file_not_found(monkeypatch):
    def _open(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(builtins, "open", _open)
    assert load_help_json() == {}


def test_load_help_json_valid(monkeypatch):
    data = {"ok": True}

    def _open(*args, **kwargs):
        return io.StringIO(json.dumps(data))

    monkeypatch.setattr(builtins, "open", _open)
    assert load_help_json() == data


def test_load_help_config_structured_format(monkeypatch):
    # Ton format structuré réel :
    # {"categories": {"Nom": {"description": "...", "commands": {"cmd": "desc"}}}}
    data = {
        "categories": {
            "Utilitaires": {
                "description": "Commandes utiles",
                "commands": {
                    "ping": "Vérifie la latence",
                    "help": "Affiche l'aide",
                },
            },
            "Divers": {
                "description": "Autres commandes",
                "commands": {"foo": "bar"},
            },
        }
    }

    def _open(*args, **kwargs):
        return io.StringIO(json.dumps(data))

    monkeypatch.setattr(builtins, "open", _open)

    help_infos, categories, cat_desc = load_help_config()

    assert help_infos == {
        "ping": "Vérifie la latence",
        "help": "Affiche l'aide",
        "foo": "bar",
    }
    assert categories == {
        "Utilitaires": ["ping", "help"],
        "Divers": ["foo"],
    }
    assert cat_desc == {
        "Utilitaires": "Commandes utiles",
        "Divers": "Autres commandes",
    }


def test_load_help_config_intermediate_format(monkeypatch):
    data = {
        "commands": {"ban": "Ban un utilisateur"},
        "categories": {"Moderation": ["ban"]},
        "category_descriptions": {"Moderation": "Outils de modération"},
    }

    def _open(*args, **kwargs):
        return io.StringIO(json.dumps(data))

    monkeypatch.setattr(builtins, "open", _open)

    help_infos, categories, cat_desc = load_help_config()
    assert help_infos == {"ban": "Ban un utilisateur"}
    assert categories == {"Moderation": ["ban"]}
    assert cat_desc == {"Moderation": "Outils de modération"}


def test_load_help_config_legacy_format(monkeypatch):
    data = {"oldcmd": "ancienne description"}

    def _open(*args, **kwargs):
        return io.StringIO(json.dumps(data))

    monkeypatch.setattr(builtins, "open", _open)

    help_infos, categories, cat_desc = load_help_config()
    assert help_infos == {"oldcmd": "ancienne description"}
    assert categories == {}
    assert cat_desc == {}
