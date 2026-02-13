import importlib
import sys
from dataclasses import dataclass
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from _pytest.monkeypatch import MonkeyPatch

# ---------------------------------------------------------------------------
# Stubs de dépendances Eldoria + extensions du stub discord présent dans conftest
# ---------------------------------------------------------------------------


def _ensure_discord_ext_commands_stub(mp: MonkeyPatch) -> None:
    """
    tests/conftest.py installe un stub minimal de discord + discord.ext.commands.
    Pour ce cog, il manque quelques symboles (Cog, decorators, exceptions…).
    On les ajoute ici de façon rétro-compatible (sans dépendre de discord.py).

    IMPORTANT: utiliser mp.setitem pour pouvoir rollback proprement.
    """
    import discord  # type: ignore

    # -----------------------
    # discord.AllowedMentions
    # -----------------------
    if not hasattr(discord, "AllowedMentions"):

        @dataclass
        class AllowedMentions:  # pragma: no cover
            users: bool = False
            roles: bool = False
            replied_user: bool = False

        discord.AllowedMentions = AllowedMentions  # type: ignore[attr-defined]

    # -----------------------
    # discord.ext.commands
    # -----------------------
    commands_mod = sys.modules.get("discord.ext.commands")
    if commands_mod is None:
        commands_mod = ModuleType("discord.ext.commands")
        mp.setitem(sys.modules, "discord.ext.commands", commands_mod)

    # Base exceptions / checks
    class CheckFailure(Exception):
        pass

    class MissingRole(CheckFailure):
        pass

    class MissingAnyRole(CheckFailure):
        pass

    class MissingPermissions(CheckFailure):
        def __init__(self, missing_permissions):
            super().__init__("Missing permissions")
            self.missing_permissions = list(missing_permissions)

    class BotMissingPermissions(CheckFailure):
        def __init__(self, missing_permissions):
            super().__init__("Bot missing permissions")
            self.missing_permissions = list(missing_permissions)

    # Cog + decorators
    class Cog:
        @staticmethod
        def listener(name: str | None = None):
            def deco(func):
                return func

            return deco

    def slash_command(*, name: str, description: str = ""):
        def deco(func):
            # conserve juste des infos pour debug éventuel
            setattr(func, "__slash_name__", name)
            setattr(func, "__slash_description__", description)
            return func

        return deco

    # Toujours écraser ces deux-là (compat avec ton code prod)
    setattr(commands_mod, "MissingPermissions", MissingPermissions)
    setattr(commands_mod, "BotMissingPermissions", BotMissingPermissions)

    # Le reste seulement si absent (ok)
    for k, v in {
        "Cog": Cog,
        "slash_command": slash_command,
        "CheckFailure": CheckFailure,
        "MissingRole": MissingRole,
        "MissingAnyRole": MissingAnyRole,
    }.items():
        if not hasattr(commands_mod, k):
            setattr(commands_mod, k, v)


def _install_eldoria_stubs(mp: MonkeyPatch) -> None:
    """
    Installe des stubs Eldoria dans sys.modules.
    IMPORTANT:
    - On remplace AUSSI les packages parents, même s'ils existent déjà, sinon
      Python continue d'utiliser les vrais modules déjà importés.
    - On crée des ModuleType NEUFS (pas de sys.modules.get(...) ) pour ne pas muter les vrais modules.
    - On relie les sous-modules aux packages (pkg.sub = mod) pour que
      `from eldoria.utils import interactions` fonctionne.
    """
    def make_pkg(name: str) -> ModuleType:
        pkg = ModuleType(name)
        pkg.__path__ = []  # type: ignore[attr-defined]
        mp.setitem(sys.modules, name, pkg)
        return pkg

    # --- packages parents (TOUJOURS neufs)
    eldoria_pkg = make_pkg("eldoria")
    app_pkg = make_pkg("eldoria.app")
    exc_pkg = make_pkg("eldoria.exceptions")
    ui_pkg = make_pkg("eldoria.ui")
    help_pkg = make_pkg("eldoria.ui.help")
    version_pkg = make_pkg("eldoria.ui.version")
    utils_pkg = make_pkg("eldoria.utils")
    cogs_pkg = make_pkg("eldoria.cogs")

    # relier la hiérarchie (utile pour certains imports)
    eldoria_pkg.app = app_pkg
    eldoria_pkg.exceptions = exc_pkg
    eldoria_pkg.ui = ui_pkg
    eldoria_pkg.utils = utils_pkg
    eldoria_pkg.cogs = cogs_pkg
    ui_pkg.help = help_pkg
    ui_pkg.version = version_pkg

    # --- eldoria.app.bot
    bot_mod = ModuleType("eldoria.app.bot")

    class EldoriaBot:  # pragma: no cover
        pass

    bot_mod.EldoriaBot = EldoriaBot
    mp.setitem(sys.modules, "eldoria.app.bot", bot_mod)
    app_pkg.bot = bot_mod  # pour `from eldoria.app import bot`

    # --- eldoria.exceptions.general_exceptions
    exc_mod = ModuleType("eldoria.exceptions.general_exceptions")

    class GuildRequired(Exception):
        pass

    class ChannelRequired(Exception):
        pass

    class MessageRequired(Exception):
        pass

    exc_mod.GuildRequired = GuildRequired
    exc_mod.ChannelRequired = ChannelRequired
    exc_mod.MessageRequired = MessageRequired
    mp.setitem(sys.modules, "eldoria.exceptions.general_exceptions", exc_mod)
    exc_pkg.general_exceptions = exc_mod  # pour `from eldoria.exceptions import general_exceptions`

    # --- eldoria.ui.help.view
    help_view_mod = ModuleType("eldoria.ui.help.view")
    help_view_mod.send_help_menu = AsyncMock()
    mp.setitem(sys.modules, "eldoria.ui.help.view", help_view_mod)
    help_pkg.view = help_view_mod  # pour `from eldoria.ui.help import view`

    # --- eldoria.ui.version.embeds
    version_mod = ModuleType("eldoria.ui.version.embeds")
    version_mod.build_version_embed = AsyncMock(return_value=(object(), []))
    mp.setitem(sys.modules, "eldoria.ui.version.embeds", version_mod)
    version_pkg.embeds = version_mod  # pour `from eldoria.ui.version import embeds`

    # --- eldoria.utils.interactions
    interactions_mod = ModuleType("eldoria.utils.interactions")
    interactions_mod.reply_ephemeral = AsyncMock()
    mp.setitem(sys.modules, "eldoria.utils.interactions", interactions_mod)
    utils_pkg.interactions = interactions_mod  # pour `from eldoria.utils import interactions`

    # --- eldoria.utils.mentions
    mentions_mod = ModuleType("eldoria.utils.mentions")
    mentions_mod.level_mention = MagicMock(return_value="<lvl>")
    mp.setitem(sys.modules, "eldoria.utils.mentions", mentions_mod)
    utils_pkg.mentions = mentions_mod  # pour `from eldoria.utils import mentions`


