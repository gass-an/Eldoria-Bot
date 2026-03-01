from __future__ import annotations

import sys

import pytest

# ---------- Local stubs / shims (complements tests/conftest.py stubs) ----------
# ---------- Import module under test (adjust if needed) ----------
import eldoria.extensions.xp_voice as xv_mod  # noqa: E402
from eldoria.extensions.xp_voice import (  # noqa: E402
    XpVoice,
    _pick_voice_levelup_text_channel,
    setup,
)

# ---------- Fakes ----------

def _perms_init(self, send_messages: bool = True):
    self.send_messages = send_messages


PermsStub = type("PermsStub", (), {"__init__": _perms_init})


def _textch_init(self, name: str, channel_id: int = 1, *, can_send: bool = True):
    self.name = name
    self.id = channel_id
    self.sent = []
    self._can_send = can_send


def _textch_permissions_for(self, _member):
    return PermsStub(send_messages=self._can_send)


async def _textch_send(self, content: str, **kwargs):
    self.sent.append({"content": content, **kwargs})


TextChannelStub = type(
    "TextChannelStub",
    (sys.modules["discord"].TextChannel,),
    {"__init__": _textch_init, "permissions_for": _textch_permissions_for, "send": _textch_send},
)


def _voicech_init(self, members=None):
    self.members = list(members or [])


VoiceChannelStub = type("VoiceChannelStub", (), {"__init__": _voicech_init})


def _member_init(self, member_id: int, guild, *, mention: str | None = None, bot: bool = False):
    self.id = member_id
    self.guild = guild
    self.mention = mention or f"<@{member_id}>"
    self.bot = bot


MemberStub = type(
    "MemberStub",
    (sys.modules["discord"].Member,),
    {"__init__": _member_init},
)


def _botuser_init(self, user_id: int = 999):
    self.id = user_id


BotUserStub = type("BotUserStub", (), {"__init__": _botuser_init})


def _guild_init(self, guild_id: int):
    self.id = guild_id
    self.system_channel = None
    self.text_channels = []
    self.voice_channels = []
    self.me = None
    self._members = {}
    self._channels = {}


def _guild_get_member(self, user_id: int):
    return self._members.get(user_id)


def _guild_get_channel(self, channel_id: int):
    return self._channels.get(channel_id)


GuildStub = type(
    "GuildStub",
    (sys.modules["discord"].Guild,),
    {"__init__": _guild_init, "get_member": _guild_get_member, "get_channel": _guild_get_channel},
)


def _vs_init(self, channel=None, *, mute=False, deaf=False, self_mute=False, self_deaf=False):
    self.channel = channel
    self.mute = mute
    self.deaf = deaf
    self.self_mute = self_mute
    self.self_deaf = self_deaf


VoiceStateStub = type(
    "VoiceStateStub",
    (sys.modules["discord"].VoiceState,),
    {"__init__": _vs_init},
)


def _xpsvc_init(self):
    from tests._fakes import FakeXpService

    impl = FakeXpService()
    self._impl = impl
    self.calls = impl.calls
    self._cfg = impl._voice_cfg
    self._role_ids = impl._role_ids
    self._is_active = impl._voice_is_active
    self._tick_return = impl._voice_tick_return
    self._voice_upsert_raises = impl._voice_upsert_raises
    self._ensure_raises = impl._ensure_raises


def _xpsvc_ensure_defaults(self, guild_id: int):
    self.calls.append(("ensure_defaults", guild_id))
    if self._ensure_raises:
        raise RuntimeError("ensure")


def _xpsvc_get_config(self, guild_id: int):
    self.calls.append(("get_config", guild_id))
    return dict(self._cfg)


def _xpsvc_is_voice_member_active(self, member):
    self.calls.append(("is_voice_member_active", getattr(member, "id", None)))
    return self._is_active and not getattr(member, "bot", False)


def _xpsvc_voice_upsert_progress(self, guild_id: int, user_id: int, *, last_tick_ts: int):
    self.calls.append(("voice_upsert_progress", guild_id, user_id, last_tick_ts))
    if self._voice_upsert_raises:
        raise RuntimeError("upsert")


