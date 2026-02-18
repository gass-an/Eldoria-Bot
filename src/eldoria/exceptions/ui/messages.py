"""Module de mapping des exceptions de l'application en messages d'erreur destinés à être affichés dans l'interface utilisateur (UI)."""

from eldoria.exceptions.base import AppError
from eldoria.exceptions.duel import DuelError
from eldoria.exceptions.ui.duel_ui import duel_error_message
from eldoria.exceptions.ui.general_ui import general_error_message


def app_error_message(e: AppError) -> str:
    """Routeur général: choisit le bon mapper selon le type d'erreur."""
    if isinstance(e, DuelError):
        return duel_error_message(e)
    
    return general_error_message(e)