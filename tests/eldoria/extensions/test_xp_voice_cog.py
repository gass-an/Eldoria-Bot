from __future__ import annotations

import sys
import types

import pytest


# ---------- Local stubs / shims (complements tests/conftest.py stubs) ----------
def _ensure_discord_stubs() -> None:
    """
    Ensure minimal discord.py surface used by this module exists at import-time.
    The source does not use `from __future__ import annotations`, so some annotations
    are evaluated at import time.
    """
    if "discord" not in sys.modules:
        sys.modules["discord"] = types.ModuleType("discord")
    discord = sys.modules["discord"]

    # Exceptions
    for exc_name in ("Forbidden", "HTTPException", "NotFound"):
        if not hasattr(discord, exc_name):
            setattr(discord, exc_name, type(exc_name, (Exception,), {}))

    # AllowedMentions
    if not hasattr(discord, "AllowedMentions"):
        class AllowedMentions:  # pragma: no cover
            def __init__(self, **kw):
                self.kw = kw
        discord.AllowedMentions = AllowedMentions

    # discord.utils.get
    if not hasattr(discord, "utils"):
        discord.utils = types.SimpleNamespace()
    if not hasattr(discord.utils, "get"):
        def _get(iterable, **attrs):
            for obj in iterable:
                ok = True
                for k, v in attrs.items():
                    if getattr(obj, k, None) != v:
                        ok = False
                        break
                if ok:
                    return obj
            return None
        discord.utils.get = _get

    # Types used in annotations
    for name in ("Guild", "TextChannel", "Member", "VoiceState"):
        if not hasattr(discord, name):
            setattr(discord, name, type(name, (), {}))

    # discord.ext stubs
    if "discord.ext" not in sys.modules:
        sys.modules["discord.ext"] = types.ModuleType("discord.ext")
    if "discord.ext.commands" not in sys.modules:
        sys.modules["discord.ext.commands"] = types.ModuleType("discord.ext.commands")
    if "discord.ext.tasks" not in sys.modules:
        sys.modules["discord.ext.tasks"] = types.ModuleType("discord.ext.tasks")

    commands = sys.modules["discord.ext.commands"]

    if not hasattr(commands, "Cog"):
        class Cog:  # pragma: no cover
            @classmethod
            def listener(cls, *_a, **_k):
                def deco(fn):
                    return fn
                return deco
        commands.Cog = Cog
    


_ensure_discord_stubs()

# ---------- Import module under test (adjust if needed) ----------
import eldoria.extensions.xp_voice as xv_mod  # noqa: E402
from eldoria.extensions.xp_voice import (  # noqa: E402
    XpVoice,
    _pick_voice_levelup_text_channel,
    setup,
)


# ---------- Fakes ----------
class _FakePerms:
    def __init__(self, send_messages: bool = True):
        self.send_messages = send_messages


class _FakeTextChannel(sys.modules["discord"].TextChannel):
    def __init__(self, name: str, channel_id: int = 1, *, can_send: bool = True):
        self.name = name
        self.id = channel_id
        self.sent = []
        self._can_send = can_send

    def permissions_for(self, _member):
        return _FakePerms(send_messages=self._can_send)

    async def send(self, content: str, **kwargs):
        self.sent.append({"content": content, **kwargs})


class _FakeVoiceChannel:
    def __init__(self, members=None):
        self.members = list(members or [])


class _FakeMember(sys.modules["discord"].Member):
    def __init__(self, member_id: int, guild, *, mention: str | None = None, bot: bool = False):
        self.id = member_id
        self.guild = guild
        self.mention = mention or f"<@{member_id}>"
        self.bot = bot


class _FakeBotUser:
    def __init__(self, user_id: int = 999):
        self.id = user_id


class _FakeGuild(sys.modules["discord"].Guild):
    def __init__(self, guild_id: int):
        self.id = guild_id
        self.system_channel = None
        self.text_channels = []
        self.voice_channels = []
        self.me = None  # can be set
        self._members = {}
        self._channels = {}

    def get_member(self, user_id: int):
        return self._members.get(user_id)

    def get_channel(self, channel_id: int):
        return self._channels.get(channel_id)


class _FakeVoiceState(sys.modules["discord"].VoiceState):
    def __init__(self, channel=None, *, mute=False, deaf=False, self_mute=False, self_deaf=False):
        self.channel = channel
        self.mute = mute
        self.deaf = deaf
        self.self_mute = self_mute
        self.self_deaf = self_deaf


