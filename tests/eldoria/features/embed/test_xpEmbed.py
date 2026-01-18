import pytest

from tests._embed_fakes import FakeBot, FakeGuild, FakeMember, FakeRole  # active stubs discord


@pytest.mark.asyncio
async def test_generate_xp_status_embed_disabled_branch():
    from eldoria.features.embed.xpEmbed import generate_xp_status_embed

    bot = FakeBot(FakeGuild(123))
    embed, files = await generate_xp_status_embed({"enabled": False}, 123, bot)

    assert embed.title == "Statut du système XP"
    assert any(f["name"] == "État" and "Désactivé" in f["value"] for f in embed.fields)
    assert any(f["name"] == "Information" for f in embed.fields)
    assert "Serveur : Eldoria" in embed.footer["text"]
    assert len(files) == 2


@pytest.mark.asyncio
async def test_generate_xp_status_embed_enabled_with_voice_cap_hours():
    from eldoria.features.embed.xpEmbed import generate_xp_status_embed

    bot = FakeBot(FakeGuild(123, name="Srv"))
    cfg = {
        "enabled": True,
        "points_per_message": 8,
        "cooldown_seconds": 90,
        "bonus_percent": 20,
        "karuta_k_small_percent": 30,
        "voice_enabled": True,
        "voice_interval_seconds": 180,  # 3min
        "voice_xp_per_interval": 2,
        "voice_daily_cap_xp": 100,
    }

    embed, _files = await generate_xp_status_embed(cfg, 123, bot)
    values = "\n".join(f["value"] for f in embed.fields)

    assert "✅ Activé" in values
    assert "XP / 3min" in values
    assert "100 XP/jour" in values
    assert "h" in values  # format "x.xh"


@pytest.mark.asyncio
async def test_generate_list_xp_embed_empty(monkeypatch):
    import eldoria.features.embed.xpEmbed as mod

    monkeypatch.setattr(mod.gestionDB, "xp_get_role_ids", lambda guild_id: {})

    bot = FakeBot(FakeGuild(123))
    embed, files = await mod.generate_list_xp_embed([], 0, 1, 123, bot)

    assert embed.title == "Classement XP"
    assert embed.fields and embed.fields[0]["name"] == "Aucun membre"
    assert "Page 1/1" in embed.footer["text"]
    assert len(files) == 2


@pytest.mark.asyncio
async def test_generate_list_xp_embed_labels_from_roles_and_precomputed(monkeypatch):
    import eldoria.features.embed.xpEmbed as mod

    # mapping level->role_id
    monkeypatch.setattr(mod.gestionDB, "xp_get_role_ids", lambda guild_id: {5: 555})

    guild = FakeGuild(123)
    guild.add_member(FakeMember("<@1>", display_name="Alice", member_id=1))
    guild.add_role(FakeRole(555))
    bot = FakeBot(guild)

    items = [
        (1, 120, 5),               # label doit venir du role mention
        (999, 50, 2, "lvl2"),      # label pré-calculé
    ]

    embed, _files = await mod.generate_list_xp_embed(items, 0, 2, 123, bot)

    text = embed.fields[0]["value"]
    assert "**1.** Alice" in text
    assert "<@&555>" in text
    assert "ID 999" in text
    assert "lvl2" in text


@pytest.mark.asyncio
async def test_generate_xp_profile_embed_max_level():
    import eldoria.features.embed.xpEmbed as mod

    bot = FakeBot(FakeGuild(123, name="Srv"))
    user = FakeMember("<@42>", display_name="Alice", member_id=42)

    embed, files = await mod.generate_xp_profile_embed(
        guild_id=123,
        user=user,
        xp=999,
        level=10,
        level_label="lvl10",
        next_level_label=None,
        next_xp_required=None,
        bot=bot,
    )

    assert embed.title == "📊 Ton profil XP"
    assert embed.author and embed.author["name"] == "Alice"
    assert any(f["name"] == "Progression" and "Niveau maximum" in f["value"] for f in embed.fields)
    assert len(files) == 2


@pytest.mark.asyncio
async def test_generate_xp_profile_embed_next_level_remaining():
    import eldoria.features.embed.xpEmbed as mod

    bot = FakeBot(FakeGuild(123, name="Srv"))
    user = FakeMember("<@99>", display_name="Bob", member_id=99)

    embed, _files = await mod.generate_xp_profile_embed(
        guild_id=123,
        user=user,
        xp=80,
        level=3,
        level_label="lvl3",
        next_level_label="lvl4",
        next_xp_required=100,
        bot=bot,
    )

    next_field = next(f for f in embed.fields if f["name"] == "Prochain niveau")
    assert "Seuil : **100 XP**" in next_field["value"]
    assert "XP restante : **20 XP**" in next_field["value"]


@pytest.mark.asyncio
async def test_generate_xp_roles_embed_empty_and_non_empty():
    import eldoria.features.embed.xpEmbed as mod

    bot = FakeBot(FakeGuild(123))
    embed_empty, _ = await mod.generate_xp_roles_embed([], 123, bot)
    assert embed_empty.fields and embed_empty.fields[0]["name"] == "Aucune configuration"

    guild = FakeGuild(123)
    guild.add_role(FakeRole(777))
    bot2 = FakeBot(guild)

    embed, _ = await mod.generate_xp_roles_embed([(1, 10, None), (2, 50, 777)], 123, bot2)
    value = embed.fields[0]["value"]

    assert "**Niveau 1**" in value and "lvl1" in value and "**10 XP**" in value
    assert "**Niveau 2**" in value and "<@&777>" in value and "**50 XP**" in value
