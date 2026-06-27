"""Initialisation UI pour le ticketing (enregistre les views persistantes)."""

from __future__ import annotations

from typing import Any

from eldoria.ui.ticketing.create_view import TicketCreateView


def init_ticket_ui(bot: Any) -> None:
    """Enregistre la view persistante pour gérer les boutons de création de ticket.

    Doit être appelé au démarrage avec l'instance du bot.
    """
    try:
        bot.add_view(TicketCreateView())
    except Exception:
        # Ne pas planter le démarrage si l'enregistrement échoue
        pass