@pytest.fixture()
def core_module():
    """
    Installe les stubs uniquement le temps du test, puis rollback.
    Import/reload du module testé APRÈS stubbing, sinon le module capte les vrais imports.
    """
    mp = MonkeyPatch()

    _ensure_discord_ext_commands_stub(mp)
    _install_eldoria_stubs(mp)

    mod = importlib.import_module("eldoria.extensions.core")
    mod = importlib.reload(mod)

    yield mod

    mp.undo()


# ---------------------------------------------------------------------------
# Fakes locaux
# ---------------------------------------------------------------------------


class FakeRole:
    def __init__(self, role_id: int):
        self.id = role_id


class FakeGuild:
    def __init__(self, guild_id: int = 123, role: FakeRole | None = None):
        self.id = guild_id
        self._role = role

    def get_role(self, role_id: int):
        if self._role and self._role.id == role_id:
            return self._role
        return None


class FakeAuthor:
    def __init__(self, *, mention: str = "<@42>"):
        self.mention = mention
        self.add_roles = AsyncMock()


class FakeChannel:
    def __init__(self, channel_id: int = 9):
        self.id = channel_id


class FakeMessage:
    def __init__(
        self,
        *,
        bot_user: object,
        author: object,
        guild: FakeGuild | None,
        content: str | None = "",
        attachments=None,
        channel: FakeChannel | None = None,
    ):
        self.author = author
        self.guild = guild
        self.content = content
        self.attachments = attachments or []
        self.channel = channel or FakeChannel()
        self.reply = AsyncMock()
        self.delete = AsyncMock()


class FakeBot:
    def __init__(self):
        self.user = object()
        self.guilds = [object(), object()]
        self.latency = 0.123

        self.services = SimpleNamespace(
            xp=SimpleNamespace(
                handle_message_xp=AsyncMock(),
                get_role_ids=MagicMock(return_value=[1, 2, 3]),
            ),
            role=SimpleNamespace(
                sr_match=MagicMock(return_value=None),
            ),
        )

        self.sync_commands = AsyncMock()
        self.process_commands = AsyncMock()
        self.add_cog = MagicMock()

        # boot fields
        self._booted = False
        self._started_at = 1.0


# ---------------------------------------------------------------------------
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
async def test_on_message_xp_exception_is_caught_and_does_not_stop(core_module, capsys):
    Core = core_module.Core

    bot = FakeBot()
    cog = Core(bot)

    guild = FakeGuild()
    author = FakeAuthor()
    msg = FakeMessage(bot_user=bot.user, author=author, guild=guild, content="hello")

    bot.services.xp.handle_message_xp.side_effect = RuntimeError("xp boom")

    await cog.on_message(msg)

    out = capsys.readouterr().out
    assert "[XP] Erreur handle message" in out
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
async def test_on_message_secret_role_exception_is_caught(core_module, capsys):
    Core = core_module.Core

    bot = FakeBot()
    cog = Core(bot)

    guild = FakeGuild()
    author = FakeAuthor()
    msg = FakeMessage(bot_user=bot.user, author=author, guild=guild, content="secret")

    bot.services.role.sr_match.side_effect = RuntimeError("sr boom")

    await cog.on_message(msg)

    out = capsys.readouterr().out
    assert "[SecretRole] Erreur" in out
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
    from eldoria.exceptions import general_exceptions as excs  # type: ignore
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
    from eldoria.exceptions import general_exceptions as excs  # type: ignore
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
async def test_on_application_command_error_falls_back_to_generic_message(core_module, capsys):
    Core = core_module.Core
    from eldoria.utils import interactions as interactions_mod  # type: ignore

    bot = FakeBot()
    cog = Core(bot)
    interaction = object()

    err = RuntimeError("boom")
    await cog.on_application_command_error(interaction, err)

    out = capsys.readouterr().out
    assert "[CommandError] RuntimeError" in out
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