class _FakeXpService:
    def __init__(self):
        self.calls = []
        self._cfg = {"enabled": True, "voice_enabled": True, "voice_levelup_channel_id": 0}
        self._role_ids = []

        # behavior controls
        self._is_active = True
        self._tick_return = None  # None or (new_xp,new_lvl,old_lvl)
        self._voice_upsert_raises = False
        self._ensure_raises = False

    def ensure_defaults(self, guild_id: int):
        self.calls.append(("ensure_defaults", guild_id))
        if self._ensure_raises:
            raise RuntimeError("ensure")

    def get_config(self, guild_id: int):
        self.calls.append(("get_config", guild_id))
        return dict(self._cfg)

    def is_voice_member_active(self, member):
        self.calls.append(("is_voice_member_active", getattr(member, "id", None)))
        return self._is_active and not getattr(member, "bot", False)

    def voice_upsert_progress(self, guild_id: int, user_id: int, *, last_tick_ts: int):
        self.calls.append(("voice_upsert_progress", guild_id, user_id, last_tick_ts))
        if self._voice_upsert_raises:
            raise RuntimeError("upsert")

    async def tick_voice_xp_for_member(self, guild, member):
        self.calls.append(("tick_voice_xp_for_member", guild.id, member.id))
        return self._tick_return

    def get_role_ids(self, guild_id: int):
        self.calls.append(("get_role_ids", guild_id))
        return list(self._role_ids)


class _FakeServices:
    def __init__(self, xp: _FakeXpService):
        self.xp = xp


class _FakeBot:
    def __init__(self, xp: _FakeXpService):
        self.services = _FakeServices(xp)
        self.user = _FakeBotUser(999)
        self.guilds = []

    async def wait_until_ready(self):
        return None


# ---------- Tests: helper _pick_voice_levelup_text_channel ----------
def test_pick_voice_levelup_text_channel_prefers_configured_id():
    g = _FakeGuild(1)
    ch_cfg = _FakeTextChannel("cfg", channel_id=10)
    g._channels[10] = ch_cfg
    cfg = {"voice_levelup_channel_id": 10}

    assert _pick_voice_levelup_text_channel(g, cfg) is ch_cfg


def test_pick_voice_levelup_text_channel_falls_back_to_system_channel_and_names():
    g = _FakeGuild(1)
    sys_ch = _FakeTextChannel("system", channel_id=20)
    g.system_channel = sys_ch

    assert _pick_voice_levelup_text_channel(g, {"voice_levelup_channel_id": 0}) is sys_ch

    # if no system channel, find by preferred name
    g2 = _FakeGuild(2)
    g2.system_channel = None
    preferred = _FakeTextChannel("general", channel_id=30)
    g2.text_channels = [preferred]

    assert _pick_voice_levelup_text_channel(g2, {"voice_levelup_channel_id": 0}) is preferred


# ---------- Tests: XpVoice lifecycle ----------
def test_xpvoice_init_starts_loop():
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = XpVoice(bot)

    assert cog.voice_xp_loop.started is True  # provided by loop wrapper
    assert cog.xp is xp


def test_cog_unload_cancels_loop_no_throw():
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = XpVoice(bot)

    cog.cog_unload()
    assert cog.voice_xp_loop.cancelled is True


def test_cog_unload_ignores_cancel_errors(monkeypatch):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = XpVoice(bot)

    def cancel_raises():
        raise RuntimeError("no")

    cog.voice_xp_loop.cancel = cancel_raises  # type: ignore[attr-defined]
    cog.cog_unload()  # doit ignorer


# ---------- Tests: voice_xp_loop behavior ----------
@pytest.mark.asyncio
async def test_voice_xp_loop_skips_when_disabled_or_voice_disabled(monkeypatch):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    g = _FakeGuild(1)
    bot.guilds = [g]
    cog = XpVoice(bot)

    xp._cfg = {"enabled": False, "voice_enabled": True, "voice_levelup_channel_id": 0}
    await cog.voice_xp_loop()
    assert ("get_config", 1) in xp.calls

    xp.calls.clear()
    xp._cfg = {"enabled": True, "voice_enabled": False, "voice_levelup_channel_id": 0}
    await cog.voice_xp_loop()
    assert ("get_config", 1) in xp.calls


@pytest.mark.asyncio
async def test_voice_xp_loop_updates_last_tick_when_solo(monkeypatch):
    # solo / only 1 active member -> voice_upsert_progress called
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    g = _FakeGuild(1)
    bot.guilds = [g]
    cog = XpVoice(bot)

    m1 = _FakeMember(1, g)
    vc = _FakeVoiceChannel([m1])
    g.voice_channels = [vc]

    monkeypatch.setattr(xv_mod, "now_ts", lambda: 123, raising=True)

    await cog.voice_xp_loop()

    assert ("voice_upsert_progress", 1, 1, 123) in xp.calls


