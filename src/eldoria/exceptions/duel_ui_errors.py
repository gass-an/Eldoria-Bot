from __future__ import annotations
from eldoria.exceptions.duel_exceptions import *

def duel_error_message(e: DuelError) -> str:
    # Messages “membre-friendly” (pas trop techniques)
    match e:
        case SamePlayerDuel():
            return "😅 Tu ne peux pas te défier toi-même."

        case PlayerAlreadyInDuel():
            return "⚠️ L'un des joueurs est déjà en duel."

        case DuelNotFound():
            return "⚠️ Ce duel n'existe plus (ou a expiré)."

        case ExpiredDuel():
            return "⌛ Ce duel a expiré."

        case NotAuthorizedPlayer():
            return "⛔ Tu n'as pas l'autorisation d'interagir avec ce duel."

        case ConfigurationIncomplete():
            return "⚠️ Le duel n'est pas entièrement configuré."

        case InvalidGameType():
            return "⚠️ Jeu invalide."

        case InvalidStake():
            return "⚠️ Mise invalide."

        case InsufficientXp(required=req):
            return f"💸 Mise impossible : il faut au moins **{req} XP** des deux côtés."

        case DuelNotAcceptable():
            return "⚠️ Ce duel ne peut pas être accepté dans son état actuel."

        case DuelNotFinishable():
            return "⚠️ Ce duel ne peut pas être terminé dans son état actuel."

        case DuelNotActive():
            return "⚠️ Le duel n'est pas actif."

        case WrongGameType():
            return "⚠️ Mauvais jeu pour cette action."

        case InvalidMove():
            return "⚠️ Coup invalide."

        case AlreadyPlayed():
            return "⚠️ Tu as déjà joué."

        case PayloadError():
            return "⚠️ Petit souci technique, réessaie."

        case DuelAlreadyHandled():
            return "ℹ️ Ce duel a déjà été traité (quelqu'un a cliqué juste avant)."

        case (ConfigurationError() | MissingMessageId() | InvalidResult() | DuelNotFinished()):
            return "❌ Une erreur est survenue. Réessaie."

        case _:
            # fallback: garde un message générique, pas le détail technique
            return "❌ Une erreur est survenue."