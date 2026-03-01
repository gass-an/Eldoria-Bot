from __future__ import annotations

"""Fakes d'entités Discord (guilds, membres, rôles, messages…).

Objectif:
- Une seule implémentation canonique par Fake* dans `tests/_fakes/**`.
- Les autres modules historiques deviennent des couches de compat (imports).

Ce module est volontairement "feuille" (pas d'import depuis d'autres fakes)
pour limiter les cycles d'import.
"""

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import discord  # type: ignore


@dataclass
class FakePrimaryGuild:
    identity_enabled: bool = False
    identity_guild_id: int | None = None
    tag: str | None = None


class FakeVoiceState:
    def __init__(
        self,
        channel: object | None,
        *,
        mute: bool = False,
        self_mute: bool = False,
        deaf: bool = False,
        self_deaf: bool = False,
    ):
        self.channel = channel
        self.mute = mute
        self.self_mute = self_mute
        self.deaf = deaf
        self.self_deaf = self_deaf


class FakeRole:
    def __init__(
        self,
        role_id: int,
        name: str = "R",
        *,
        mention: str | None = None,
        position: int = 0,
    ):
        self.id = role_id
        self.name = name
        self.position = position
        self.mention = mention or f"<@&{role_id}>"


class FakeGuild:
    def __init__(
        self,
        guild_id: int = 123,
        *,
        tag: str | None = "ELD",
        name: str = "Eldoria",
        role: FakeRole | None = None,
        roles: list[FakeRole] | None = None,
        channels: list[object] | None = None,
        channel: object | None = None,
        voice_channels: list[object] | None = None,
        me: FakeMember | None = None,
    ):
        self.id = guild_id
        self.tag = tag
        self.name = name

        base_roles = list(roles or [])
        if role is not None:
            base_roles.append(role)
        self._roles: dict[int, FakeRole] = {r.id: r for r in base_roles}

        all_channels = list(channels or [])
        if channel is not None:
            all_channels.append(channel)
        all_channels += list(voice_channels or [])
        self._channels: dict[int, object] = {
            int(getattr(ch, "id")): ch for ch in all_channels if hasattr(ch, "id")
        }

        # Certains tests (temp voice) utilisent `guild.voice_channels`.
        self.voice_channels = list(voice_channels or [])

        # Temp voice: les tests inspectent `guild.created`.
        self.created: list[dict[str, Any]] = []

        # Members (some cogs use guild.me / get_member)
        self._members: dict[int, FakeMember] = {}
        self._me = me

    def add_role(self, role: FakeRole) -> None:
        self._roles[role.id] = role

    def get_role(self, role_id: int | None):
        if not role_id:
            return None
        return self._roles.get(role_id)

    def add_channel(self, ch: object) -> None:
        ch_id = getattr(ch, "id", None)
        if ch_id is not None:
            self._channels[int(ch_id)] = ch

    def get_channel(self, channel_id: int):
        return self._channels.get(channel_id)

    def add_member(self, member: FakeMember) -> None:
        self._members[member.id] = member

    def get_member(self, user_id: int):
        if self._me is not None and user_id == getattr(self._me, "id", None):
            return self._me
        return self._members.get(user_id)

    @property
    def me(self):
        return self._me or self._members.get(999)

    async def create_voice_channel(self, **kwargs):
        """Support minimal pour `extensions.temp_voice` tests."""

        class _CreatedVoiceChannel:
            def __init__(self, channel_id: int, *, category=None, bitrate: int = 64):
                self.id = channel_id
                self.category = category
                self.bitrate = bitrate
                self.mention = f"<#{channel_id}>"
                self.members: list[object] = []
                self.deleted = False
                self._delete_raises: BaseException | None = None

            async def delete(self):
                self.deleted = True
                if self._delete_raises:
                    raise self._delete_raises

        new_id = 10_000 + len(self.created) + 1
        ch = _CreatedVoiceChannel(new_id, category=kwargs.get("category"), bitrate=kwargs.get("bitrate", 64))
        self.created.append({"kwargs": dict(kwargs), "channel": ch})
        self.add_channel(ch)
        self.voice_channels.append(ch)
        return ch


