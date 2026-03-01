"""Exceptions de support pour les tests.

Ce module centralise les petites classes utilitaires (souvent des subclasses
d'exceptions) afin d'éviter toute déclaration de `class` dans `tests/eldoria/**`.
"""

from __future__ import annotations

from eldoria.exceptions.base import AppError
from eldoria.exceptions.duel import DuelError


class UnknownDuelError(DuelError):
    """Erreur de duel inconnue utilisée pour tester le fallback UI."""


class DummyDuelError(DuelError):
    """Erreur de duel factice pour vérifier le routage app_error_message()."""


class DummyAppError(AppError):
    """Erreur applicative factice pour vérifier le routage app_error_message()."""
