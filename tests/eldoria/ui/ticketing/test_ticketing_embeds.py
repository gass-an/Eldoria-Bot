import discord
import pytest

from eldoria.ui.common.embeds.colors import EMBED_COLOUR_PRIMARY
from eldoria.ui.ticketing.embeds import (
    build_ticket_closed_embed,
    build_ticket_request_embed,
)


def test_build_ticket_closed_embed_preserves_content_and_colour():
    embed = build_ticket_closed_embed(
        closed_by_mention="<@42>", closed_at=123456, ticket_number=7
    )

    assert embed.title == "Ticket fermé"
    assert embed.description == (
        "Ce ticket a été archivé.\n\n"
        "- Fermé par : <@42>\n"
        "- Date de fermeture : <t:123456:F>\n"
        "- Numéro : #007\n\n"
        "Ce ticket est désormais conservé en lecture seule dans les archives."
    )
    assert embed.colour == EMBED_COLOUR_PRIMARY


def test_build_ticket_request_embed_preserves_content_and_colour(
    monkeypatch: pytest.MonkeyPatch,
):
    blurple = discord.Color(0x5865F2)
    monkeypatch.setattr(discord.Color, "blurple", lambda: blurple, raising=False)

    embed = build_ticket_request_embed()

    assert embed.title == "📜 Envoyer une requête"
    assert embed.description == (
        "Adresse ton message aux gardiens du serveur en ouvrant un ticket privé. "
        "Nous te répondrons dans les meilleurs délais."
    )
    assert embed.colour == blurple