@pytest.mark.asyncio
async def test_voice_xp_loop_skips_empty_voice_channels(monkeypatch):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    g = _FakeGuild(1)
    bot.guilds = [g]
    cog = XpVoice(bot)

    # members empty -> continue (ligne 92-93)
    g.voice_channels = [_FakeVoiceChannel([])]
    await cog.voice_xp_loop()


@pytest.mark.asyncio
async def test_voice_xp_loop_solo_upsert_errors_are_swallowed(monkeypatch):
    xp = _FakeXpService()
    xp._voice_upsert_raises = True
    bot = _FakeBot(xp)
    g = _FakeGuild(1)
    bot.guilds = [g]
    cog = XpVoice(bot)

    m1 = _FakeMember(1, g)
    g.voice_channels = [_FakeVoiceChannel([m1])]

    monkeypatch.setattr(xv_mod, "now_ts", lambda: 123, raising=True)
    await cog.voice_xp_loop()  # ne doit pas lever


@pytest.mark.asyncio
async def test_voice_xp_loop_tick_returns_none_noop(monkeypatch):
    xp = _FakeXpService()
    xp._tick_return = None
    bot = _FakeBot(xp)
    g = _FakeGuild(1)
    bot.guilds = [g]
    cog = XpVoice(bot)

    m1 = _FakeMember(1, g)
    m2 = _FakeMember(2, g)
    g.voice_channels = [_FakeVoiceChannel([m1, m2])]

    await cog.voice_xp_loop()  # ne doit pas lever


@pytest.mark.asyncio
async def test_voice_xp_loop_no_level_up_no_send(monkeypatch):
    xp = _FakeXpService()
    xp._tick_return = (10, 2, 2)  # new_lvl <= old_lvl
    bot = _FakeBot(xp)
    g = _FakeGuild(1)
    bot.guilds = [g]
    cog = XpVoice(bot)

    m1 = _FakeMember(1, g)
    m2 = _FakeMember(2, g)
    g.voice_channels = [_FakeVoiceChannel([m1, m2])]

    txt = _FakeTextChannel("general", channel_id=50, can_send=True)
    g.text_channels = [txt]
    g.me = _FakeMember(999, g)

    await cog.voice_xp_loop()
    assert txt.sent == []


@pytest.mark.asyncio
async def test_voice_xp_loop_send_errors_are_swallowed(monkeypatch):
    xp = _FakeXpService()
    xp._tick_return = (10, 2, 1)  # would level up
    bot = _FakeBot(xp)
    g = _FakeGuild(1)
    bot.guilds = [g]
    cog = XpVoice(bot)

    m1 = _FakeMember(1, g)
    m2 = _FakeMember(2, g)
    g.voice_channels = [_FakeVoiceChannel([m1, m2])]

    class BoomChannel(_FakeTextChannel):
        async def send(self, *_a, **_k):
            raise RuntimeError("boom")

    txt = BoomChannel("general", channel_id=50, can_send=True)
    g.text_channels = [txt]
    g.me = _FakeMember(999, g)

    monkeypatch.setattr(xv_mod, "level_mention", lambda *_a, **_k: "@lvl2", raising=True)

    await cog.voice_xp_loop()  # ne doit pas lever


@pytest.mark.asyncio
async def test_wait_until_ready_calls_bot(monkeypatch):
    xp = _FakeXpService()

    class Bot(_FakeBot):
        def __init__(self, xp):
            super().__init__(xp)
            self.ready_called = 0

        async def wait_until_ready(self):
            self.ready_called += 1

    bot = Bot(xp)
    cog = XpVoice(bot)
    await cog._wait_until_ready()
    assert bot.ready_called == 1


@pytest.mark.asyncio
async def test_voice_xp_loop_levelup_sends_message_when_permitted(monkeypatch):
    discord = sys.modules["discord"]
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    g = _FakeGuild(1)
    bot.guilds = [g]
    cog = XpVoice(bot)

    # 2 active members -> tick called for each active
    m1 = _FakeMember(1, g)
    m2 = _FakeMember(2, g)
    vc = _FakeVoiceChannel([m1, m2])
    g.voice_channels = [vc]

    # configure pick channel
    txt = _FakeTextChannel("general", channel_id=50, can_send=True)
    g.text_channels = [txt]

    # guild.me exists
    me = _FakeMember(999, g)
    g.me = me

    xp._tick_return = (10, 2, 1)  # level up
    xp._role_ids = [100, 200]

    monkeypatch.setattr(xv_mod, "now_ts", lambda: 123, raising=True)
    monkeypatch.setattr(xv_mod, "level_mention", lambda *_a, **_k: "@lvl2", raising=True)

    await cog.voice_xp_loop()

    assert any("Félicitations" in s["content"] for s in txt.sent)
    # AllowedMentions passed with roles=False
    sent = txt.sent[-1]
    assert isinstance(sent["allowed_mentions"], discord.AllowedMentions)
    assert sent["allowed_mentions"].kw.get("roles") is False