class FakeMember:
    def __init__(
        self,
        member_id: int = 42,
        guild: FakeGuild | None = None,
        *,
        bot: bool = False,
        mention: str | None = None,
        display_name: str = "User",
        avatar_url: str = "https://cdn/avatar.png",
        primary_guild: FakePrimaryGuild | None = None,
        voice: FakeVoiceState | None = None,
        with_add_roles: bool = False,
        roles: list[FakeRole] | None = None,
        top_role_position: int = 10_000,
    ):
        self.id = member_id
        self.bot = bot
        self.guild = guild
        self.mention = mention or f"<@{member_id}>"
        self.display_name = display_name
        self.display_avatar = FakeAvatar(avatar_url)
        self.primary_guild = primary_guild
        self.voice = voice

        self.roles = list(roles or [])
        self.top_role = SimpleNamespace(position=top_role_position)

        self.added: list[object] = []
        self.removed: list[object] = []
        self._raise_add: BaseException | None = None
        self._raise_remove: BaseException | None = None
        self.top_role = SimpleNamespace(position=top_role_position)

        # `with_add_roles` est conservé pour compat ; s'il est True on garde
        # une AsyncMock en plus (certains tests inspectent call args).
        if with_add_roles:
            self.add_roles = AsyncMock()  # type: ignore[attr-defined]

        # Temp voice
        self.moved_to: list[object] = []

    async def move_to(self, channel):
        self.moved_to.append(channel)

    async def add_roles(self, role):  # type: ignore[override]
        if self._raise_add:
            raise self._raise_add
        self.added.append(role)

    async def remove_roles(self, role):  # type: ignore[override]
        if self._raise_remove:
            raise self._raise_remove
        self.removed.append(role)

    def __eq__(self, other):
        return getattr(other, "id", object()) == self.id

    def __hash__(self):
        return hash(self.id)


class FakeUser:
    def __init__(self, user_id: int, *, guild_permissions: object | None = None):
        self.id = user_id
        self.guild_permissions = guild_permissions


class FakeDisplayMember:
    def __init__(self, name: str):
        self.display_name = name


class FakeAttachment:
    def __init__(self, *, filename: str = "file.bin", url: str = ""):
        self.filename = filename
        self.url = url
        self.saved_to: list[str] = []

    async def save(self, path):
        self.saved_to.append(str(path))


