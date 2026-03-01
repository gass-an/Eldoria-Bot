import discord  # type: ignore
import pytest

from eldoria.exceptions.general import ChannelRequired, GuildRequired, MemberNotFound, UserRequired
from eldoria.exceptions.role import InvalidLink
from eldoria.utils.discord_utils import (
    extract_id_from_link,
    find_channel_id,
    get_member_by_id_or_raise,
    get_text_or_thread_channel,
    require_guild,
    require_user_id,
)

# ------------------------------------------------------------
# Fakes (no local `class` allowed)
# ------------------------------------------------------------

def _channel_init(self, channel_id: int, *, behavior: str = "ok"):
    self.id = channel_id
    self._behavior = behavior


async def _channel_fetch_message(self, message_id: int):
    if self._behavior == "not_found":
        raise discord.NotFound()  # type: ignore
    if self._behavior == "forbidden":
        raise discord.Forbidden()  # type: ignore
    return {"id": message_id}


ChannelStub = type(
    "ChannelStub",
    (),
    {"__init__": _channel_init, "fetch_message": _channel_fetch_message},
)


def _guild_init(self, guild_id: int, text_channels):
    self.id = guild_id
    self.text_channels = list(text_channels)
    self._members = {}
    self._fetch_members = {}
    self.fetch_called = []


def _guild_add_member_cached(self, member_id: int, member_obj: object):
    self._members[member_id] = member_obj


def _guild_add_member_fetchable(self, member_id: int, member_obj: object):
    self._fetch_members[member_id] = member_obj


def _guild_get_member(self, member_id: int):
    return self._members.get(member_id)


async def _guild_fetch_member(self, member_id: int):
    self.fetch_called.append(member_id)
    if member_id in self._fetch_members:
        return self._fetch_members[member_id]
    raise discord.NotFound()  # type: ignore


GuildStub = type(
    "GuildStub",
    (),
    {
        "__init__": _guild_init,
        "add_member_cached": _guild_add_member_cached,
        "add_member_fetchable": _guild_add_member_fetchable,
        "get_member": _guild_get_member,
        "fetch_member": _guild_fetch_member,
    },
)


def _bot_init(self, *, guild_by_id=None, channel_by_id=None, fetch_channel_by_id=None):
    self._guilds = dict(guild_by_id or {})
    self._channels = dict(channel_by_id or {})
    self._fetch_channels = dict(fetch_channel_by_id or {})
    self.fetch_channel_called = []


def _bot_get_guild(self, guild_id: int):
    return self._guilds.get(guild_id)


def _bot_get_channel(self, channel_id: int):
    return self._channels.get(channel_id)


async def _bot_fetch_channel(self, channel_id: int):
    self.fetch_channel_called.append(channel_id)
    return self._fetch_channels.get(channel_id)


BotStub = type(
    "BotStub",
    (),
    {"__init__": _bot_init, "get_guild": _bot_get_guild, "get_channel": _bot_get_channel, "fetch_channel": _bot_fetch_channel},
)


DummyMessageable = type(
    "DummyMessageable",
    (discord.abc.Messageable,),  # type: ignore
    {},
)


InteractionStub = type("InteractionStub", (), {})


def make_interaction(*, guild=None, user=None):
    inter = InteractionStub()
    inter.guild = guild
    inter.user = user
    return inter


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
def test_extract_id_from_link_invalid_raises(link):
    with pytest.raises(InvalidLink):
        extract_id_from_link(link)


# ------------------------------------------------------------
# Tests find_channel_id
# ------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_channel_id_returns_none_when_guild_not_found():
    bot = BotStub(guild_by_id={})
    assert await find_channel_id(bot, message_id=1, guild_id=999) is None


@pytest.mark.asyncio
async def test_find_channel_id_returns_channel_id_when_message_found():
    g = GuildStub(
        123,
        text_channels=[ChannelStub(10, behavior="not_found"), ChannelStub(11, behavior="ok")],
    )
    bot = BotStub(guild_by_id={123: g})
    assert await find_channel_id(bot, message_id=42, guild_id=123) == 11


@pytest.mark.asyncio
async def test_find_channel_id_skips_forbidden_and_not_found_then_none():
    g = GuildStub(
        123,
        text_channels=[
            ChannelStub(10, behavior="not_found"),
            ChannelStub(11, behavior="forbidden"),
            ChannelStub(12, behavior="not_found"),
        ],
    )
    bot = BotStub(guild_by_id={123: g})
    assert await find_channel_id(bot, message_id=42, guild_id=123) is None


# ------------------------------------------------------------
# get_member_by_id_or_raise
# ------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_member_by_id_or_raise_uses_cache_first():
    g = GuildStub(1, text_channels=[])
    m = object()
    g.add_member_cached(42, m)

    assert await get_member_by_id_or_raise(g, 42) is m


@pytest.mark.asyncio
async def test_get_member_by_id_or_raise_fetches_when_missing_cache():
    g = GuildStub(1, text_channels=[])
    m = object()
    g.add_member_fetchable(42, m)

    assert await get_member_by_id_or_raise(g, 42) is m
    assert g.fetch_called == [42]


@pytest.mark.asyncio
async def test_get_member_by_id_or_raise_raises_when_not_found():
    g = GuildStub(1, text_channels=[])

    with pytest.raises(MemberNotFound):
        await get_member_by_id_or_raise(g, 999)


# ------------------------------------------------------------
# require_user_id / require_guild
# ------------------------------------------------------------

def test_require_user_id_raises_when_user_missing():
    with pytest.raises(UserRequired):
        require_user_id(make_interaction(user=None))


def test_require_user_id_returns_id_when_present():
    u = type("U", (), {"id": 123})()
    assert require_user_id(make_interaction(user=u)) == 123


def test_require_guild_raises_when_guild_missing():
    with pytest.raises(GuildRequired):
        require_guild(make_interaction(guild=None))


def test_require_guild_returns_guild_when_present():
    g = object()
    assert require_guild(make_interaction(guild=g)) is g


# ------------------------------------------------------------
# get_text_or_thread_channel
# ------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_text_or_thread_channel_uses_cache_when_present():
    ch = discord.TextChannel()  # type: ignore
    bot = BotStub(channel_by_id={10: ch})

    got = await get_text_or_thread_channel(bot, 10)
    assert got is ch
    assert bot.fetch_channel_called == []


@pytest.mark.asyncio
async def test_get_text_or_thread_channel_fetches_when_not_cached():
    ch = discord.Thread()  # type: ignore
    bot = BotStub(channel_by_id={}, fetch_channel_by_id={10: ch})

    got = await get_text_or_thread_channel(bot, 10)
    assert got is ch
    assert bot.fetch_channel_called == [10]


@pytest.mark.asyncio
async def test_get_text_or_thread_channel_raises_when_not_messageable_type():
    bot = BotStub(channel_by_id={10: DummyMessageable()})
    with pytest.raises(ChannelRequired):
        await get_text_or_thread_channel(bot, 10)
