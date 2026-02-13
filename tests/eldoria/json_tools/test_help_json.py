# tests/eldoria/json_tools/test_help_json.py
import json

from eldoria.json_tools.help_json import load_help_config, load_help_json


def test_load_help_json_file_not_found():
    assert load_help_json(path="does_not_exist_help.json") == {}


def test_load_help_json_valid(tmp_path):
    data = {"ok": True}
    p = tmp_path / "help.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    assert load_help_json(path=str(p)) == data


def test_load_help_config_structured_format(monkeypatch):
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

    # On patch le loader, pas open()
    monkeypatch.setattr("eldoria.json_tools.help_json.load_help_json", lambda: data)

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

    monkeypatch.setattr("eldoria.json_tools.help_json.load_help_json", lambda: data)

    help_infos, categories, cat_desc = load_help_config()
    assert help_infos == {"ban": "Ban un utilisateur"}
    assert categories == {"Moderation": ["ban"]}
    assert cat_desc == {"Moderation": "Outils de modération"}


def test_load_help_config_legacy_format(monkeypatch):
    data = {"oldcmd": "ancienne description"}

    monkeypatch.setattr("eldoria.json_tools.help_json.load_help_json", lambda: data)

    help_infos, categories, cat_desc = load_help_config()
    assert help_infos == {"oldcmd": "ancienne description"}
    assert categories == {}
    assert cat_desc == {}
