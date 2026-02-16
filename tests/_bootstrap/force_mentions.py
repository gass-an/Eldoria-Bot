from __future__ import annotations

import sys


def force_real_mentions_module() -> None:
    mod_name = "eldoria.utils.mentions"
    sys.modules.pop(mod_name, None)  # purge si un stub traîne
    __import__(mod_name)  # importe le vrai


