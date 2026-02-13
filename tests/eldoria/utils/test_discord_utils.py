# tests/eldoria/utils/test_discord_utils.py
import discord  # type: ignore
import pytest

from eldoria.exceptions.general_exceptions import ChannelRequired, GuildRequired, UserRequired
from eldoria.utils.discord_utils import (
    extract_id_from_link,
    find_channel_id,
    get_member_by_id_or_raise,
    get_text_or_thread_channel,
    require_guild,
    require_user,
    require_user_id,
)


# ------------------------------------------------------------
# Fakes
# ------------------------------------------------------------
class FakeChannel:
    def __init__(self, channel_id: int, *, behavior: str = "ok"):
        self.id = channel_id
        self._behavior = behavior

    async def fetch_message(self, message_id: int):
        if self._behavior == "not_found":
            raise discord.NotFound()  # type: ignore
        if self._behavior == "forbidden":
            raise discord.Forbidden()  # type: ignore
        return {"id": message_id}


class FakeGuild:
    def __init__(self, guild_id: int, text_channels):
        self.id = guild_id
        self.text_channels = list(text_channels)
        self._members: dict[int, object] = {}
        self._fetch_members: dict[int, object] = {}
        self.fetch_called: list[int] = []

    def add_member_cached(self, member_id: int, member_obj: object):
        self._members[member_id] = member_obj

    def add_member_fetchable(self, member_id: int, member_obj: object):
        self._fetch_members[member_id] = member_obj

    def get_member(self, member_id: int):
        return self._members.get(member_id)

    async def fetch_member(self, member_id: int):
        self.fetch_called.append(member_id)
        if member_id in self._fetch_members:
            return self._fetch_members[member_id]
        raise discord.NotFound()  # type: ignore


class FakeBot:
    def __init__(self, *, guild_by_id=None, channel_by_id=None, fetch_channel_by_id=None):
        self._guilds = dict(guild_by_id or {})
        self._channels = dict(channel_by_id or {})
        self._fetch_channels = dict(fetch_channel_by_id or {})
        self.fetch_channel_called: list[int] = []

    def get_guild(self, guild_id: int):
        return self._guilds.get(guild_id)

    def get_channel(self, channel_id: int):
        return self._channels.get(channel_id)

    async def fetch_channel(self, channel_id: int):
        self.fetch_channel_called.append(channel_id)
        return self._fetch_channels.get(channel_id)


class DummyMessageable(discord.abc.Messageable):  # type: ignore
    """Objet qui n'est PAS un TextChannel/Thread/DMChannel => doit déclencher ChannelRequired."""
    pass


class FakeInteraction:
    def __init__(self, *, guild=None, user=None):
        self.guild = guild
        self.user = user


# ------------------------------------------------------------
# Tests extract_id_from_link
# ------------------------------------------------------------
def test_extract_id_from_link_valid():
    guild_id, channel_id, message_id = extract_id_from_link("https://discord.com/channels/123/456/789")
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


# ------------------------------------------------------------
# Tests find_channel_id
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_find_channel_id_returns_none_when_guild_not_found():
    bot = FakeBot(guild_by_id={})
    assert await find_channel_id(bot, message_id=1, guild_id=999) is None


@pytest.mark.asyncio
async def test_find_channel_id_returns_channel_id_when_message_found():
    g = FakeGuild(
        123,
        text_channels=[FakeChannel(10, behavior="not_found"), FakeChannel(11, behavior="ok")],
    )
    bot = FakeBot(guild_by_id={123: g})
    assert await find_channel_id(bot, message_id=42, guild_id=123) == 11


@pytest.mark.asyncio
async def test_find_channel_id_skips_forbidden_and_not_found_then_none():
    g = FakeGuild(
        123,
        text_channels=[
            FakeChannel(10, behavior="not_found"),
            FakeChannel(11, behavior="forbidden"),
            FakeChannel(12, behavior="not_found"),
        ],
    )
    bot = FakeBot(guild_by_id={123: g})
    assert await find_channel_id(bot, message_id=42, guild_id=123) is None


# ------------------------------------------------------------
# Tests get_member_by_id_or_raise
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_member_by_id_or_raise_returns_cached_member():
    guild = FakeGuild(1, text_channels=[])
    cached = object()
    guild.add_member_cached(42, cached)

    result = await get_member_by_id_or_raise(guild, 42)
    assert result is cached
    assert guild.fetch_called == []


@pytest.mark.asyncio
async def test_get_member_by_id_or_raise_fetches_when_not_cached():
    guild = FakeGuild(1, text_channels=[])
    fetched = object()
    guild.add_member_fetchable(99, fetched)

    result = await get_member_by_id_or_raise(guild, 99)
    assert result is fetched
    assert guild.fetch_called == [99]


@pytest.mark.asyncio
async def test_get_member_by_id_or_raise_raises_value_error_when_not_found():
    guild = FakeGuild(777, text_channels=[])
    with pytest.raises(ValueError) as e:
        await get_member_by_id_or_raise(guild, 1234)
    assert "Member 1234 not found in guild 777" in str(e.value)


# ------------------------------------------------------------
# Tests get_text_or_thread_channel
# ------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_text_or_thread_channel_uses_cache_when_present():
    ch = discord.TextChannel()  # type: ignore
    bot = FakeBot(channel_by_id={10: ch})

    got = await get_text_or_thread_channel(bot, 10)
    assert got is ch
    assert bot.fetch_channel_called == []


@pytest.mark.asyncio
async def test_get_text_or_thread_channel_fetches_when_not_cached():
    ch = discord.Thread()  # type: ignore
    bot = FakeBot(channel_by_id={}, fetch_channel_by_id={10: ch})

    got = await get_text_or_thread_channel(bot, 10)
    assert got is ch
    assert bot.fetch_channel_called == [10]


@pytest.mark.asyncio
async def test_get_text_or_thread_channel_raises_when_not_messageable_type():
    bot = FakeBot(channel_by_id={10: DummyMessageable()})
    with pytest.raises(ChannelRequired):
        await get_text_or_thread_channel(bot, 10)


# ------------------------------------------------------------
# Tests require_guild / require_user / require_user_id
# ------------------------------------------------------------
def test_require_guild_raises_without_guild():
    inter = FakeInteraction(guild=None, user=object())
    with pytest.raises(GuildRequired):
        require_guild(inter)  # type: ignore[arg-type]


def test_require_guild_returns_guild():
    g = object()
    inter = FakeInteraction(guild=g, user=object())
    assert require_guild(inter) is g  # type: ignore[return-value]


def test_require_user_raises_without_user():
    inter = FakeInteraction(guild=object(), user=None)
    with pytest.raises(UserRequired):
        require_user(inter)  # type: ignore[arg-type]


def test_require_user_returns_user():
    u = type("U", (), {"id": 123})()
    inter = FakeInteraction(guild=object(), user=u)
    assert require_user(inter) is u  # type: ignore[return-value]


def test_require_user_id_raises_without_user():
    inter = FakeInteraction(guild=object(), user=None)
    with pytest.raises(UserRequired):
        require_user_id(inter)  # type: ignore[arg-type]


def test_require_user_id_returns_id():
    u = type("U", (), {"id": 999})()
    inter = FakeInteraction(guild=object(), user=u)
    assert require_user_id(inter) == 999
