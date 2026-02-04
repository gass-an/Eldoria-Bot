import pytest

# active les stubs discord.Embed/Color/File + fournit les fakes
from tests._embed_fakes import FakeBot, FakeGuild, FakeMember  # noqa: F401


@pytest.mark.asyncio
async def test_build_version_embed_contains_version_and_files():
    from eldoria.ui.version.embeds import build_version_embed
    from eldoria.version import VERSION

    embed, files = await build_version_embed()

    assert embed.title == "Eldoria"
    assert any(f["name"] == "Version" and f"v{VERSION}" in f["value"] for f in embed.fields)
    assert any(f["name"] == "Statut" for f in embed.fields)
    assert embed.footer == {"text": "Développé par Faucon98"}
    assert len(files) == 2


@pytest.mark.asyncio
async def test_build_welcome_embed_uses_welcome_message_and_avatar(monkeypatch):
    import eldoria.ui.welcome.embeds as mod

    def fake_getWelcomeMessage(guild_id, *, user, server, recent_limit):
        assert guild_id == 123
        assert user == "<@42>"
        assert server == "Eldoria"
        assert recent_limit == 10
        return ("👋 Bienvenue", "Hello <@42>", ["👋", "✨"])

    monkeypatch.setattr(mod, "getWelcomeMessage", fake_getWelcomeMessage)

    bot = FakeBot(FakeGuild(123, name="Eldoria"))
    member = FakeMember(mention="<@42>", avatar_url="https://cdn/avatar.png")

    embed, emojis = await mod.build_welcome_embed(123, member, bot)

    assert embed.title == "👋 Bienvenue"
    assert "Hello <@42>" in (embed.description or "")
    assert embed.footer == {"text": "✨ Bienvenue parmi nous."}
    assert embed.thumbnail == {"url": "https://cdn/avatar.png"}
    assert emojis == ["👋", "✨"]
