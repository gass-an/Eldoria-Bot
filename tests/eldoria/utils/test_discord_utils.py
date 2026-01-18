import sys
import types

import pytest


def _ensure_discord_stubs():
    """Ensure the minimum symbols required by eldoria.utils.discord_utils exist.

    - discord.NotFound exception
    - discord.ext.commands.Bot type (for type hints/import)
    """
    discord_mod = sys.modules.get("discord")
    if discord_mod is None:
        discord_mod = types.SimpleNamespace()
        sys.modules["discord"] = discord_mod

    if not hasattr(discord_mod, "NotFound"):
        class NotFound(Exception):
            pass
        discord_mod.NotFound = NotFound

    if not hasattr(discord_mod, "Forbidden"):
        class Forbidden(Exception):
            pass
        discord_mod.Forbidden = Forbidden

    if "discord.ext" not in sys.modules:
        sys.modules["discord.ext"] = types.ModuleType("discord.ext")

    if "discord.ext.commands" not in sys.modules:
        commands_mod = types.ModuleType("discord.ext.commands")

        class Bot:  # pragma: no cover
            pass

        commands_mod.Bot = Bot
        sys.modules["discord.ext.commands"] = commands_mod
        sys.modules["discord.ext"].commands = commands_mod


_ensure_discord_stubs()


from eldoria.utils.discord_utils import extract_id_from_link, find_channel_id  # noqa: E402


class FakeChannel:
    def __init__(self, channel_id: int, *, behavior: str = "ok"):
        self.id = channel_id
        self._behavior = behavior

    async def fetch_message(self, message_id: int):
        discord_mod = sys.modules["discord"]
        if self._behavior == "not_found":
            raise discord_mod.NotFound()
        if self._behavior == "forbidden":
            raise discord_mod.Forbidden()
        return {"id": message_id}


class FakeGuild:
    def __init__(self, text_channels):
        self.text_channels = list(text_channels)


class FakeBot:
    def __init__(self, guild_by_id: dict[int, FakeGuild]):
        self._guilds = dict(guild_by_id)

    def get_guild(self, guild_id: int):
        return self._guilds.get(guild_id)


def test_extract_id_from_link_valid():
    guild_id, channel_id, message_id = extract_id_from_link(
        "https://discord.com/channels/123/456/789"
    )
    assert guild_id == 123
    assert channel_id == 456
    assert message_id == 789


@pytest.mark.parametrize(
    "link",
    [
        "http://discord.com/channels/123/456/789",
        "https://discord.com/channels/123/456",
        "https://discord.com/channels//456/789",
        "https://example.com/channels/123/456/789",
        "not a link",
        "",
    ],
)
def test_extract_id_from_link_invalid_returns_nones(link):
    assert extract_id_from_link(link) == (None, None, None)


@pytest.mark.asyncio
async def test_find_channel_id_returns_none_when_guild_not_found():
    bot = FakeBot(guild_by_id={})
    assert await find_channel_id(bot, message_id=1, guild_id=999) is None


@pytest.mark.asyncio
async def test_find_channel_id_returns_channel_id_when_message_found():
    g = FakeGuild(text_channels=[FakeChannel(10, behavior="not_found"), FakeChannel(11, behavior="ok")])
    bot = FakeBot(guild_by_id={123: g})
    assert await find_channel_id(bot, message_id=42, guild_id=123) == 11


@pytest.mark.asyncio
async def test_find_channel_id_skips_forbidden_and_not_found_then_none():
    g = FakeGuild(
        text_channels=[
            FakeChannel(10, behavior="not_found"),
            FakeChannel(11, behavior="forbidden"),
            FakeChannel(12, behavior="not_found"),
        ]
    )
    bot = FakeBot(guild_by_id={123: g})
    assert await find_channel_id(bot, message_id=42, guild_id=123) is None