async def _xpsvc_tick_voice(self, guild, member):
    self.calls.append(("tick_voice_xp_for_member", guild.id, member.id))
    return self._tick_return


def _xpsvc_get_role_ids(self, guild_id: int):
    self.calls.append(("get_role_ids", guild_id))
    return list(self._role_ids)


XpServiceStub = type(
    "XpServiceStub",
    (),
    {
        "__init__": _xpsvc_init,
        "ensure_defaults": _xpsvc_ensure_defaults,
        "get_config": _xpsvc_get_config,
        "is_voice_member_active": _xpsvc_is_voice_member_active,
        "voice_upsert_progress": _xpsvc_voice_upsert_progress,
        "tick_voice_xp_for_member": _xpsvc_tick_voice,
        "get_role_ids": _xpsvc_get_role_ids,
    },
)


def _services_init(self, xp: XpServiceStub):
    self.xp = xp


ServicesStub = type("ServicesStub", (), {"__init__": _services_init})


def _bot_init(self, xp: XpServiceStub):
    self.services = ServicesStub(xp)
    self.user = BotUserStub(999)
    self.guilds = []


async def _bot_wait_until_ready(self):
    return None


BotStub = type("BotStub", (), {"__init__": _bot_init, "wait_until_ready": _bot_wait_until_ready})


# ---------- Tests: helper _pick_voice_levelup_text_channel ----------
def test_pick_voice_levelup_text_channel_prefers_configured_id():
    g = GuildStub(1)
    ch_cfg = TextChannelStub("cfg", channel_id=10)
    g._channels[10] = ch_cfg
    cfg = {"voice_levelup_channel_id": 10}

    assert _pick_voice_levelup_text_channel(g, cfg) is ch_cfg


def test_pick_voice_levelup_text_channel_falls_back_to_system_channel_and_names():
    g = GuildStub(1)
    sys_ch = TextChannelStub("system", channel_id=20)
    g.system_channel = sys_ch

    assert _pick_voice_levelup_text_channel(g, {"voice_levelup_channel_id": 0}) is sys_ch

    # if no system channel, find by preferred name
    g2 = GuildStub(2)
    g2.system_channel = None
    preferred = TextChannelStub("general", channel_id=30)
    g2.text_channels = [preferred]

    assert _pick_voice_levelup_text_channel(g2, {"voice_levelup_channel_id": 0}) is preferred


# ---------- Tests: XpVoice lifecycle ----------
def test_xpvoice_init_starts_loop():
    xp = XpServiceStub()
    bot = BotStub(xp)
    cog = XpVoice(bot)

    assert cog.voice_xp_loop.started is True  # provided by loop wrapper
    assert cog.xp is xp


def test_cog_unload_cancels_loop_no_throw():
    xp = XpServiceStub()
    bot = BotStub(xp)
    cog = XpVoice(bot)

    cog.cog_unload()
    assert cog.voice_xp_loop.cancelled is True


def test_cog_unload_ignores_cancel_errors(monkeypatch):
    xp = XpServiceStub()
    bot = BotStub(xp)
    cog = XpVoice(bot)

    def cancel_raises():
        raise RuntimeError("no")

    cog.voice_xp_loop.cancel = cancel_raises  # type: ignore[attr-defined]
    cog.cog_unload()  # doit ignorer


# ---------- Tests: voice_xp_loop behavior ----------
@pytest.mark.asyncio
async def test_voice_xp_loop_skips_when_disabled_or_voice_disabled(monkeypatch):
    xp = XpServiceStub()
    bot = BotStub(xp)
    g = GuildStub(1)
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
    xp = XpServiceStub()
    bot = BotStub(xp)
    g = GuildStub(1)
    bot.guilds = [g]
    cog = XpVoice(bot)

    m1 = MemberStub(1, g)
    vc = VoiceChannelStub([m1])
    g.voice_channels = [vc]

    monkeypatch.setattr(xv_mod, "now_ts", lambda: 123, raising=True)

    await cog.voice_xp_loop()

    assert ("voice_upsert_progress", 1, 1, 123) in xp.calls


