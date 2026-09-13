from types import SimpleNamespace

import discord  # type: ignore
import pytest

from eldoria.ui.embed.preview import EmbedPreviewView, build_custom_embed
from tests._fakes import FakeInteraction, FakeMember, FakeTextChannel, FakeUser


def test_build_custom_embed_identifies_author_and_keeps_footer():
    author = FakeMember(42, display_name="Alice", avatar_url="https://cdn/alice.png")

    embed = build_custom_embed(
        title="Annonce",
        content="Contenu",
        footer="Pied de page",
        author=author,
    )

    assert embed.title == "Annonce"
    assert embed.description == "Contenu"
    assert embed.author == {
        "name": "Publié par Alice",
        "icon_url": "https://cdn/alice.png",
    }
    assert embed.footer == {"text": "Pied de page"}
    assert embed.thumbnail == {"url": "attachment://logo_bot.png"}
    assert embed.image is None


@pytest.mark.asyncio
async def test_publish_sends_embed_without_mass_mentions_by_default():
    channel = FakeTextChannel(123)
    embed = discord.Embed(title="Annonce")
    view = EmbedPreviewView(
        author_id=42,
        channel=channel,
        embed=embed,
        role=None,
    )
    interaction = FakeInteraction(
        user=FakeUser(42),
        data={"custom_id": "embed:publish"},
    )

    await view.route_button(interaction)

    sent = channel.sent[-1]
    assert sent["embed"] is embed
    assert sent["content"] is None
    assert len(sent["files"]) == 1
    assert sent["kwargs"]["allowed_mentions"].everyone is False
    assert interaction.response.deferred is True
    assert interaction.original_edits[-1]["content"].startswith("✅ Embed publié")
    assert interaction.original_edits[-1]["attachments"] == []
    assert view.completed is True


@pytest.mark.asyncio
async def test_publish_mentions_only_selected_role_in_spoiler():
    channel = FakeTextChannel(123, guild=type("Guild", (), {"me": object()})())
    role = type(
        "Role",
        (),
        {"id": 456, "mention": "<@&456>", "mentionable": False},
    )()
    view = EmbedPreviewView(
        author_id=42,
        channel=channel,
        embed=discord.Embed(title="Annonce"),
        role=role,
    )
    interaction = FakeInteraction(
        user=FakeUser(42),
        data={"custom_id": "embed:publish"},
    )

    await view.route_button(interaction)

    sent = channel.sent[-1]
    assert sent["content"] == "|| <@&456> ||"
    assert sent["kwargs"]["allowed_mentions"].everyone is False
    assert sent["kwargs"]["allowed_mentions"].roles == [role]


@pytest.mark.asyncio
async def test_publish_refuses_role_that_discord_would_not_notify():
    guild = type("Guild", (), {"me": object()})()
    channel = FakeTextChannel(123, guild=guild)
    role = type(
        "Role",
        (),
        {"id": 456, "mention": "<@&456>", "mentionable": False},
    )()
    view = EmbedPreviewView(
        author_id=42,
        channel=channel,
        embed=discord.Embed(title="Annonce"),
        role=role,
    )
    interaction = FakeInteraction(
        user=FakeUser(42),
        data={"custom_id": "embed:publish"},
    )
    channel.permissions_for = lambda _member: type(
        "Permissions",
        (),
        {"mention_everyone": False},
    )()

    await view.route_button(interaction)

    assert channel.sent == []
    assert interaction.response.sent[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_cancel_does_not_send_message():
    channel = FakeTextChannel(123)
    view = EmbedPreviewView(
        author_id=42,
        channel=channel,
        embed=discord.Embed(title="Annonce"),
        role=None,
    )
    interaction = FakeInteraction(
        user=FakeUser(42),
        data={"custom_id": "embed:cancel"},
    )

    await view.route_button(interaction)

    assert channel.sent == []
    assert interaction.response.edits[-1]["content"] == "❌ Publication annulée."
    assert interaction.response.edits[-1]["attachments"] == []


@pytest.mark.asyncio
async def test_preview_rejects_another_user():
    view = EmbedPreviewView(
        author_id=42,
        channel=FakeTextChannel(123),
        embed=discord.Embed(title="Annonce"),
        role=None,
    )
    response = SimpleNamespace(sent=[])

    async def send_message(content, *, ephemeral=False):
        response.sent.append({"content": content, "ephemeral": ephemeral})

    response.send_message = send_message
    interaction = SimpleNamespace(user=FakeUser(99), response=response)

    assert await view.interaction_check(interaction) is False
    assert response.sent[-1]["ephemeral"] is True
