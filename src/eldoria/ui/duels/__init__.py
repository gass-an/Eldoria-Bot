from __future__ import annotations

def init_duel_ui() -> None:
    
    from .games import rps as rps_ui
    rps_ui.register()