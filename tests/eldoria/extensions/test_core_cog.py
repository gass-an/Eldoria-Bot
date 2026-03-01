"""Tests du Core cog.

Les stubs Eldoria ont été factorisés dans `tests/_bootstrap/eldoria_stubs.py`.
"""

import importlib

import pytest
from _pytest.monkeypatch import MonkeyPatch

from tests._bootstrap.eldoria_stubs import install_eldoria_stubs
from tests._fakes import (
    FakeAuthor,
    FakeBot,
    FakeChannel,
    FakeGuild,
    FakeMessage,
    FakeRole,
)


@pytest.fixture()
def core_module():
    """
    Installe les stubs uniquement le temps du test, puis rollback.
    Import/reload du module testé APRÈS stubbing, sinon le module capte les vrais imports.
    """
    mp = MonkeyPatch()

    install_eldoria_stubs(mp)

    mod = importlib.import_module("eldoria.extensions.core")
    mod = importlib.reload(mod)

    yield mod

    mp.undo()


# Tests on_ready
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_on_ready_is_idempotent(core_module):
    Core = core_module.Core

    bot = FakeBot()
    cog = Core(bot)

    bot._booted = True
    await cog.on_ready()

    bot.sync_commands.assert_not_called()


@pytest.mark.asyncio
async def test_on_ready_sets_booted_and_syncs(core_module, monkeypatch):
    Core = core_module.Core
    import time as _time

    bot = FakeBot()
    cog = Core(bot)

    # temps contrôlé
    t = {"v": 10.0}

    def fake_perf_counter():
        t["v"] += 0.5
        return t["v"]

    monkeypatch.setattr(_time, "perf_counter", fake_perf_counter)

    bot._booted = False
    bot._started_at = 10.0
    await cog.on_ready()

    assert bot._booted is True
    bot.sync_commands.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_ready_sync_exception_is_caught(core_module):
    Core = core_module.Core

    bot = FakeBot()
    bot.sync_commands.side_effect = RuntimeError("boom")
    cog = Core(bot)

    # ne doit pas lever
    await cog.on_ready()
    bot.sync_commands.assert_awaited_once()


# ---------------------------------------------------------------------------
# Tests on_message (router)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_on_message_ignores_bot_messages(core_module):
    Core = core_module.Core

    bot = FakeBot()
    cog = Core(bot)

    guild = FakeGuild()
    msg = FakeMessage(bot_user=bot.user, author=bot.user, guild=guild, content="hi")

    await cog.on_message(msg)
    bot.process_commands.assert_not_called()


@pytest.mark.asyncio
async def test_on_message_ignores_dm_messages(core_module):
    Core = core_module.Core

    bot = FakeBot()
    cog = Core(bot)

    author = FakeAuthor()
    msg = FakeMessage(bot_user=bot.user, author=author, guild=None, content="hi")

    await cog.on_message(msg)
    bot.process_commands.assert_not_called()


@pytest.mark.asyncio
async def test_on_message_xp_no_result_still_processes_commands(core_module):
    Core = core_module.Core

    bot = FakeBot()
    cog = Core(bot)

    guild = FakeGuild()
    author = FakeAuthor()
    msg = FakeMessage(bot_user=bot.user, author=author, guild=guild, content="hello")

    bot.services.xp.handle_message_xp.return_value = None

    await cog.on_message(msg)

    bot.services.xp.handle_message_xp.assert_awaited_once_with(msg)
    msg.reply.assert_not_called()
    bot.process_commands.assert_awaited_once_with(msg)


@pytest.mark.asyncio
async def test_on_message_xp_levelup_replies_with_mentions(core_module):
    Core = core_module.Core
    import discord  # type: ignore

    from eldoria.utils import mentions as mentions_mod  # type: ignore

    bot = FakeBot()
    cog = Core(bot)

    guild = FakeGuild(guild_id=777)
    author = FakeAuthor(mention="<@999>")
    msg = FakeMessage(bot_user=bot.user, author=author, guild=guild, content="hello")

    mentions_mod.level_mention.return_value = "<lvl2>"
    bot.services.xp.handle_message_xp.return_value = (10, 2, 1)

    await cog.on_message(msg)

    bot.services.xp.get_role_ids.assert_called_once_with(777)
    msg.reply.assert_awaited_once()
    args, kwargs = msg.reply.await_args
    assert "🎉" in args[0]
    assert "<@999>" in args[0]
    assert "<lvl2>" in args[0]
    assert isinstance(kwargs["allowed_mentions"], discord.AllowedMentions)
    assert kwargs["allowed_mentions"].roles is False

    bot.process_commands.assert_awaited_once_with(msg)


