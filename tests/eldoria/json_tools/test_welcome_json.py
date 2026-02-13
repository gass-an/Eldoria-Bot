# tests/eldoria/json_tools/test_welcome_json.py
import json

from eldoria.json_tools.welcome_json import load_welcome_json


def test_load_welcome_json_file_not_found():
    assert load_welcome_json(path="does_not_exist_welcome_message.json") == {}


def test_load_welcome_json_valid_dict(tmp_path):
    data = {"packs": []}
    p = tmp_path / "welcome_message.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    assert load_welcome_json(path=str(p)) == data


def test_load_welcome_json_returns_empty_when_json_is_not_dict(tmp_path):
    # Si le JSON n'est pas un dict (liste, str, int...), la fonction doit renvoyer {}
    p = tmp_path / "welcome_message.json"
    p.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")

    assert load_welcome_json(path=str(p)) == {}


def test_load_welcome_json_invalid_json_returns_empty(tmp_path):
    # JSON invalide -> json.JSONDecodeError -> except Exception -> {}
    p = tmp_path / "welcome_message.json"
    p.write_text("{not valid json", encoding="utf-8")

    assert load_welcome_json(path=str(p)) == {}
