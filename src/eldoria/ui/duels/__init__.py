"""Module d'initialisation de l'interface utilisateur pour les duels."""

from __future__ import annotations


def init_duel_ui() -> None:
    """Initialise les composants de l'interface utilisateur pour les duels."""
    # Import local pour éviter un import circulaire
    from .games import rps as rps_ui
    
    rps_ui.register()