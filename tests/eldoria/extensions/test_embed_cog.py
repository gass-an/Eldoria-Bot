import pytest

import eldoria.extensions.embed as embed_mod
from eldoria.extensions.embed import Embed, setup
from tests._fakes import FakeBot, FakeCtx, FakeGuild, FakeMember, FakeRole, FakeTextChannel


@pytest.mark.asyncio
async def test_embed_command_opens_modal_with_selected_options(monkeypatch):
    bot = FakeBot()
    cog = Embed(bot)
    guild = FakeGuild(123)
    author = FakeMember(42, guild=guild)
    ctx = FakeCtx(guild=guild, author=author)
    channel = FakeTextChannel(456)
    role = FakeRole(789, name="Annonces")
    captured = {}

    class ModalStub:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(embed_mod, "EmbedModal", ModalStub, raising=True)

    await cog.create_embed(ctx, channel, role)

    assert captured == {
        "channel": channel,
        "author": author,
        "role": role,
    }
    assert len(ctx.modals) == 1


@pytest.mark.asyncio
async def test_embed_command_rejects_everyone_role():
    bot = FakeBot()
    cog = Embed(bot)
    guild = FakeGuild(123)
    ctx = FakeCtx(guild=guild, author=FakeMember(42, guild=guild))

    await cog.create_embed(ctx, FakeTextChannel(456), FakeRole(123, name="@everyone"))

    assert ctx.modals == []
    assert ctx.responded[-1]["ephemeral"] is True


def test_setup_adds_cog():
    bot = FakeBot()

    setup(bot)

    bot.add_cog.assert_called_once()
    assert isinstance(bot.add_cog.call_args.args[0], Embed)