@pytest.mark.asyncio
async def test_voice_xp_loop_skips_empty_voice_channels(monkeypatch):
    xp = XpServiceStub()
    bot = BotStub(xp)
    g = GuildStub(1)
    bot.guilds = [g]
    cog = XpVoice(bot)

    # members empty -> continue (ligne 92-93)
    g.voice_channels = [VoiceChannelStub([])]
    await cog.voice_xp_loop()


@pytest.mark.asyncio
async def test_voice_xp_loop_solo_upsert_errors_are_swallowed(monkeypatch):
    xp = XpServiceStub()
    xp._voice_upsert_raises = True
    bot = BotStub(xp)
    g = GuildStub(1)
    bot.guilds = [g]
    cog = XpVoice(bot)

    m1 = MemberStub(1, g)
    g.voice_channels = [VoiceChannelStub([m1])]

    monkeypatch.setattr(xv_mod, "now_ts", lambda: 123, raising=True)
    await cog.voice_xp_loop()  # ne doit pas lever


@pytest.mark.asyncio
async def test_voice_xp_loop_tick_returns_none_noop(monkeypatch):
    xp = XpServiceStub()
    xp._tick_return = None
    bot = BotStub(xp)
    g = GuildStub(1)
    bot.guilds = [g]
    cog = XpVoice(bot)

    m1 = MemberStub(1, g)
    m2 = MemberStub(2, g)
    g.voice_channels = [VoiceChannelStub([m1, m2])]

    await cog.voice_xp_loop()  # ne doit pas lever


@pytest.mark.asyncio
async def test_voice_xp_loop_no_level_up_no_send(monkeypatch):
    xp = XpServiceStub()
    xp._tick_return = (10, 2, 2)  # new_lvl <= old_lvl
    bot = BotStub(xp)
    g = GuildStub(1)
    bot.guilds = [g]
    cog = XpVoice(bot)

    m1 = MemberStub(1, g)
    m2 = MemberStub(2, g)
    g.voice_channels = [VoiceChannelStub([m1, m2])]

    txt = TextChannelStub("general", channel_id=50, can_send=True)
    g.text_channels = [txt]
    g.me = MemberStub(999, g)

    await cog.voice_xp_loop()
    assert txt.sent == []


@pytest.mark.asyncio
async def test_voice_xp_loop_send_errors_are_swallowed(monkeypatch):
    xp = XpServiceStub()
    xp._tick_return = (10, 2, 1)  # would level up
    bot = BotStub(xp)
    g = GuildStub(1)
    bot.guilds = [g]
    cog = XpVoice(bot)

    m1 = MemberStub(1, g)
    m2 = MemberStub(2, g)
    g.voice_channels = [VoiceChannelStub([m1, m2])]

    async def _boom_send(self, *_a, **_k):
        raise RuntimeError("boom")

    BoomChannel = type("BoomChannel", (TextChannelStub,), {"send": _boom_send})

    txt = BoomChannel("general", channel_id=50, can_send=True)
    g.text_channels = [txt]
    g.me = MemberStub(999, g)

    monkeypatch.setattr(xv_mod, "level_mention", lambda *_a, **_k: "@lvl2", raising=True)

    await cog.voice_xp_loop()  # ne doit pas lever


@pytest.mark.asyncio
async def test_wait_until_ready_calls_bot(monkeypatch):
    xp = XpServiceStub()

    def _bot2_init(self, xp):
        BotStub.__init__(self, xp)
        self.ready_called = 0

    async def _bot2_wait(self):
        self.ready_called += 1

    Bot = type("Bot", (BotStub,), {"__init__": _bot2_init, "wait_until_ready": _bot2_wait})

    bot = Bot(xp)
    cog = XpVoice(bot)
    await cog._wait_until_ready()
    assert bot.ready_called == 1