@pytest.mark.asyncio
async def test_on_message_xp_exception_is_caught_and_does_not_stop(core_module, caplog):
    Core = core_module.Core

    bot = FakeBot()
    cog = Core(bot)

    guild = FakeGuild()
    author = FakeAuthor()
    msg = FakeMessage(bot_user=bot.user, author=author, guild=guild, content="hello")

    bot.services.xp.handle_message_xp.side_effect = RuntimeError("xp boom")

    await cog.on_message(msg)

    assert "Erreur dans handle_message_xp" in caplog.text
    # même si xp plante, on traite quand même les commandes
    bot.process_commands.assert_awaited_once_with(msg)


@pytest.mark.asyncio
async def test_on_message_secret_role_success_deletes_and_adds_role(core_module):
    Core = core_module.Core

    bot = FakeBot()
    cog = Core(bot)

    role = FakeRole(55)
    guild = FakeGuild(role=role)
    author = FakeAuthor()
    channel = FakeChannel(channel_id=999)
    msg = FakeMessage(bot_user=bot.user, author=author, guild=guild, content="secret", channel=channel)

    bot.services.role.sr_match.return_value = 55

    await cog.on_message(msg)

    msg.delete.assert_awaited_once()
    author.add_roles.assert_awaited_once_with(role)
    bot.process_commands.assert_awaited_once_with(msg)


@pytest.mark.asyncio
async def test_on_message_secret_role_delete_forbidden_is_ignored(core_module):
    Core = core_module.Core
    import discord  # type: ignore

    bot = FakeBot()
    cog = Core(bot)

    role = FakeRole(55)
    guild = FakeGuild(role=role)
    author = FakeAuthor()
    msg = FakeMessage(bot_user=bot.user, author=author, guild=guild, content="secret")

    bot.services.role.sr_match.return_value = 55
    msg.delete.side_effect = discord.Forbidden()

    await cog.on_message(msg)

    # delete a levé Forbidden mais doit être swallow
    author.add_roles.assert_awaited_once_with(role)
    bot.process_commands.assert_awaited_once_with(msg)


@pytest.mark.asyncio
async def test_on_message_secret_role_add_roles_forbidden_is_ignored(core_module):
    Core = core_module.Core
    import discord  # type: ignore

    bot = FakeBot()
    cog = Core(bot)

    role = FakeRole(55)
    guild = FakeGuild(role=role)
    author = FakeAuthor()
    msg = FakeMessage(bot_user=bot.user, author=author, guild=guild, content="secret")

    bot.services.role.sr_match.return_value = 55
    author.add_roles.side_effect = discord.HTTPException()

    await cog.on_message(msg)

    # on ne veut pas d'exception
    bot.process_commands.assert_awaited_once_with(msg)


@pytest.mark.asyncio
async def test_on_message_secret_role_exception_is_caught(core_module, caplog):
    Core = core_module.Core

    bot = FakeBot()
    cog = Core(bot)

    guild = FakeGuild()
    author = FakeAuthor()
    msg = FakeMessage(bot_user=bot.user, author=author, guild=guild, content="secret")

    bot.services.role.sr_match.side_effect = RuntimeError("sr boom")

    await cog.on_message(msg)

    assert "[SecretRole] Erreur" in caplog.text
    bot.process_commands.assert_awaited_once_with(msg)


# ---------------------------------------------------------------------------
# Tests erreurs commandes slash
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exc, expected",
    [
        ("GuildRequired", "❌ Cette commande doit être utilisée sur un serveur."),
        ("ChannelRequired", "❌ Impossible de retrouver le salon associé à cette action."),
        ("MessageRequired", "❌ Le message associé à cette action est introuvable."),
    ],
)
async def test_on_application_command_error_custom_exceptions(core_module, exc, expected):
    Core = core_module.Core
    from eldoria.exceptions import general as excs
    from eldoria.utils import interactions as interactions_mod  # type: ignore

    bot = FakeBot()
    cog = Core(bot)
    interaction = object()

    err = getattr(excs, exc)()
    await cog.on_application_command_error(interaction, err)

    interactions_mod.reply_ephemeral.assert_awaited_with(interaction, expected)


