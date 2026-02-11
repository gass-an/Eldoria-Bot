"""Module d'initialisation du jeu Pierre-Feuille-Ciseaux pour les duels."""
import eldoria.features.duel.constants as constants
from eldoria.ui.duels.games.rps.renderer import render_rps


def register() -> None:
    """Enregistre le renderer du jeu Pierre-Feuille-Ciseaux."""
    from eldoria.ui.duels.registry import register_renderer
    register_renderer(constants.GAME_RPS, render_rps)
