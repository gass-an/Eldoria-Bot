import pytest

from tests._embed_fakes import FakeBot, FakeChannel, FakeGuild  # active stubs discord


@pytest.mark.asyncio
async def test_build_list_roles_embed_builds_fields_and_footer(monkeypatch):
    from eldoria.ui.roles import embeds

    async def fake_find_channel_id(*, bot, message_id, guild_id):
        assert guild_id == 123
        assert message_id == "111"
        return 999

    monkeypatch.setattr(embeds.discord_utils, "find_channel_id", fake_find_channel_id)

    roles = [
        ("111", {"😀": 1, "🔥": 2}),
    ]

    embed, files = await embeds.build_list_roles_embed(
        roles=roles,
        current_page=0,
        total_pages=3,
        guild_id=123,
        bot=object(),
    )

    assert embed.title == "Liste des rôles"
    assert len(embed.fields) == 2  # separator + content
    assert "https://discord.com/channels/123/999/111" in embed.fields[1]["name"]
    assert "😀" in embed.fields[1]["value"] and "<@&1>" in embed.fields[1]["value"]
    assert "🔥" in embed.fields[1]["value"] and "<@&2>" in embed.fields[1]["value"]
    assert embed.footer["text"].startswith("Nombre de rôles attribués : 2")
    assert "Page 1/3" in embed.footer["text"]
    assert len(files) == 2
    assert embed.thumbnail == {"url": "attachment://logo_bot.png"}
    assert embed.image == {"url": "attachment://banner_bot.png"}


@pytest.mark.asyncio
async def test_build_list_secret_roles_embed():
    from eldoria.ui.roles import embeds

    roles = [
        ("777", {"open sesame": 42}),
    ]

    embed, files = await embeds.build_list_secret_roles_embed(
        roles=roles,
        current_page=1,
        total_pages=2,
        guild_id=123,
        bot=object(),
    )

    assert embed.title == "Liste des rôles secrets"
    assert len(embed.fields) == 2
    assert "https://discord.com/channels/123/777" in embed.fields[1]["name"]
    assert "`open sesame`" in embed.fields[1]["value"]
    assert "<@&42>" in embed.fields[1]["value"]
    assert "Nombre de rôles attribués : 1" in embed.footer["text"]
    assert "Page 2/2" in embed.footer["text"]
    assert len(files) == 2


@pytest.mark.asyncio
async def test_build_list_temp_voice_parents_embed_empty_items():
    from eldoria.ui.temp_voice import embeds

    bot = FakeBot(guild=None)
    embed, files = await embeds.build_list_temp_voice_parents_embed(
        items=[], page=0, total_pages=1, identifiant_for_embed=123, bot=bot
    )

    assert embed.title == "Salons pour la création de vocaux temporaires"
    assert embed.fields and embed.fields[0]["name"] == "Aucun salon"
    assert "Page 1/1" in embed.footer["text"]
    assert len(files) == 2


@pytest.mark.asyncio
async def test_build_list_temp_voice_parents_embed_with_found_and_missing_channels():
    from eldoria.ui.temp_voice import embeds

    guild = FakeGuild(123)
    guild.add_channel(FakeChannel(10))
    bot = FakeBot(guild)

    embed, files = await embeds.build_list_temp_voice_parents_embed(
        items=[(10, 3), (999, 2)], page=1, total_pages=5, identifiant_for_embed=123, bot=bot
    )

    assert embed.fields and embed.fields[0]["name"] == "Salons configurés"
    value = embed.fields[0]["value"]
    assert "<#10>" in value and "`3`" in value
    assert "Salon introuvable" in value and "ID `999`" in value and "`2`" in value
    assert "Page 2/5" in embed.footer["text"]
    assert len(files) == 2
