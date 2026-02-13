# tests/eldoria/json_tools/test_duels_json.py

from eldoria.json_tools.duels_json import get_duel_embed_data, get_game_text


def test_get_duel_embed_data_defaults_when_file_missing(monkeypatch):
    # On évite de monkeypatch open() (VSCode pytest), on patch la fonction loader
    monkeypatch.setattr("eldoria.json_tools.duels_json.load_duels_json", lambda: {})

    data = get_duel_embed_data()

    assert data["title"] == "⚔️ Duel d'XP"
    assert "Défie un autre joueur" in data["description"]
    assert "games" in data
    assert "RPS" in data["games"]  # fallback minimal présent


def test_get_duel_embed_data_uses_title_and_description_when_valid(monkeypatch):
    monkeypatch.setattr(
        "eldoria.json_tools.duels_json.load_duels_json",
        lambda: {
            "title": "  Mon titre  ",
            "description": "  Ma description  ",
            "games": {},
        },
    )

    data = get_duel_embed_data()
    assert data["title"] == "Mon titre"
    assert data["description"] == "Ma description"


def test_get_duel_embed_data_filters_invalid_games_and_strips(monkeypatch):
    # Mélange de jeux valides/invalides + trims
    monkeypatch.setattr(
        "eldoria.json_tools.duels_json.load_duels_json",
        lambda: {
            "title": "T",
            "description": "D",
            "games": {
                "": {"name": "X", "description": "Y"},  # clé vide -> ignoré
                "   ": {"name": "X", "description": "Y"},  # clé vide -> ignoré
                "OK": "not a dict",  # payload invalide -> ignoré
                "NO_NAME": {"name": "   ", "description": "desc"},  # name vide -> ignoré
                "NO_DESC": {"name": "name", "description": ""},  # desc vide -> ignoré
                "RPS": {"name": "  Rock Paper Scissors  ", "description": "  Rules  "},  # valide
            },
        },
    )

    data = get_duel_embed_data()

    # Seul RPS doit survivre
    assert set(data["games"].keys()) == {"RPS"}
    assert data["games"]["RPS"]["name"] == "Rock Paper Scissors"
    assert data["games"]["RPS"]["description"] == "Rules"


def test_get_duel_embed_data_fallback_games_when_all_invalid(monkeypatch):
    # Si aucun jeu valide, fallback RPS
    monkeypatch.setattr(
        "eldoria.json_tools.duels_json.load_duels_json",
        lambda: {"title": "T", "description": "D", "games": {"BAD": {"name": "", "description": ""}}},
    )

    data = get_duel_embed_data()
    assert "RPS" in data["games"]
    assert "Pierre" in data["games"]["RPS"]["name"]  # signature du fallback


def test_get_game_text_returns_game_when_exists(monkeypatch):
    monkeypatch.setattr(
        "eldoria.json_tools.duels_json.get_duel_embed_data",
        lambda: {
            "title": "T",
            "description": "D",
            "games": {
                "RPS": {"name": "  N  ", "description": "  Desc  "},
            },
        },
    )

    name, desc = get_game_text("RPS")
    assert name == "N"
    assert desc == "Desc"


def test_get_game_text_fallback_when_missing(monkeypatch):
    monkeypatch.setattr(
        "eldoria.json_tools.duels_json.get_duel_embed_data",
        lambda: {"title": "T", "description": "D", "games": {}},
    )

    name, desc = get_game_text("RPS")
    assert name == "🎮 Jeu inconnu"
    assert "pas disponible" in desc


def test_get_game_text_fallback_when_invalid_payload(monkeypatch):
    monkeypatch.setattr(
        "eldoria.json_tools.duels_json.get_duel_embed_data",
        lambda: {"title": "T", "description": "D", "games": {"RPS": "not a dict"}},
    )

    name, desc = get_game_text("RPS")
    assert name == "🎮 Jeu inconnu"
    assert "pas disponible" in desc


def test_get_game_text_accepts_non_string_key(monkeypatch):
    # get_game_text convertit en str(game_key)
    monkeypatch.setattr(
        "eldoria.json_tools.duels_json.get_duel_embed_data",
        lambda: {"title": "T", "description": "D", "games": {"123": {"name": "N", "description": "D"}}},
    )

    name, desc = get_game_text(123)  # type: ignore[arg-type]
    assert name == "N"
    assert desc == "D"