class FakeMessage:
    """Fake canonique unique pour simuler ``discord.Message``.

    Objectif: compat maximale avec les usages historiques des tests.

    Compat gérée :
    - Construction : ``FakeMessage('hello')`` (content), ``FakeMessage(123)`` (id),
      ``FakeMessage(id=...)``, ``FakeMessage(message_id=...)``.
    - Attributs présents : ``channel`` (avec au minimum ``id``), ``guild``, ``author``,
      ``embeds``, ``attachments``, ``view``.
    - Méthodes mockables : ``reply`` et ``delete`` doivent supporter
      ``assert_awaited_once`` / ``side_effect`` (tests utilisent AsyncMock).
    - Tracking : ``edits`` (liste de dicts) et ``reactions_added``.
    """

    def __init__(
        self,
        *args: Any,
        id: int = 0,
        message_id: int | None = None,
        content: str = "",
        author: Any = None,
        channel: Any = None,
        guild: Any = None,
        embeds: list[Any] | None = None,
        embed: Any = None,
        attachments: list[Any] | None = None,
        files: list[Any] | None = None,
        file: Any = None,
        view: Any = None,
        bot_user: Any = None,
        **_kwargs: Any,
    ):
        # Positional compat:
        #   FakeMessage('hello') -> content
        #   FakeMessage(123) -> id
        #   FakeMessage([attachment]) -> attachments
        if args:
            if len(args) == 1:
                a0 = args[0]
                if isinstance(a0, str):
                    content = a0
                elif isinstance(a0, int):
                    id = a0
                elif isinstance(a0, (list, tuple)):
                    # Historique: certains tests construisent un message avec une liste d'attachments
                    attachments = list(a0)
                else:
                    # fallback : ne pas planter, mais stocker en content
                    content = str(a0)
            else:
                # trop d'args positionnels => on fait au mieux
                content = str(args[0])

        # Compat: message_id -> id
        if message_id is not None and id == 0:
            id = message_id

        self.id: int = id
        self.content: str = content
        self.author: Any = author
        self.guild: Any = guild

        # bot_user utilisé par certains listeners (core cog)
        self._bot_user = bot_user

        # channel doit exister et avoir au minimum un id (certains cogs lisent message.channel.id)
        if channel is None:
            from types import SimpleNamespace

            channel = SimpleNamespace(id=0)
        self.channel: Any = channel

        # discord payload
        if embeds is not None:
            self.embeds: list[Any] = list(embeds)
        elif embed is not None:
            self.embeds = [embed]
        else:
            self.embeds = []

        if attachments is not None:
            self.attachments: list[Any] = list(attachments)
        elif files is not None:
            self.attachments = list(files)
        elif file is not None:
            self.attachments = [file]
        else:
            self.attachments = []

        self.view: Any = view

        # state + tracking
        self.deleted: bool = False
        self.edits: list[dict[str, Any]] = []
        self.replies: list[FakeMessage] = []  # type: ignore[name-defined]
        self.reactions: list[Any] = []
        self.reactions_added: list[Any] = []
        self.cleared_reactions: list[Any] = []
        self.cleared_all_reactions: int = 0

        # Exposer reply/delete/clear_* comme AsyncMock pour permettre les asserts pytest
        from unittest.mock import AsyncMock

        self.reply = AsyncMock(wraps=self._reply_impl)
        self.delete = AsyncMock(wraps=self._delete_impl)
        self.add_reaction = AsyncMock(wraps=self._add_reaction_impl)
        self.clear_reaction = AsyncMock(wraps=self._clear_reaction_impl)
        self.clear_reactions = AsyncMock(wraps=self._clear_reactions_impl)

    @property
    def reaction_cleared(self) -> list[Any]:
        # Compat: anciens tests
        return self.cleared_reactions

    @property
    def reactions_cleared(self) -> int:
        # Compat: anciens tests
        return self.cleared_all_reactions

    @property
    def message_id(self) -> int:
        return self.id

    @property
    def bot_user(self) -> Any:
        return self._bot_user

    async def edit(
        self,
        *,
        content: str | None = None,
        embed: Any = None,
        embeds: list[Any] | None = None,
        view: Any = None,
        attachments: list[Any] | None = None,
        files: list[Any] | None = None,
        file: Any = None,
        **_kwargs: Any,
    ) -> FakeMessage:  # type: ignore[name-defined]
        if content is not None:
            self.content = content

        # choix embed (discord.py accepte embed= ou embeds=)
        chosen_embed = None
        if embeds is not None:
            self.embeds = list(embeds)
            chosen_embed = embeds[0] if embeds else None
        elif embed is not None:
            self.embeds = [embed]
            chosen_embed = embed

        # attachments compat
        if attachments is not None:
            self.attachments = list(attachments)
        elif files is not None:
            self.attachments = list(files)
        elif file is not None:
            self.attachments = [file]

        if view is not None:
            self.view = view

        # IMPORTANT: plusieurs tests comparent exactement le dict contenu dans edits.
        # On stocke donc un dict minimal et stable.
        self.edits.append(
            {
                "content": self.content if content is not None else ("" if self.content is None else self.content),
                "embed": chosen_embed,
                "view": view,
                "files": None,
            }
        )
        return self

    # ---------- impls wrapées par AsyncMock ----------

    async def _delete_impl(self, **_kwargs: Any) -> None:
        self.deleted = True

    async def _reply_impl(
        self,
        content: str | None = None,
        *,
        embed: Any = None,
        embeds: list[Any] | None = None,
        view: Any = None,
        **_kwargs: Any,
    ) -> FakeMessage:  # type: ignore[name-defined]
        msg = FakeMessage(
            content=content or "",
            author=self.author,
            channel=self.channel,
            guild=self.guild,
            embed=embed,
            embeds=embeds,
            view=view,
            bot_user=self._bot_user,
        )
        self.replies.append(msg)
        return msg

    async def _add_reaction_impl(self, emoji: Any) -> None:
        exc = getattr(self, "_raise_add_reaction", None)
        if exc is not None:
            raise exc
        self.reactions.append(emoji)
        self.reactions_added.append(emoji)

    async def _clear_reaction_impl(self, emoji: Any, **_kwargs: Any) -> None:
        exc = getattr(self, "_raise_clear_reaction", None)
        if exc is not None:
            raise exc
        self.cleared_reactions.append(emoji)

    async def _clear_reactions_impl(self, **_kwargs: Any) -> None:
        exc = getattr(self, "_raise_clear_reactions", None)
        if exc is not None:
            raise exc
        self.cleared_all_reactions += 1