@pytest.mark.asyncio
async def test_voice_xp_loop_does_not_send_when_no_txt_channel_or_no_perms(monkeypatch):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    g = _FakeGuild(1)
    bot.guilds = [g]
    cog = XpVoice(bot)

    m1 = _FakeMember(1, g)
    m2 = _FakeMember(2, g)
    vc = _FakeVoiceChannel([m1, m2])
    g.voice_channels = [vc]

    xp._tick_return = (10, 2, 1)  # would level up

    # No channel found
    g.text_channels = []
    await cog.voice_xp_loop()

    # With channel but no perms
    txt = _FakeTextChannel("general", channel_id=50, can_send=False)
    g.text_channels = [txt]
    g.me = _FakeMember(999, g)

    await cog.voice_xp_loop()
    assert txt.sent == []


@pytest.mark.asyncio
async def test_voice_xp_loop_handles_exceptions_and_continues(monkeypatch):
    xp = _FakeXpService()
    bot = _FakeBot(xp)

    g1 = _FakeGuild(1)
    g2 = _FakeGuild(2)
    bot.guilds = [g1, g2]

    cog = XpVoice(bot)

    calls = {"n": 0}
    orig_ensure = xp.ensure_defaults

    def ensure_maybe(gid):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        return orig_ensure(gid)

    monkeypatch.setattr(xp, "ensure_defaults", ensure_maybe, raising=True)

    await cog.voice_xp_loop()
    # we reached at least get_config for g2
    assert ("get_config", 2) in xp.calls


# ---------- Tests: listener on_voice_state_update ----------
@pytest.mark.asyncio
async def test_voice_state_update_ignores_bots_and_missing_guild(monkeypatch):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = XpVoice(bot)

    g = _FakeGuild(1)
    bot_member = _FakeMember(10, g, bot=True)
    await cog.on_voice_state_update(bot_member, _FakeVoiceState(), _FakeVoiceState())
    assert xp.calls == []

    no_guild_member = _FakeMember(11, None)  # type: ignore[arg-type]
    no_guild_member.guild = None
    await cog.on_voice_state_update(no_guild_member, _FakeVoiceState(), _FakeVoiceState())
    assert xp.calls == []


@pytest.mark.asyncio
async def test_voice_state_update_no_relevant_change_noop(monkeypatch):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = XpVoice(bot)
    g = _FakeGuild(1)
    m = _FakeMember(1, g)

    before = _FakeVoiceState(channel=None, mute=False, deaf=False, self_mute=False, self_deaf=False)
    after = _FakeVoiceState(channel=None, mute=False, deaf=False, self_mute=False, self_deaf=False)

    await cog.on_voice_state_update(m, before, after)
    assert xp.calls == []


@pytest.mark.asyncio
async def test_voice_state_update_relevant_change_upserts_last_tick(monkeypatch):
    xp = _FakeXpService()
    bot = _FakeBot(xp)
    cog = XpVoice(bot)
    g = _FakeGuild(1)
    m = _FakeMember(1, g)

    monkeypatch.setattr(xv_mod, "now_ts", lambda: 999, raising=True)

    before = _FakeVoiceState(channel="A", mute=False)
    after = _FakeVoiceState(channel="B", mute=False)

    await cog.on_voice_state_update(m, before, after)

    assert ("ensure_defaults", 1) in xp.calls
    assert ("voice_upsert_progress", 1, 1, 999) in xp.calls


@pytest.mark.asyncio
async def test_voice_state_update_swallow_errors(monkeypatch):
    xp = _FakeXpService()
    xp._voice_upsert_raises = True
    bot = _FakeBot(xp)
    cog = XpVoice(bot)
    g = _FakeGuild(1)
    m = _FakeMember(1, g)

    monkeypatch.setattr(xv_mod, "now_ts", lambda: 999, raising=True)

    before = _FakeVoiceState(channel="A", mute=False)
    after = _FakeVoiceState(channel="B", mute=True)

    # Should not raise
    await cog.on_voice_state_update(m, before, after)


# ---------- Tests: setup ----------
def test_setup_adds_cog():
    xp = _FakeXpService()
    bot = _FakeBot(xp)

    added = {}

    def add_cog(cog):
        added["cog"] = cog

    bot.add_cog = add_cog  # type: ignore[attr-defined]

    setup(bot)
    assert isinstance(added["cog"], XpVoice)
