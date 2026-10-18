"""Construction des embeds du système de ticketing."""

from __future__ import annotations

import discord

from eldoria.ui.common.embeds.colors import EMBED_COLOUR_PRIMARY


def build_ticket_closed_embed(
    *, closed_by_mention: str, closed_at: int, ticket_number: int
) -> discord.Embed:
    """Construit l'embed envoyé dans un ticket nouvellement archivé."""
    return discord.Embed(
        title="Ticket fermé",
        description=(
            "Ce ticket a été archivé.\n\n"
            f"- Fermé par : {closed_by_mention}\n"
            f"- Date de fermeture : <t:{closed_at}:F>\n"
            f"- Numéro : #{ticket_number:03d}\n\n"
            "Ce ticket est désormais conservé en lecture seule dans les archives."
        ),
        color=EMBED_COLOUR_PRIMARY,
    )


def build_ticket_request_embed() -> discord.Embed:
    """Construit l'embed public permettant d'ouvrir un ticket."""
    return discord.Embed(
        title="📜 Envoyer une requête",
        description=(
            "Adresse ton message aux gardiens du serveur en ouvrant un ticket privé. "
            "Nous te répondrons dans les meilleurs délais."
        ),
        color=discord.Color.blurple(),
    )
