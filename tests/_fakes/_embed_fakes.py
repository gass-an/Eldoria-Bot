# tests/_embed_fakes.py
"""
Helpers/fakes pour tester les embeds sans dépendre de py-cord/discord.py.

Hypothèse :
- tests/conftest.py installe déjà un stub "discord" (ModuleType + sous-modules).
- Ici, on complète uniquement Embed/Color/File si absents, et on fournit
  des fakes réutilisables (Bot/Guild/Member/Channel/Role).

Usage:
    from tests._embed_fakes import FakeBot, FakeGuild, FakeMember
"""

from __future__ import annotations

import discord  # type: ignore


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
    """
    Remplace discord.Embed.
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


# ------------------------------------------------------------
# Injection "soft" : on ne remplace pas si déjà présent.
# (Le conftest peut déjà fournir certaines classes)
# ------------------------------------------------------------
if not hasattr(discord, "Color"):
    discord.Color = FakeColor  # type: ignore[attr-defined]

if not hasattr(discord, "File"):
    discord.File = FakeFile  # type: ignore[attr-defined]

if not hasattr(discord, "Embed"):
    discord.Embed = FakeEmbed  # type: ignore[attr-defined]


# ------------------------------------------------------------
# Fakes "discord-like" utiles pour tester le rendu des embeds
# ------------------------------------------------------------
class FakeAvatar:
    def __init__(self, url: str):
        self.url = url


class FakeMember:
    def __init__(
        self,
        mention: str = "<@42>",
        *,
        avatar_url: str = "https://cdn/avatar.png",
        display_name: str | None = None,
        member_id: int = 42,
    ):
        self.mention = mention
        self.display_avatar = FakeAvatar(avatar_url)
        self.display_name = display_name or mention
        self.id = member_id


class FakeChannel:
    def __init__(self, channel_id: int):
        self.id = channel_id
        self.mention = f"<#{channel_id}>"


class FakeRole:
    def __init__(self, role_id: int):
        self.id = role_id
        self.mention = f"<@&{role_id}>"


class FakeGuild:
    def __init__(self, guild_id: int = 123, *, name: str = "Eldoria"):
        self.id = guild_id
        self.name = name
        self._channels: dict[int, FakeChannel] = {}
        self._roles: dict[int, FakeRole] = {}
        self._members: dict[int, FakeMember] = {}

    # --- channels ---
    def add_channel(self, ch: FakeChannel):
        self._channels[ch.id] = ch

    def get_channel(self, channel_id: int):
        return self._channels.get(channel_id)

    # --- roles ---
    def add_role(self, role: FakeRole):
        self._roles[role.id] = role

    def get_role(self, role_id: int):
        return self._roles.get(role_id)

    # --- members ---
    def add_member(self, member: FakeMember):
        self._members[member.id] = member

    def get_member(self, member_id: int):
        return self._members.get(member_id)


class FakeBot:
    """Suffit pour les fonctions qui font bot.get_guild()."""

    def __init__(self, guild: FakeGuild | None):
        self._guild = guild

    def get_guild(self, gid: int):
        if self._guild and self._guild.id == gid:
            return self._guild
        return None