@pytest.mark.asyncio
async def test_on_application_command_error_missing_permissions_formats_list(core_module):
    Core = core_module.Core
    from discord.ext import commands  # type: ignore

    from eldoria.utils import interactions as interactions_mod  # type: ignore

    bot = FakeBot()
    cog = Core(bot)
    interaction = object()

    err = commands.MissingPermissions(["ban_members", "kick_members"])
    await cog.on_application_command_error(interaction, err)

    interactions_mod.reply_ephemeral.assert_awaited_with(
        interaction, "❌ Permissions manquantes : **ban_members, kick_members**."
    )


@pytest.mark.asyncio
async def test_on_application_command_error_bot_missing_permissions_formats_list(core_module):
    Core = core_module.Core
    from discord.ext import commands  # type: ignore

    from eldoria.utils import interactions as interactions_mod  # type: ignore

    bot = FakeBot()
    cog = Core(bot)
    interaction = object()

    err = commands.BotMissingPermissions(["send_messages"])
    await cog.on_application_command_error(interaction, err)

    interactions_mod.reply_ephemeral.assert_awaited_with(
        interaction, "❌ Il me manque des permissions : **send_messages**."
    )


@pytest.mark.asyncio
async def test_on_application_command_error_missing_role(core_module):
    Core = core_module.Core
    from discord.ext import commands  # type: ignore

    from eldoria.utils import interactions as interactions_mod  # type: ignore

    bot = FakeBot()
    cog = Core(bot)
    interaction = object()

    err = commands.MissingRole("Admin")
    await cog.on_application_command_error(interaction, err)

    interactions_mod.reply_ephemeral.assert_awaited_with(
        interaction, "❌ Vous n'avez pas le rôle requis pour utiliser cette commande."
    )


@pytest.mark.asyncio
async def test_on_application_command_error_missing_any_role(core_module):
    Core = core_module.Core
    from discord.ext import commands  # type: ignore

    from eldoria.utils import interactions as interactions_mod  # type: ignore

    bot = FakeBot()
    cog = Core(bot)
    interaction = object()

    err = commands.MissingAnyRole(["Admin", "Mod"])
    await cog.on_application_command_error(interaction, err)

    interactions_mod.reply_ephemeral.assert_awaited_with(
        interaction, "❌ Vous n'avez aucun des rôles requis pour utiliser cette commande."
    )


@pytest.mark.asyncio
async def test_on_application_command_error_check_failure(core_module):
    Core = core_module.Core
    from discord.ext import commands  # type: ignore

    from eldoria.utils import interactions as interactions_mod  # type: ignore

    bot = FakeBot()
    cog = Core(bot)
    interaction = object()

    err = commands.CheckFailure("nope")
    await cog.on_application_command_error(interaction, err)

    interactions_mod.reply_ephemeral.assert_awaited_with(
        interaction, "❌ Vous ne pouvez pas utiliser cette commande."
    )


@pytest.mark.asyncio
async def test_on_application_command_error_uses_original_error(core_module):
    Core = core_module.Core
    from eldoria.exceptions import general as excs
    from eldoria.utils import interactions as interactions_mod  # type: ignore

    bot = FakeBot()
    cog = Core(bot)
    interaction = object()

    wrapper = Exception("wrapper")
    wrapper.original = excs.GuildRequired()

    await cog.on_application_command_error(interaction, wrapper)

    interactions_mod.reply_ephemeral.assert_awaited_with(
        interaction, "❌ Cette commande doit être utilisée sur un serveur."
    )


@pytest.mark.asyncio
async def test_on_application_command_error_falls_back_to_generic_message(core_module, caplog):
    Core = core_module.Core
    from eldoria.utils import interactions as interactions_mod  # type: ignore

    bot = FakeBot()
    cog = Core(bot)
    interaction = object()

    err = RuntimeError("boom")
    await cog.on_application_command_error(interaction, err)

    assert "Erreur inattendue lors de l'exécution de la commande" in caplog.text
    interactions_mod.reply_ephemeral.assert_awaited_with(
        interaction, "❌ Une erreur est survenue lors de l'exécution de la commande."
    )


# ---------------------------------------------------------------------------
# Test setup()
# ---------------------------------------------------------------------------


def test_setup_adds_cog(core_module):
    Core = core_module.Core
    setup = core_module.setup

    bot = FakeBot()
    setup(bot)
    bot.add_cog.assert_called_once()
    added = bot.add_cog.call_args.args[0]
    assert isinstance(added, Core)
    assert added.bot is bot
