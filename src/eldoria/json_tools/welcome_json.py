import json
from typing import Any


def load_welcome_json(path: str = "./resources/json/welcome_message.json") -> dict[str, Any]:
    """Charge le fichier welcome_message.json et renvoie le JSON brut."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

