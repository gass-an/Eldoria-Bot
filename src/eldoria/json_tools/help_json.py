import json
from typing import Any, Dict, Tuple


def load_help_json() -> Dict[str, Any]:
    """Charge le fichier resources/json/help.json.

    Le format du fichier peut évoluer : cette fonction renvoie simplement le JSON brut.
    Pour obtenir une structure normalisée (help_infos, categories, category_descriptions),
    utilise : `load_help_config()`.
    """
    try:
        with open("./resources/json/help.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def load_help_config() -> Tuple[Dict[str, str], Dict[str, list[str]], Dict[str, str]]:
    """Normalise la config help depuis help.json.

    Retourne:
    - help_infos: {cmd_name: description}
    - categories: {category_name: [cmd_name, ...]}
    - category_descriptions: {category_name: description}

    Formats supportés:
    1) Nouveau (recommandé):
       {"categories": {"Nom": {"description": "...", "commands": {"cmd": "desc"}}}}
    2) Ancien: {"commands": {...}, "categories": {...}, "category_descriptions": {...}}
    3) Très ancien: {"cmd_name": "description", ...}
    """

    help_data = load_help_json() or {}

    # 1) Format structuré
    if isinstance(help_data, dict) and "categories" in help_data and isinstance(help_data.get("categories"), dict):
        cats_obj = help_data.get("categories", {})
        structured = True
        help_infos: Dict[str, str] = {}
        categories: Dict[str, list[str]] = {}
        cat_desc: Dict[str, str] = {}

        for cat_name, cat_payload in cats_obj.items():
            if not isinstance(cat_payload, dict):
                structured = False
                break
            desc = cat_payload.get("description", "")
            cmds = cat_payload.get("commands", {})
            if not isinstance(cmds, dict):
                cmds = {}

            cat_desc[cat_name] = desc
            categories[cat_name] = list(cmds.keys())
            for cmd_name, cmd_desc in cmds.items():
                if isinstance(cmd_desc, str):
                    help_infos[cmd_name] = cmd_desc

        if structured:
            return help_infos, categories, cat_desc

    # 2) Format intermédiaire
    if isinstance(help_data, dict) and "commands" in help_data:
        help_infos = dict(help_data.get("commands", {}) or {})
        categories = dict(help_data.get("categories", {}) or {})
        cat_desc = dict(help_data.get("category_descriptions", {}) or {})
        return help_infos, categories, cat_desc

    # 3) Format legacy
    return dict(help_data or {}), {}, {}
