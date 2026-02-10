from __future__ import annotations


def init_duel_ui() -> None:
    
    # Import local pour éviter un import circulaire
    from .games import rps as rps_ui
    
    rps_ui.register()