@pytest.mark.asyncio
async def test_voice_xp_loop_levelup_sends_message_when_permitted(monkeypatch):
    discord = sys.modules["discord"]
    xp = XpServiceStub()
    bot = BotStub(xp)
    g = GuildStub(1)
    bot.guilds = [g]
    cog = XpVoice(bot)

    # 2 active members -> tick called for each active
    m1 = MemberStub(1, g)
    m2 = MemberStub(2, g)
    vc = VoiceChannelStub([m1, m2])
    g.voice_channels = [vc]

    # configure pick channel
    txt = TextChannelStub("general", channel_id=50, can_send=True)
    g.text_channels = [txt]

    # guild.me exists
    me = MemberStub(999, g)
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
    xp = XpServiceStub()
    bot = BotStub(xp)
    g = GuildStub(1)
    bot.guilds = [g]
    cog = XpVoice(bot)

    m1 = MemberStub(1, g)
    m2 = MemberStub(2, g)
    vc = VoiceChannelStub([m1, m2])
    g.voice_channels = [vc]

    xp._tick_return = (10, 2, 1)  # would level up

    # No channel found
    g.text_channels = []
    await cog.voice_xp_loop()

    # With channel but no perms
    txt = TextChannelStub("general", channel_id=50, can_send=False)
    g.text_channels = [txt]
    g.me = MemberStub(999, g)

    await cog.voice_xp_loop()
    assert txt.sent == []


@pytest.mark.asyncio
async def test_voice_xp_loop_handles_exceptions_and_continues(monkeypatch):
    xp = XpServiceStub()
    bot = BotStub(xp)

    g1 = GuildStub(1)
    g2 = GuildStub(2)
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
    xp = XpServiceStub()
    bot = BotStub(xp)
    cog = XpVoice(bot)

    g = GuildStub(1)
    bot_member = MemberStub(10, g, bot=True)
    await cog.on_voice_state_update(bot_member, VoiceStateStub(), VoiceStateStub())
    assert xp.calls == []

    no_guild_member = MemberStub(11, None)  # type: ignore[arg-type]
    no_guild_member.guild = None
    await cog.on_voice_state_update(no_guild_member, VoiceStateStub(), VoiceStateStub())
    assert xp.calls == []


@pytest.mark.asyncio
async def test_voice_state_update_no_relevant_change_noop(monkeypatch):
    xp = XpServiceStub()
    bot = BotStub(xp)
    cog = XpVoice(bot)
    g = GuildStub(1)
    m = MemberStub(1, g)

    before = VoiceStateStub(channel=None, mute=False, deaf=False, self_mute=False, self_deaf=False)
    after = VoiceStateStub(channel=None, mute=False, deaf=False, self_mute=False, self_deaf=False)

    await cog.on_voice_state_update(m, before, after)
    assert xp.calls == []


@pytest.mark.asyncio
async def test_voice_state_update_relevant_change_upserts_last_tick(monkeypatch):
    xp = XpServiceStub()
    bot = BotStub(xp)
    cog = XpVoice(bot)
    g = GuildStub(1)
    m = MemberStub(1, g)

    monkeypatch.setattr(xv_mod, "now_ts", lambda: 999, raising=True)

    before = VoiceStateStub(channel="A", mute=False)
    after = VoiceStateStub(channel="B", mute=False)

    await cog.on_voice_state_update(m, before, after)

    assert ("ensure_defaults", 1) in xp.calls
    assert ("voice_upsert_progress", 1, 1, 999) in xp.calls


@pytest.mark.asyncio
async def test_voice_state_update_swallow_errors(monkeypatch):
    xp = XpServiceStub()
    xp._voice_upsert_raises = True
    bot = BotStub(xp)
    cog = XpVoice(bot)
    g = GuildStub(1)
    m = MemberStub(1, g)

    monkeypatch.setattr(xv_mod, "now_ts", lambda: 999, raising=True)

    before = VoiceStateStub(channel="A", mute=False)
    after = VoiceStateStub(channel="B", mute=True)

    # Should not raise
    await cog.on_voice_state_update(m, before, after)


# ---------- Tests: setup ----------
def test_setup_adds_cog():
    xp = XpServiceStub()
    bot = BotStub(xp)

    added = {}

    def add_cog(cog):
        added["cog"] = cog

    bot.add_cog = add_cog  # type: ignore[attr-defined]

    setup(bot)
    assert isinstance(added["cog"], XpVoice)
