"""Définit le protocole (interface) que doivent implémenter les jeux de duel pour être compatibles avec le système de duels d'Eldoria."""

from __future__ import annotations

from sqlite3 import Row
from typing import Any, Protocol


class DuelGame(Protocol):
    """Interface que doit implémenter un jeu de duel pour être compatible avec le système de duels d'Eldoria."""

    GAME_KEY: str  # ex "RPS"

    def play(self, duel_id: int, user_id: int, action: dict[str, Any]) -> dict[str, Any]: 
        """Traite une action de jeu (coup joué) pour un duel, met à jour le duel en conséquence."""
        ...
    
    def is_complete(self, duel: Row) -> bool:
        """Retourne True si le duel est dans un état considéré comme "complet" pour ce jeu, c'est à dire que les conditions de fin du jeu sont remplies."""
        ...
    
    def resolve(self, duel: Row) -> str:
        """Retourne le résultat du duel pour ce jeu, en supposant que le duel est dans un état "complet" (conditions de fin du jeu remplies)."""
        ...