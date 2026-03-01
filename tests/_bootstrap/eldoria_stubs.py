from __future__ import annotations

"""Stubs Eldoria injectés dans sys.modules pour certains tests.

Objectif: éviter de dépendre des vrais modules `eldoria.*` lors de tests unitaires
qui ciblent uniquement une surface réduite (ex: le Core cog).

IMPORTANT: ce module ne doit modifier que `sys.modules` via un MonkeyPatch.
"""

import sys
import importlib
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock

from _pytest.monkeypatch import MonkeyPatch


def install_eldoria_stubs(mp: MonkeyPatch) -> None:
    """Installe des stubs Eldoria dans sys.modules via `mp` (rollbackable)."""

    def make_pkg(name: str) -> ModuleType:
        pkg = ModuleType(name)
        pkg.__path__ = []  # type: ignore[attr-defined]
        mp.setitem(sys.modules, name, pkg)
        return pkg

    # --- package racine
    # On NE remplace PAS `eldoria` (package réel dans src/), sinon
    # `eldoria.extensions.core` devient introuvable.
    eldoria_pkg = sys.modules.get("eldoria")
    if eldoria_pkg is None:
        eldoria_pkg = importlib.import_module("eldoria")

    # --- packages parents (stubbés)
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
    app_pkg.bot = bot_mod

    # --- eldoria.exceptions.base
    base_mod = ModuleType("eldoria.exceptions.base")

    class AppError(Exception):
        pass

    base_mod.AppError = AppError
    mp.setitem(sys.modules, "eldoria.exceptions.base", base_mod)
    exc_pkg.base = base_mod

    # --- eldoria.exceptions.general
    general_mod = ModuleType("eldoria.exceptions.general")

    class GuildRequired(AppError):
        pass

    class ChannelRequired(AppError):
        pass

    class MessageRequired(AppError):
        pass

    class XpDisabled(AppError):
        def __init__(self, guild_id: int = 0):
            super().__init__("xp disabled")
            self.guild_id = guild_id

    general_mod.GuildRequired = GuildRequired
    general_mod.ChannelRequired = ChannelRequired
    general_mod.MessageRequired = MessageRequired
    general_mod.XpDisabled = XpDisabled
    mp.setitem(sys.modules, "eldoria.exceptions.general", general_mod)
    exc_pkg.general = general_mod

    # --- eldoria.exceptions.ui.messages
    ui_exc_pkg = make_pkg("eldoria.exceptions.ui")
    exc_pkg.ui = ui_exc_pkg
    messages_mod = ModuleType("eldoria.exceptions.ui.messages")

    def _app_error_message(e):
        name = type(e).__name__
        return {
            "GuildRequired": "❌ Cette commande doit être utilisée sur un serveur.",
            "ChannelRequired": "❌ Impossible de retrouver le salon associé à cette action.",
            "MessageRequired": "❌ Le message associé à cette action est introuvable.",
        }.get(name, "❌ Une erreur est survenue.")

    messages_mod.app_error_message = MagicMock(side_effect=_app_error_message)
    mp.setitem(sys.modules, "eldoria.exceptions.ui.messages", messages_mod)
    ui_exc_pkg.messages = messages_mod

    # --- eldoria.ui.help.view
    help_view_mod = ModuleType("eldoria.ui.help.view")
    help_view_mod.send_help_menu = AsyncMock()
    mp.setitem(sys.modules, "eldoria.ui.help.view", help_view_mod)
    help_pkg.view = help_view_mod

    # --- eldoria.ui.version.embeds
    version_mod = ModuleType("eldoria.ui.version.embeds")
    version_mod.build_version_embed = AsyncMock(return_value=(object(), []))
    mp.setitem(sys.modules, "eldoria.ui.version.embeds", version_mod)
    version_pkg.embeds = version_mod

    # --- eldoria.ui.xp.embeds.status
    xp_pkg = make_pkg("eldoria.ui.xp")
    embeds_pkg = make_pkg("eldoria.ui.xp.embeds")
    ui_pkg.xp = xp_pkg
    xp_pkg.embeds = embeds_pkg

    xp_status_mod = ModuleType("eldoria.ui.xp.embeds.status")
    xp_status_mod.build_xp_status_embed = AsyncMock(return_value=(object(), []))
    mp.setitem(sys.modules, "eldoria.ui.xp.embeds.status", xp_status_mod)
    embeds_pkg.status = xp_status_mod

    # --- eldoria.utils.interactions
    interactions_mod = ModuleType("eldoria.utils.interactions")
    interactions_mod.reply_ephemeral = AsyncMock()
    interactions_mod.reply_ephemeral_embed = AsyncMock()
    mp.setitem(sys.modules, "eldoria.utils.interactions", interactions_mod)
    utils_pkg.interactions = interactions_mod

    # --- eldoria.utils.mentions
    mentions_mod = ModuleType("eldoria.utils.mentions")
    mentions_mod.level_mention = MagicMock(return_value="<lvl>")
    mp.setitem(sys.modules, "eldoria.utils.mentions", mentions_mod)
    utils_pkg.mentions = mentions_mod