class FakeAvatar:

    def __init__(self, url: str):
        self.url = url


# ---------------------------------------------------------------------------
# Extra entities used in UI/cogs (reactions, embeds, authors)
# ---------------------------------------------------------------------------


class FakeAuthor:
    """Auteur de message reconnu comme un `discord.Member` (stub)."""

    def __init__(self, *, mention: str = "<@42>"):
        # Hérite dynamiquement du stub discord.Member pour satisfaire
        # `isinstance(author, discord.Member)`.
        self.__class__ = type(self.__class__.__name__, (discord.Member,), dict(self.__class__.__dict__))

        self.mention = mention
        self.add_roles = AsyncMock()


class FakeEmoji:
    def __init__(self, name: str = "😀"):
        self.name = name


class FakeReactionPayload:
    """Payload minimal pour les events raw_reaction_*"""

    def __init__(
        self,
        *,
        user_id: int = 1,
        guild_id: int = 1,
        channel_id: int = 1,
        message_id: int = 1,
        emoji_name: str | None = None,
        emoji: FakeEmoji | None = None,
    ):
        self.user_id = user_id
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.message_id = message_id
        if emoji is not None:
            self.emoji = emoji
        else:
            self.emoji = FakeEmoji(emoji_name or "😀")


# ------------------------------------------------------------
# Stubs Discord (Embed / Color / File)
# ------------------------------------------------------------


class FakeColor(int):
    """Remplace discord.Color (souvent un int sous le capot)."""

    def __new__(cls, value: int):
        obj = int.__new__(cls, value)
        obj.value = value  # compatibilité avec discord.Color.value
        return obj


class FakeFile:
    """Remplace discord.File (ex: envoi de fichiers/attachments)."""

    def __init__(self, fp: str, *, filename: str | None = None):
        self.fp = fp
        self.filename = filename


class FakeEmbed:
    """Remplace discord.Embed.

    On implémente uniquement les champs utilisés par le projet/tests.
    """

    def __init__(self, *, title=None, description=None, colour=None, color=None):
        self.title = title
        self.description = description
        # Discord accepte `colour` ou `color` selon versions / libs
        self.colour = colour if colour is not None else color

        self.fields: list[dict] = []
        self.footer: dict | None = None
        self.thumbnail: dict | None = None
        self.image: dict | None = None
        self.author: dict | None = None

    def add_field(self, *, name: str, value: str, inline: bool = False):
        self.fields.append({"name": name, "value": value, "inline": inline})

    def set_footer(self, *, text: str):
        self.footer = {"text": text}

    def set_thumbnail(self, *, url: str):
        self.thumbnail = {"url": url}

    def set_image(self, *, url: str):
        self.image = {"url": url}

    def set_author(self, *, name: str, icon_url: str | None = None):
        self.author = {"name": name, "icon_url": icon_url}


# Injection "soft" : on ne remplace pas si déjà présent.
if not hasattr(discord, "Color"):
    discord.Color = FakeColor  # type: ignore[attr-defined]

if not hasattr(discord, "File"):
    discord.File = FakeFile  # type: ignore[attr-defined]

if not hasattr(discord, "Embed"):
    discord.Embed = FakeEmbed  # type: ignore[attr-defined]
