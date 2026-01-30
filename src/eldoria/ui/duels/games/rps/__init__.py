import eldoria.features.duel.constants as constants
from .renderer import render_rps


def register() -> None:
    from eldoria.ui.duels.registry import register_renderer
    register_renderer(constants.GAME_RPS, render_rps)
