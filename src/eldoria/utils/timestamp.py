"""Utilitaires pour la gestion des timestamps, avec des fonctions pour obtenir le timestamp actuel et ajouter une durée à un timestamp donné."""

from datetime import UTC, datetime


def now_ts() -> int:
    """Retourne le timestamp actuel en secondes depuis l'époque Unix."""
    return int(datetime.now(UTC).timestamp())

def add_duration(timestamp:int, *, seconds:int = 0, minutes:int = 0, hours:int = 0, days:int = 0) -> int:
    """Retourne un timestamp correspondant à l'addition de la durée spécifiée au timestamp donné."""
    if seconds < 0 or minutes < 0 or hours < 0 or days < 0:
        raise ValueError("Durée négative interdite")

    return timestamp + seconds + (minutes * 60) + (hours * 3600) + (days * 86400)