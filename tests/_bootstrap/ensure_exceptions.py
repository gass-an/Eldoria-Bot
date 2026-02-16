from __future__ import annotations

import sys
from types import ModuleType


def ensure_general_exceptions() -> None:
    mod_name = "eldoria.exceptions.general_exceptions"
    try:
        __import__(mod_name)
        mod = sys.modules[mod_name]
    except Exception:
        mod = sys.modules.get(mod_name)
        if mod is None:
            mod = ModuleType(mod_name)
            sys.modules[mod_name] = mod

    for exc in ("GuildRequired", "ChannelRequired", "UserRequired", "MessageRequired"):
        if not hasattr(mod, exc):
            setattr(mod, exc, type(exc, (Exception,), {}))


