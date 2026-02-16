from __future__ import annotations

# Petites entités discord-like pour les embeds/profiles.

class FakeAvatar:
    def __init__(self, url: str):
        self.url = url


class FakeGuild:
    def __init__(self, name: str):
        self.name = name
