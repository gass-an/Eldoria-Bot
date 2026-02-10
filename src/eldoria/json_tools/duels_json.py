import json
from typing import Any


def load_duels_json() -> dict[str, Any]:
    """
    Charge le fichier resources/json/duels.json.
    Renvoie le JSON brut (dict).
    """
    try:
        with open("./resources/json/duels.json", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def get_duel_embed_data() -> dict[str, Any]:
    """
    Retourne un dict NORMALISÉ, directement exploitable pour les embeds :

    {
        "title": str,
        "description": str,
        "games": {
            "game_type": {
            "name": str,
            "description": str
            }
        }
    }
    """
    data = load_duels_json() or {}

    # ---- title
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        title = "⚔️ Duel d'XP"
    else:
        title = title.strip()

    # ---- description
    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        description = (
            "Défie un autre joueur dans un mini-jeu avec une mise en XP.\n"
            "Choisis un jeu et une mise, puis envoie une invitation."
        )
    else:
        description = description.strip()

    # ---- games
    games_raw = data.get("games", {})
    games: dict[str, dict[str, str]] = {}

    if isinstance(games_raw, dict):
        for game_key, g in games_raw.items():
            if not isinstance(game_key, str) or not game_key.strip():
                continue
            if not isinstance(g, dict):
                continue

            name = g.get("name")
            desc = g.get("description")

            if not isinstance(name, str) or not name.strip():
                continue
            if not isinstance(desc, str) or not desc.strip():
                continue

            games[game_key] = {
                "name": name.strip(),
                "description": desc.strip(),
            }

    # ---- fallback minimal
    if not games:
        games = {
            "RPS": {
                "name": "✊📄✂️ Pierre • Feuille • Ciseaux",
                "description": (
                    "Chaque joueur choisit un coup en secret.\n\n"
                    "✊ bat ✂️ • ✂️ bat 📄 • 📄 bat ✊\n"
                    "Même coup = égalité."
                ),
            }
        }

    return {
        "title": title,
        "description": description,
        "games": games,
    }

def get_game_text(game_key: str) -> tuple[str, str]:
    """
    Retourne (game_name, game_description) pour un game_key (ex: 'RPS').

    Fallback safe si le jeu n'existe pas.
    """
    data = get_duel_embed_data()
    games = data.get("games", {})

    g = games.get(str(game_key))
    if isinstance(g, dict):
        name = g.get("name")
        desc = g.get("description")
        if isinstance(name, str) and name.strip() and isinstance(desc, str) and desc.strip():
            return name.strip(), desc.strip()

    return (
        "🎮 Jeu inconnu",
        "Ce jeu n'est pas disponible ou n'est pas encore documenté."
    )