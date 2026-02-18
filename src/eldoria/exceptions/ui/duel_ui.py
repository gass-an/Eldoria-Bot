"""Module `duel_ui_errors`.

Contient des fonctions pour convertir les exceptions de duel en messages d'erreur "membre-friendly" à afficher dans l'interface utilisateur,
afin de fournir des retours clairs et compréhensibles aux utilisateurs lorsqu'une action liée au duel échoue.
"""

from __future__ import annotations

from eldoria.exceptions import duel as exc


def duel_error_message(e: exc.DuelError) -> str:
    """Retourne un message d'erreur "membre-friendly" à partir d'une exception de duel."""
    match e:
        case exc.SamePlayerDuel():
            return "😅 Tu ne peux pas te défier toi-même."

        case exc.PlayerAlreadyInDuel():
            return "⚠️ L'un des joueurs est déjà en duel."

        case exc.DuelNotFound():
            return "⚠️ Ce duel n'existe plus (ou a expiré)."

        case exc.ExpiredDuel():
            return "⌛ Ce duel a expiré."

        case exc.NotAuthorizedPlayer():
            return "⛔ Tu n'as pas l'autorisation d'interagir avec ce duel."

        case exc.ConfigurationIncomplete():
            return "⚠️ Le duel n'est pas entièrement configuré."

        case exc.InvalidGameType():
            return "⚠️ Jeu invalide."

        case exc.InvalidStake():
            return "⚠️ Mise invalide."

        case exc.InsufficientXp(required=req):
            return f"💸 Mise impossible : il faut au moins **{req} XP** des deux côtés."

        case exc.DuelNotAcceptable():
            return "⚠️ Ce duel ne peut pas être accepté dans son état actuel."

        case exc.DuelNotFinishable():
            return "⚠️ Ce duel ne peut pas être terminé dans son état actuel."

        case exc.DuelNotActive():
            return "⚠️ Le duel n'est pas actif."

        case exc.WrongGameType():
            return "⚠️ Mauvais jeu pour cette action."

        case exc.InvalidMove():
            return "⚠️ Coup invalide."

        case exc.AlreadyPlayed():
            return "⚠️ Tu as déjà joué."

        case exc.PayloadError():
            return "⚠️ Petit souci technique, réessaie."

        case exc.DuelAlreadyHandled():
            return "ℹ️ Ce duel a déjà été traité (quelqu'un a cliqué juste avant)."

        case (exc.ConfigurationError() | exc.MissingMessageId() | exc.InvalidResult() | exc.DuelNotFinished()):
            return "❌ Une erreur est survenue. Réessaie."
    
        case exc.InvalidSnapshot():
            return "⚠️ Le duel est dans un état inattendu. Réessaie."

        case _:
            # fallback: garde un message générique, pas le détail technique
            return "❌ Une erreur est survenue."