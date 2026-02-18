"""Module définissant les exceptions liées à la configuration de l'application (variables d'environnement, .env, etc.)."""

from eldoria.exceptions.base import AppError


class ConfigError(AppError):
    """Erreur de configuration (variables d'environnement, .env, etc.)."""

class MissingEnvVar(ConfigError):
    """Erreur indiquant qu'une variable d'environnement requise est manquante."""

    def __init__(self, name: str) -> None:
        """Initialise l'exception avec le nom de la variable d'environnement manquante."""
        super().__init__(f"Variable d'environnement requise manquante: {name}")
        self.name = name

class InvalidEnvVar(ConfigError):
    """Erreur indiquant qu'une variable d'environnement a une valeur invalide ou mal formatée."""

    def __init__(self, name: str, expected: str) -> None:
        """Initialise l'exception avec le nom de la variable d'environnement concernée et une description du format attendu."""
        super().__init__(f"Variable d'environnement invalide: {name} (attendu: {expected})")
        self.name = name
        self.expected = expected

class IncompleteFeatureConfig(ConfigError):
    """Erreur indiquant qu'une fonctionnalité est activée mais que certaines variables de configuration nécessaires sont manquantes."""

    def __init__(self, feature: str, missing: list[str]) -> None:
        """Initialise l'exception avec le nom de la fonctionnalité concernée et la liste des variables de configuration manquantes."""
        super().__init__(f"Configuration incomplète pour {feature}: {', '.join(missing)}")
        self.feature = feature
        self.missing = missing
