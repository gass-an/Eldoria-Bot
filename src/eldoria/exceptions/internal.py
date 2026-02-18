"""Module des exceptions internes liées à l'état et au cycle de vie du bot."""

from eldoria.exceptions.base import AppError


class InternalStateError(AppError):
    """Erreur interne liée à l'état/cycle de vie du bot."""

class ServicesNotInitialized(InternalStateError):
    """Erreur indiquant que les services du bot n'ont pas été initialisés."""

    def __init__(self) -> None:
        """Initialise l'exception avec un message indiquant que les services n'ont pas été initialisés."""
        super().__init__("Services non initialisés. Appelle bot.set_services(...) avant de charger les cogs.")

class ServicesAlreadyInitialized(InternalStateError):
    """Erreur indiquant que les services du bot ont déjà été initialisés."""

    def __init__(self) -> None:
        """Initialise l'exception avec un message indiquant que les services ont déjà été initialisés."""
        super().__init__("Services déjà initialisés.")

class TestsFailed(InternalStateError):
    """Les tests unitaires ont échoué."""

    def __init__(self) -> None:
        """Initialise l'exception avec un message indiquant que les tests unitaires ont échoué."""
        super().__init__("Les tests unitaires ont échoué. Abandon du démarrage du bot.")