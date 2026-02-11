"""Service de gestion des duels.

Ce service expose les différentes fonctionnalités liées aux duels, telles que la création de duels,
la configuration, l'acceptation/refus, le déroulement des jeux, et la maintenance des duels (annulation des duels expirés, nettoyage des anciens duels).
C'est l'interface principale utilisée par les autres parties du bot pour interagir avec le système de duels.
"""

from dataclasses import dataclass
from typing import Any

from eldoria.features.duel._internal import flow, gameplay, helpers, maintenance


@dataclass(slots=True)
class DuelService:
    """Service de gestion des duels, exposant les différentes fonctionnalités liées aux duels."""

    def new_duel(self, guild_id: int, channel_id: int, player_a_id: int, player_b_id: int) -> dict[str, Any]:
        """Crée un nouveau duel en base de données avec les informations spécifiées, et retourne un objet décrivant le duel nouvellement créé."""
        return flow.new_duel(guild_id, channel_id, player_a_id, player_b_id)

    def configure_game_type(self, duel_id: int, game_type: str) -> dict[str, Any]:
        """Configure le type de jeu d'un duel en cours de configuration, et retourne un objet décrivant le duel mis à jour."""
        return flow.configure_game_type(duel_id, game_type)

    def configure_stake_xp(self, duel_id: int, stake_xp: int) -> dict[str, Any]:
        """Configure la mise d'XP d'un duel en cours de configuration, et retourne un objet décrivant le duel mis à jour."""
        return flow.configure_stake_xp(duel_id, stake_xp)

    def send_invite(self, duel_id: int, message_id: int) -> dict[str, Any]:
        """Envoie l'invitation de duel (message + boutons) dans le salon Discord, et retourne un objet décrivant le duel mis à jour avec les informations du message d'invitation."""
        return flow.send_invite(duel_id, message_id)

    def accept_duel(self, duel_id: int, user_id: int) -> dict[str, Any]:
        """Accepte une invitation de duel pour un utilisateur donné, et retourne un objet décrivant le duel mis à jour avec les informations du début du duel (statut, configuration du jeu, etc)."""
        return flow.accept_duel(duel_id, user_id)

    def refuse_duel(self, duel_id: int, user_id: int) -> dict[str, Any]:
        """Refuse une invitation de duel pour un utilisateur donné, et retourne un objet décrivant le duel mis à jour avec le statut CANCELLED."""
        return flow.refuse_duel(duel_id, user_id)

    def play_game_action(self, duel_id: int, user_id: int, action: dict[str, Any]) -> dict[str, Any]:
        """Traite une action de jeu pour un duel en cours, et retourne un objet décrivant le duel mis à jour avec les informations de jeu mises à jour (coup joué, résultat du coup, etc)."""
        return gameplay.play_game_action(duel_id, user_id, action)

    def cancel_expired_duels(self) -> list[dict[str, Any]]:
        """Expire les duels arrivés à échéance, et retourne une liste d'objets décrivant les duels effectivement passés en EXPIRED."""
        return maintenance.cancel_expired_duels()

    def cleanup_old_duels(self, now_ts: int) -> None:
        """Supprime les duels terminés depuis suffisamment longtemps de la base de données."""
        return maintenance.cleanup_old_duels(now_ts)
    
    def get_allowed_stakes(self, duel_id: int) -> list[int]:
        """Retourne la liste des mises en XP autorisées pour un duel donné, c'est à dire les mises pour lesquelles les 2 joueurs ont suffisamment d'XP."""
        return helpers.get_allowed_stakes(duel_id)
