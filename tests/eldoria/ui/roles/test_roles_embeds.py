from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.roles import embeds as M


class FakeBot:
    pass


@pytest.mark.asyncio
async def test_build_list_roles_embed_empty_roles(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 123)

    # decorate/common_files
    decorated = {"called": False}
    def fake_decorate(embed, thumb, banner):
        decorated["called"] = True
        return embed

    monkeypatch.setattr(M, "decorate", fake_decorate)
    monkeypatch.setattr(M, "common_files", lambda t, b: ["F1", "F2"])

    # find_channel_id ne doit pas être appelé si roles vide
    async def fake_find_channel_id(*, bot, message_id, guild_id):
        raise AssertionError("should not call")

    monkeypatch.setattr(M, "find_channel_id", fake_find_channel_id)

    embed, files = await M.build_list_roles_embed(
        roles=[],
        current_page=0,
        total_pages=1,
        guild_id=999,
        bot=FakeBot(),
    )

    assert isinstance(embed, discord.Embed)
    assert embed.title == "Liste des rôles"
    assert embed.colour == 123
    assert embed.fields == []
    assert "Nombre de rôles attribués : 0" in embed.footer["text"]
    assert "Page 1/1" in embed.footer["text"]
    assert decorated["called"] is True
    assert files == ["F1", "F2"]


@pytest.mark.asyncio
async def test_build_list_roles_embed_builds_fields_and_counts_roles(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)

    # decorate/common_files
    monkeypatch.setattr(M, "decorate", lambda embed, t, b: embed)
    monkeypatch.setattr(M, "common_files", lambda t, b: ["FILES"])

    # find_channel_id returns per message
    calls = []
    async def fake_find_channel_id(*, bot, message_id, guild_id):
        calls.append({"message_id": message_id, "guild_id": guild_id})
        return 555 if message_id == 111 else 777

    monkeypatch.setattr(M, "find_channel_id", fake_find_channel_id)

    roles = [
        ("111", {"😀": 10, "🔥": 20}),
        ("222", {"✅": 30}),
    ]

    embed, files = await M.build_list_roles_embed(
        roles=roles,
        current_page=1,
        total_pages=3,
        guild_id=42,
        bot=FakeBot(),
    )

    assert files == ["FILES"]

    # 2 messages => pour chacun : 1 field vide + 1 field lien = 4 fields
    assert len(embed.fields) == 4

    # message 111
    assert embed.fields[0] == {"name": "", "value": "", "inline": False}
    assert embed.fields[1]["name"] == "· https://discord.com/channels/42/555/111 : "
    assert "😀  **->** <@&10>" in embed.fields[1]["value"]
    assert "🔥  **->** <@&20>" in embed.fields[1]["value"]

    # message 222
    assert embed.fields[2] == {"name": "", "value": "", "inline": False}
    assert embed.fields[3]["name"] == "· https://discord.com/channels/42/777/222 : "
    assert "✅  **->** <@&30>" in embed.fields[3]["value"]

    # compteur: 2 + 1 = 3
    assert "Nombre de rôles attribués : 3" in embed.footer["text"]
    assert "Page 2/3" in embed.footer["text"]

    # find_channel_id called with correct params
    assert calls == [
        {"message_id": 111, "guild_id": 42},
        {"message_id": 222, "guild_id": 42},
    ]


@pytest.mark.asyncio
async def test_build_list_roles_embed_skips_field_when_mapping_empty(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)
    monkeypatch.setattr(M, "decorate", lambda embed, t, b: embed)
    monkeypatch.setattr(M, "common_files", lambda t, b: [])

    async def fake_find_channel_id(*, bot, message_id, guild_id):
        return 123

    monkeypatch.setattr(M, "find_channel_id", fake_find_channel_id)

    roles = [
        ("111", {}),  # mapping vide => pas de fields ajoutés
    ]

    embed, _ = await M.build_list_roles_embed(
        roles=roles,
        current_page=0,
        total_pages=1,
        guild_id=42,
        bot=FakeBot(),
    )

    assert embed.fields == []
    assert "Nombre de rôles attribués : 0" in embed.footer["text"]


@pytest.mark.asyncio
async def test_build_list_secret_roles_embed_builds_fields_and_counts(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 5)
    monkeypatch.setattr(M, "decorate", lambda embed, t, b: embed)
    monkeypatch.setattr(M, "common_files", lambda t, b: ["FILES"])

    # find_channel_id n'est PAS utilisé ici
    async def fake_find_channel_id(**kwargs):
        raise AssertionError("should not call")

    monkeypatch.setattr(M, "find_channel_id", fake_find_channel_id)

    roles = [
        ("555", {"open sesame": 10, "abracadabra": 20}),
        ("777", {"hello": 30}),
    ]

    embed, files = await M.build_list_secret_roles_embed(
        roles=roles,
        current_page=0,
        total_pages=2,
        guild_id=42,
        bot=FakeBot(),
    )

    assert isinstance(embed, discord.Embed)
    assert embed.title == "Liste des rôles secrets"
    assert embed.colour == 5
    assert files == ["FILES"]

    # 2 channels => 4 fields (vide + lien) *2
    assert len(embed.fields) == 4

    assert embed.fields[1]["name"] == "· https://discord.com/channels/42/555 : "
    assert "Message: `open sesame`  **->** <@&10>" in embed.fields[1]["value"]
    assert "Message: `abracadabra`  **->** <@&20>" in embed.fields[1]["value"]

    assert embed.fields[3]["name"] == "· https://discord.com/channels/42/777 : "
    assert "Message: `hello`  **->** <@&30>" in embed.fields[3]["value"]

    # compteur: 2 + 1 = 3
    assert "Nombre de rôles attribués : 3" in embed.footer["text"]
    assert "Page 1/2" in embed.footer["text"]


@pytest.mark.asyncio
async def test_build_list_secret_roles_embed_skips_when_mapping_empty(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)
    monkeypatch.setattr(M, "decorate", lambda embed, t, b: embed)
    monkeypatch.setattr(M, "common_files", lambda t, b: [])

    roles = [
        ("555", {}),
    ]

    embed, _ = await M.build_list_secret_roles_embed(
        roles=roles,
        current_page=0,
        total_pages=1,
        guild_id=42,
        bot=FakeBot(),
    )

    assert embed.fields == []
    assert "Nombre de rôles attribués : 0" in embed.footer["text"]
