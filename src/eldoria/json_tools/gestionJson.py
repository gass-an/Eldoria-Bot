import json

def load_help_json():
    try:
        with open(f"./json/help.json","r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
