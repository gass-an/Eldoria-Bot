from __future__ import annotations

# Fake Bot minimal utilisé par les embeds XP.
# Doit juste exposer get_guild(guild_id).

class FakeBot:
    def __init__(self, guild):
        self._guild = guild
        self.get_guild_calls: list[int] = []

    def get_guild(self, gid: int):
        self.get_guild_calls.append(gid)
        return self._guild
