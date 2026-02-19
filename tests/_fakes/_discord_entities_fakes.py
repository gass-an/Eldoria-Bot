from __future__ import annotations

from dataclasses import dataclass


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


class FakeVoiceChannel:
    def __init__(self, channel_id: int, name: str = "Vocal"):
        self.id = channel_id
        self.name = name
        self.mention = f"<#{channel_id}>"


class FakeGuild:
    def __init__(
        self,
        guild_id: int = 123,
        *,
        tag: str | None = "ELD",
        voice_channels: list[FakeVoiceChannel] | None = None,
    ):
        self.id = guild_id
        self.tag = tag
        self.voice_channels = voice_channels or []
        self._channels = {ch.id: ch for ch in self.voice_channels}

    def get_channel(self, channel_id: int):
        return self._channels.get(channel_id)



class FakeMember:
    def __init__(
        self,
        member_id: int = 42,
        *,
        bot: bool = False,
        primary_guild: FakePrimaryGuild | None = None,
        voice: FakeVoiceState | None = None,
    ):
        self.id = member_id
        self.bot = bot
        self.primary_guild = primary_guild
        self.voice = voice


class FakeDisplayMember:
    def __init__(self, name: str):
        self.display_name = name


class FakeMessage:
    def __init__(self, *, guild: FakeGuild, author: FakeMember, content: str):
        self.guild = guild
        self.author = author
        self.content = content


class FakeRole:
    def __init__(self, role_id: int):
        self.id = role_id
        self.mention = f"<@&{role_id}>"


class FakeAvatar:
    def __init__(self, url: str):
        self.url = url
