from __future__ import annotations

"""Fakes liés au bot/ctx discord (cogs, commandes, app)."""

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import discord  # type: ignore

from tests._fakes.discord_interactions import FakeFollowup

# ---------------------------------------------------------------------------
# App/bootstrap helpers (intents + logging)
# ---------------------------------------------------------------------------


class FakeIntents:
    """Intents minimalistes (tests app)."""

    def __init__(self):
        self.message_content = False
        self.guilds = False
        self.members = False


def make_discord_intents(intents_obj: FakeIntents):
    """Factory pour monkeypatch `discord.Intents` dans les tests."""

    class DiscordIntents:
        @staticmethod
        def default():
            return intents_obj

    return DiscordIntents


class FakeLog:
    """Logger ultra-minimal utilisé par certains tests app."""

    def __init__(self, *, on_info=None):
        self._on_info = on_info

    def info(self, msg):
        if self._on_info:
            self._on_info(msg)


class FakeCtx:
    """Context minimal (ApplicationContext-like).

    Propriétés utilisées selon les tests:
    - guild, channel
    - user et/ou author
    - followup.send
    - defer(), respond()
    """

    def __init__(self, *, guild=None, user=None, author=None, channel=None, uid: int | None = None):
        from tests._fakes.discord_entities import FakeUser

        class _GuildChan(discord.abc.GuildChannel):  # type: ignore[misc]
            id: int = 0

        self.guild = guild
        if user is None and uid is not None:
            user = FakeUser(uid)
        if user is None:
            user = FakeUser(42)
        self.user = user
        self.author = author if author is not None else user
        self.channel = channel or _GuildChan()

        self.followup = FakeFollowup()
        self.deferred = False
        self.defer_ephemeral = False
        self.responded: list[dict[str, Any]] = []

    async def defer(self, ephemeral: bool = False, **_kwargs):
        self.deferred = True
        self.defer_ephemeral = ephemeral

    async def respond(self, content: str | None = None, ephemeral: bool = False, **kwargs):
        self.responded.append({"content": content, "ephemeral": ephemeral, **kwargs})


@dataclass
class FakeBotUser:
    id: int


class FakeBot:
    """Bot fake polyvalent.

Il couvre:
- tests app (run/token, started_at)
- tests de cogs (services, sync/process/add_cog)
"""

    def __init__(
        self,
        *args,
        intents: object | None = None,
        services: Any | None = None,
        user_id: int = 999,
        guild: object | None = None,
        save: object | None = None,
        duel_service=None,
        xp_service=None,
        temp_voice=None,
    ):
        from tests._fakes.eldoria_services import FakeServices

        # Compat: certains tests historiques instancient FakeBot(duel) ou FakeBot(temp_voice).
        if args:
            if len(args) != 1:
                raise TypeError("FakeBot() accepte au plus 1 argument positionnel")
            (only,) = args
            duel_markers = {
                "new_duel",
                "configure_stakes",
                "get_games",
                "accept_invite",
                "refuse_invite",
                "apply_snapshot",
                "rps_play",
                "get_duel",
                "configure_game_type",
                "get_allowed_stakes",
                "configure_stake_xp",
                "send_invite",
                "play_game_action",
                "accept_duel",
                "refuse_duel",
            }
            if duel_service is None and any(hasattr(only, m) for m in duel_markers):
                duel_service = only
            elif temp_voice is None and (hasattr(only, "list_parents") or hasattr(only, "find_parent_of_active")):
                temp_voice = only
            else:
                services = only

        self.intents = intents

        # App metadata
        self.started_at: float | None = None
        self.discord_started_at: float | None = None
        self.ran_with: str | None = None

        # Cog services
        if services is None and any(s is not None for s in (duel_service, xp_service, temp_voice, save)):
            services = FakeServices(duel=duel_service, xp=xp_service, temp_voice=temp_voice, save=save)

        # Default services used by `extensions.core` tests.
        if services is None:
            services = SimpleNamespace(
                xp=SimpleNamespace(
                    handle_message_xp=AsyncMock(return_value=None),
                    get_role_ids=MagicMock(return_value=[1, 2, 3]),
                ),
                role=SimpleNamespace(
                    sr_match=MagicMock(return_value=None),
                ),
            )
        self.services = services

        self.user = FakeBotUser(user_id)

        # Some tests expect these attributes.
        self.guilds = [object(), object()]
        self.latency = 0.123

        # Common discord.py-ish methods mocked
        self.sync_commands = AsyncMock()
        self.process_commands = AsyncMock()
        self.add_cog = MagicMock()

        # Internal registries used by a few tests
        self._guilds: dict[int, object] = {}
        self._channels: dict[int, object] = {}
        self._waited = 0

        # Certaines suites (saves) injectent un "guild" unique.
        self._single_guild = guild

        self.get_guild_calls: list[int] = []

        # Legacy flags used by a few tests
        self._booted = False
        self._started_at = 1.0

        # Startup helpers (eldoria.app.startup)
        self.loaded: list[str] = []
        self._services = services

    # --- app helpers ---
    def set_started_at(self, started_at: float):
        self.started_at = started_at

    def set_discord_started_at(self, ts: float):
        self.discord_started_at = ts

    def run(self, token: str):
        self.ran_with = token

    # --- discord-like helpers ---
    def get_guild(self, guild_id: int):
        self.get_guild_calls.append(guild_id)
        if self._single_guild is not None:
            return self._single_guild
        return self._guilds.get(guild_id)

    def get_channel(self, channel_id: int):
        return self._channels.get(channel_id)

    async def fetch_channel(self, channel_id: int):
        return self._channels[channel_id]

    async def wait_until_ready(self):
        self._waited += 1

    # --- startup helpers ---
    def set_services(self, services):
        self._services = services
        self.services = services

    def load_extension(self, name: str):
        self.loaded.append(name)


class FakeCog(SimpleNamespace):
    """Placeholder quand un test a besoin d'un objet cog."""
