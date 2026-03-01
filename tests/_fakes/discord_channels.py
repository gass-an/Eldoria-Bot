from __future__ import annotations

"""Fakes de channels Discord.

Ce module centralise les channels utilisés par les tests (cogs & UI) afin que
les fichiers sous `tests/eldoria/**` ne contiennent pas de classes Fake.
"""

from typing import Any

import discord  # type: ignore

from .discord_entities import FakeMessage

_DEFAULT = object()


# L'ordre des bases est important pour éviter des conflits MRO avec les classes
# du stub discord (ex: `discord.TextChannel(Messageable, GuildChannel)`).
class FakeChannel(discord.abc.Messageable, discord.abc.GuildChannel):  # type: ignore[misc,attr-defined]
    """GuildChannel minimal.

    Certains helpers côté prod (ex: require_guild_ctx) vérifient que le channel
    est un `discord.abc.GuildChannel`.
    """

    def __init__(
        self,
        channel_id: int = 999,
        *,
        name: str = "general",
        mention: str | None = None,
        can_send: bool = True,
        guild: object | None = None,
        # Par défaut, `send()` renvoie un message avec un `id` (beaucoup de flows UI
        # l'utilisent ensuite pour appeler des services).
        # Si un test a besoin de `None`, il peut passer explicitement `send_returns=None`.
        send_returns: object | None | object = _DEFAULT,
    ):
        self.id = channel_id
        self.name = name
        self.mention = mention or f"<#{channel_id}>"

        self.guild = guild
        self._can_send = can_send
        self._send_returns = send_returns

        # Facilité pour des tests (ex: saves cog) qui envoient/fetch des messages.
        self.sent: list[dict[str, Any]] = []
        self.fetch_map: dict[int, object] = {}
        self.raise_on_fetch: type[BaseException] | None = None

        self._next_message_id: int = 1

    async def send(
        self,
        content=None,
        *,
        embed=None,
        embeds=None,
        view=None,
        file=None,
        files=None,
        attachments=None,
        **kwargs,
    ):
        # Compat: certains appels font `send("msg")` plutôt que `send(content="msg")`.
        if self._send_returns is None:
            msg = None
        elif self._send_returns is _DEFAULT:
            next_id = self._next_message_id
            self._next_message_id += 1

            # IMPORTANT: on renvoie le FakeMessage canonique (unique dans tests/_fakes/**)
            # et on lui passe tous les paramètres potentiellement utilisés par les tests.
            msg = FakeMessage(
                message_id=next_id,  # compat historique (certains tests utilisent message_id)
                content=content or "",
                channel=self,
                guild=self.guild,
                embed=embed,
                embeds=embeds,
                view=view,
                attachments=attachments,
                file=file or kwargs.get("file"),
                files=files if files is not None else kwargs.get("files"),
            )

        else:
            # Si un test veut forcer un objet custom (ou un FakeMessage préfabriqué)
            msg = self._send_returns

        self.sent.append(
            {
                "content": content,
                "embed": embed,
                "embeds": embeds,
                "view": view,
                "file": file or kwargs.get("file"),
                "files": files if files is not None else kwargs.get("files"),
                "attachments": attachments if attachments is not None else kwargs.get("attachments"),
                "kwargs": {k: v for k, v in kwargs.items() if k not in {"file", "files", "attachments"}},
                "message": msg,
            }
        )
        return msg

    def permissions_for(self, _member):
        # Used by xp_voice to pick a channel that can receive messages.
        class _Perms:
            def __init__(self, send_messages: bool):
                self.send_messages = send_messages

        return _Perms(send_messages=self._can_send)

    async def fetch_message(self, mid: int):
        if self.raise_on_fetch:
            raise self.raise_on_fetch
        return self.fetch_map.get(mid)


class FakeTextChannel(FakeChannel, discord.TextChannel):  # type: ignore[misc]
    """TextChannel-like.

    Certains morceaux de code testent `isinstance(channel, discord.TextChannel)`.
    """


class FakeVoiceChannel:
    def __init__(
        self,
        channel_id: int,
        name: str = "Vocal",
        *,
        category=None,
        bitrate: int = 64,
    ):
        self.id = channel_id
        self.name = name
        self.category = category
        self.bitrate = bitrate
        self.mention = f"<#{channel_id}>"

        self.user_limit: int | None = None

        # Temp voice
        self.members: list[object] = []
        self.deleted = False
        self._delete_raises: BaseException | None = None

    async def edit(self, *, user_limit: int, **_kwargs):
        self.user_limit = user_limit

    async def delete(self):
        self.deleted = True
        if self._delete_raises:
            raise self._delete_raises


class FakeFetchMessageChannel(FakeChannel):
    """Channel qui supporte fetch_message() avec un FakeMessage canonique."""

    def __init__(self, channel_id: int = 999, *, message: FakeMessage | None = None):
        super().__init__(channel_id)
        self.fetched: list[int] = []
        self.message = message or FakeMessage(message_id=999, content="", channel=self, guild=getattr(self, "guild", None))

    async def fetch_message(self, message_id: int):
        self.fetched.append(message_id)
        return self.message


class FakeReactionChannel(discord.TextChannel):  # type: ignore[misc]
    """TextChannel qui sait fetch un message (utilisé par ReactionRoles)."""

    def __init__(self, message):
        self._message = message

    async def fetch_message(self, _message_id: int):
        return self._message