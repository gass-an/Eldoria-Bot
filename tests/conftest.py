import sqlite3
import sys
import types
from dataclasses import dataclass

import pytest


# --- Stub minimal "discord" module for unit tests ---
# Le projet depend de py-cord/discord.py, mais pour ces tests unitaires on veut
# uniquement tester la logique XP. On fournit donc un module minimal "discord"
# afin que l'import de eldoria.features.xp_system fonctionne.
if "discord" not in sys.modules:
    discord_stub = types.SimpleNamespace()

    # Sous-module discord.abc
    abc_stub = types.SimpleNamespace(User=object)
    discord_stub.abc = abc_stub

    # Sous-module discord.utils.get (utilise ailleurs, pas dans ces tests)
    def _utils_get(iterable, **attrs):
        for item in iterable:
            ok = True
            for k, v in attrs.items():
                if getattr(item, k, None) != v:
                    ok = False
                    break
            if ok:
                return item
        return None

    discord_stub.utils = types.SimpleNamespace(get=_utils_get)

        # Exceptions/perms (utilise ailleurs)
    class Forbidden(Exception):
        pass

    class NotFound(Exception):
        pass

    discord_stub.Forbidden = Forbidden
    discord_stub.NotFound = NotFound

    # Types (pour les annotations)
    discord_stub.Member = object
    discord_stub.Guild = object
    discord_stub.Message = object
    discord_stub.Role = object
    discord_stub.Interaction = object  # utile pour utils.interactions

    # Sous-modules discord.ext / discord.ext.commands (type hints/imports)
    ext_mod = types.ModuleType("discord.ext")
    commands_mod = types.ModuleType("discord.ext.commands")

    class Bot:  # stub minimal
        pass

    commands_mod.Bot = Bot
    ext_mod.commands = commands_mod

    sys.modules["discord.ext"] = ext_mod
    sys.modules["discord.ext.commands"] = commands_mod

    sys.modules["discord"] = discord_stub
    sys.modules["discord.abc"] = abc_stub
    sys.modules["discord.utils"] = discord_stub.utils


# Permet d'importer le package depuis "src/" quand on lance pytest a la racine du repo.
if "src" not in sys.path:
    sys.path.insert(0, "src")


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


class FakeGuild:
    def __init__(self, guild_id: int = 123, *, tag: str | None = "ELD"):
        self.id = guild_id
        self.tag = tag


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


class FakeMessage:
    def __init__(self, *, guild: FakeGuild, author: FakeMember, content: str):
        self.guild = guild
        self.author = author
        self.content = content

@pytest.fixture(autouse=True)
def forbid_sqlite_file_creation(monkeypatch):
    real_connect = sqlite3.connect

    def guarded_connect(path, *a, **k):
        if isinstance(path, str) and path.endswith(".db"):
            raise AssertionError(f"SQLite file creation forbidden in tests: {path}")
        return real_connect(":memory:")

    monkeypatch.setattr(sqlite3, "connect", guarded_connect)