from __future__ import annotations

import discord  # type: ignore


class UserLimitModalStub:
    def __init__(self, *, on_value):
        self.on_value = on_value


class TempVoiceHomeViewStub:
    def __init__(self, *, temp_voice_service, author_id: int, guild):
        self.temp_voice_service = temp_voice_service
        self.author_id = author_id
        self.guild = guild

    def current_embed(self):
        # le code fait: embed, _ = home.current_embed()
        return (discord.Embed(title="HOME", description="OK", color=1), None)


class AddViewStub:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class RemoveViewStub:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
