from __future__ import annotations

import pytest

from eldoria.features.xp._internal import voice_xp as mod

# ----------------------------
# Fakes Discord
# ----------------------------

class FakeVoiceState:
    def __init__(
        self,
        *,
        channel: object | None = object(),
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


class FakeMember:
    def __init__(self, member_id: int = 42, *, bot: bool = False, voice: FakeVoiceState | None = None):
        self.id = member_id
        self.bot = bot
        self.voice = voice


class FakeGuild:
    def __init__(self, guild_id: int = 123):
        self.id = guild_id


# ----------------------------
# Fake config (remplace XpConfig(**raw))
# ----------------------------

class _Cfg:
    def __init__(
        self,
        *,
        enabled: bool = True,
        bonus_percent: int = 0,
        voice_enabled: bool = True,
        voice_xp_per_interval: int = 1,
        voice_interval_seconds: int = 180,
        voice_daily_cap_xp: int = 100,
        **_extra,
    ):
        self.enabled = enabled
        self.bonus_percent = bonus_percent
        self.voice_enabled = voice_enabled
        self.voice_xp_per_interval = voice_xp_per_interval
        self.voice_interval_seconds = voice_interval_seconds
        self.voice_daily_cap_xp = voice_daily_cap_xp


# ----------------------------
# Helpers patch repo
# ----------------------------

def _install_repo_mocks(monkeypatch, *, config_raw: dict, progress: dict, levels=None, old_xp=0, new_xp=0):
    """
    Installe des mocks sur mod.xp_repo avec un état contrôlé.
    - progress: dict retourné par xp_voice_get_progress
    - upsert_calls: capture toutes les upsert
    - add_calls: capture l'xp ajouté
    """
    levels = levels if levels is not None else [(1, 0), (2, 100), (3, 250)]

    upsert_calls: list[dict] = []
    add_calls: list[int] = []

    def xp_get_config(_gid: int):
        return config_raw

    def xp_voice_get_progress(_gid: int, _mid: int):
        # retourne une copie pour simuler DB et éviter des mutations surprises
        return dict(progress)

    def xp_voice_upsert_progress(_gid: int, _mid: int, **kwargs):
        upsert_calls.append(dict(kwargs))
        # on “persist” dans progress pour les tests qui en ont besoin
        progress.update(kwargs)

    def xp_get_member(_gid: int, _mid: int):
        return (old_xp, 0)

    def xp_add_xp(_gid: int, _mid: int, gained: int, **_kwargs):
        add_calls.append(int(gained))
        return new_xp if new_xp else (old_xp + int(gained))

    def xp_get_levels(_gid: int):
        return levels

    monkeypatch.setattr(mod.xp_repo, "xp_get_config", xp_get_config, raising=True)
    monkeypatch.setattr(mod.xp_repo, "xp_voice_get_progress", xp_voice_get_progress, raising=True)
    monkeypatch.setattr(mod.xp_repo, "xp_voice_upsert_progress", xp_voice_upsert_progress, raising=True)
    monkeypatch.setattr(mod.xp_repo, "xp_get_member", xp_get_member, raising=True)
    monkeypatch.setattr(mod.xp_repo, "xp_add_xp", xp_add_xp, raising=True)
    monkeypatch.setattr(mod.xp_repo, "xp_get_levels", xp_get_levels, raising=True)

    return upsert_calls, add_calls


# ----------------------------
# Tests: is_voice_member_active / eligible
# ----------------------------

def test_is_voice_member_active_false_if_bot():
    m = FakeMember(bot=True, voice=FakeVoiceState())
    assert mod.is_voice_member_active(m) is False


def test_is_voice_member_active_false_if_no_voice_or_no_channel():
    assert mod.is_voice_member_active(FakeMember(bot=False, voice=None)) is False
    assert mod.is_voice_member_active(FakeMember(bot=False, voice=FakeVoiceState(channel=None))) is False


@pytest.mark.parametrize(
    "kwargs",
    [
        {"mute": True},
        {"self_mute": True},
        {"deaf": True},
        {"self_deaf": True},
    ],
)
def test_is_voice_member_active_false_if_muted_or_deaf(kwargs):
    m = FakeMember(bot=False, voice=FakeVoiceState(**kwargs))
    assert mod.is_voice_member_active(m) is False


def test_is_voice_member_active_true_when_ok():
    m = FakeMember(bot=False, voice=FakeVoiceState())
    assert mod.is_voice_member_active(m) is True


def test_is_voice_eligible_in_channel_requires_active_and_at_least_2():
    m_ok = FakeMember(bot=False, voice=FakeVoiceState())
    m_bad = FakeMember(bot=False, voice=None)

    assert mod.is_voice_eligible_in_channel(m_ok, active_count=1) is False
    assert mod.is_voice_eligible_in_channel(m_ok, active_count=2) is True
    assert mod.is_voice_eligible_in_channel(m_bad, active_count=99) is False


# ----------------------------
# Tests: tick_voice_xp_for_member (branches)
# ----------------------------

@pytest.mark.asyncio
async def test_tick_returns_none_for_bot(monkeypatch):
    monkeypatch.setattr(mod, "XpConfig", _Cfg)
    g = FakeGuild()
    m = FakeMember(bot=True, voice=FakeVoiceState())

    # si bot => ne doit pas toucher repo
    monkeypatch.setattr(mod.xp_repo, "xp_get_config", lambda *_: (_ for _ in ()).throw(AssertionError("repo called")))
    assert await mod.tick_voice_xp_for_member(g, m) is None


@pytest.mark.asyncio
async def test_tick_returns_none_when_xp_disabled_or_voice_disabled(monkeypatch):
    monkeypatch.setattr(mod, "XpConfig", _Cfg)
    g = FakeGuild()
    m = FakeMember(bot=False, voice=FakeVoiceState())

    for raw in ({"enabled": False, "voice_enabled": True}, {"enabled": True, "voice_enabled": False}):
        progress = {"day_key": "X", "last_tick_ts": 1, "buffer_seconds": 0, "bonus_cents": 0, "xp_today": 0}
        upserts, adds = _install_repo_mocks(monkeypatch, config_raw=raw, progress=progress)
        monkeypatch.setattr(mod, "now_ts", lambda: 1000, raising=True)
        monkeypatch.setattr(mod, "day_key_utc", lambda _ts: "X", raising=True)

        assert await mod.tick_voice_xp_for_member(g, m) is None
        assert upserts == []
        assert adds == []


@pytest.mark.asyncio
async def test_tick_resets_day_progress_when_day_changed_and_upserts_reset(monkeypatch):
    monkeypatch.setattr(mod, "XpConfig", _Cfg)
    g = FakeGuild(123)
    m = FakeMember(42, bot=False, voice=FakeVoiceState())

    progress = {"day_key": "OLD", "last_tick_ts": 999, "buffer_seconds": 12, "bonus_cents": 77, "xp_today": 9}
    upserts, adds = _install_repo_mocks(monkeypatch, config_raw={"enabled": True, "voice_enabled": True}, progress=progress)

    monkeypatch.setattr(mod, "now_ts", lambda: 1000, raising=True)
    monkeypatch.setattr(mod, "day_key_utc", lambda _ts: "NEW", raising=True)

    # last_tick <=0 après reset => tick doit upsert last_tick_ts=now puis return None
    assert await mod.tick_voice_xp_for_member(g, m) is None

    assert upserts[0] == {
        "day_key": "NEW",
        "last_tick_ts": 0,
        "buffer_seconds": 0,
        "bonus_cents": 0,
        "xp_today": 0,
    }
    assert upserts[1] == {"day_key": "NEW", "last_tick_ts": 1000}
    assert adds == []


@pytest.mark.asyncio
async def test_tick_when_last_tick_missing_sets_last_tick_and_returns_none(monkeypatch):
    monkeypatch.setattr(mod, "XpConfig", _Cfg)
    g = FakeGuild()
    m = FakeMember(42, bot=False, voice=FakeVoiceState())

    progress = {"day_key": "D", "last_tick_ts": 0, "buffer_seconds": 0, "bonus_cents": 0, "xp_today": 0}
    upserts, adds = _install_repo_mocks(monkeypatch, config_raw={"enabled": True, "voice_enabled": True}, progress=progress)

    monkeypatch.setattr(mod, "now_ts", lambda: 2000, raising=True)
    monkeypatch.setattr(mod, "day_key_utc", lambda _ts: "D", raising=True)

    assert await mod.tick_voice_xp_for_member(g, m) is None
    assert upserts == [{"day_key": "D", "last_tick_ts": 2000}]
    assert adds == []


@pytest.mark.asyncio
async def test_tick_inactive_member_updates_last_tick_and_returns_none(monkeypatch):
    monkeypatch.setattr(mod, "XpConfig", _Cfg)
    g = FakeGuild()
    # inactive (mute)
    m = FakeMember(42, bot=False, voice=FakeVoiceState(mute=True))

    progress = {"day_key": "D", "last_tick_ts": 1000, "buffer_seconds": 0, "bonus_cents": 0, "xp_today": 0}
    upserts, adds = _install_repo_mocks(monkeypatch, config_raw={"enabled": True, "voice_enabled": True}, progress=progress)

    monkeypatch.setattr(mod, "now_ts", lambda: 1100, raising=True)
    monkeypatch.setattr(mod, "day_key_utc", lambda _ts: "D", raising=True)

    assert await mod.tick_voice_xp_for_member(g, m) is None
    assert upserts == [{"day_key": "D", "last_tick_ts": 1100}]
    assert adds == []


@pytest.mark.asyncio
async def test_tick_delta_is_bounded_to_600(monkeypatch):
    """
    last_tick très ancien => delta borné à 600
    """
    monkeypatch.setattr(mod, "XpConfig", _Cfg)
    g = FakeGuild()
    m = FakeMember(42, bot=False, voice=FakeVoiceState())

    # last_tick=0? non, ici valide
    progress = {"day_key": "D", "last_tick_ts": 0, "buffer_seconds": 0, "bonus_cents": 0, "xp_today": 0}
    # on veut passer la branche last_tick>0, donc last_tick_ts=1
    progress["last_tick_ts"] = 1

    upserts, adds = _install_repo_mocks(monkeypatch, config_raw={"enabled": True, "voice_enabled": True,
                                                                 "voice_interval_seconds": 60,
                                                                 "voice_xp_per_interval": 1,
                                                                 "voice_daily_cap_xp": 999}, progress=progress)

    monkeypatch.setattr(mod, "now_ts", lambda: 10_000, raising=True)  # delta énorme -> doit devenir 600
    monkeypatch.setattr(mod, "day_key_utc", lambda _ts: "D", raising=True)
    monkeypatch.setattr(mod, "has_active_server_tag_for_guild", lambda *_: False, raising=True)
    monkeypatch.setattr(mod, "compute_level", lambda xp, lvls: 1, raising=True)

    sync_calls = []
    async def _sync(_g, _m, *, xp=None):
        sync_calls.append(xp)
    monkeypatch.setattr(mod, "sync_member_level_roles", _sync, raising=True)

    # delta 600, interval 60 => 10 intervals => base_gain 10
    res = await mod.tick_voice_xp_for_member(g, m)
    assert res is not None
    assert adds == [10]
    # buffer_seconds final = 0 (600 - 10*60)
    assert upserts[-1]["buffer_seconds"] == 0
    assert sync_calls


@pytest.mark.asyncio
async def test_tick_returns_none_when_config_numbers_invalid(monkeypatch):
    monkeypatch.setattr(mod, "XpConfig", _Cfg)
    g = FakeGuild()
    m = FakeMember(42, bot=False, voice=FakeVoiceState())

    # voice_daily_cap_xp <=0 OR interval <=0 OR xp_per_interval <=0 => upsert(last_tick_ts=now) then None
    bad_cfgs = [
        {"enabled": True, "voice_enabled": True, "voice_daily_cap_xp": 0},
        {"enabled": True, "voice_enabled": True, "voice_interval_seconds": 0},
        {"enabled": True, "voice_enabled": True, "voice_xp_per_interval": 0},
    ]

    for raw in bad_cfgs:
        progress = {"day_key": "D", "last_tick_ts": 1000, "buffer_seconds": 0, "bonus_cents": 0, "xp_today": 0}
        upserts, adds = _install_repo_mocks(monkeypatch, config_raw=raw, progress=progress)
        monkeypatch.setattr(mod, "now_ts", lambda: 1100, raising=True)
        monkeypatch.setattr(mod, "day_key_utc", lambda _ts: "D", raising=True)

        assert await mod.tick_voice_xp_for_member(g, m) is None
        assert upserts == [{"day_key": "D", "last_tick_ts": 1100}]
        assert adds == []


@pytest.mark.asyncio
async def test_tick_daily_cap_reached_resets_buffer_and_returns_none(monkeypatch):
    monkeypatch.setattr(mod, "XpConfig", _Cfg)
    g = FakeGuild()
    m = FakeMember(42, bot=False, voice=FakeVoiceState())

    raw = {"enabled": True, "voice_enabled": True, "voice_daily_cap_xp": 5, "voice_interval_seconds": 60, "voice_xp_per_interval": 1}
    progress = {"day_key": "D", "last_tick_ts": 1000, "buffer_seconds": 999, "bonus_cents": 0, "xp_today": 5}  # cap atteint
    upserts, adds = _install_repo_mocks(monkeypatch, config_raw=raw, progress=progress)

    monkeypatch.setattr(mod, "now_ts", lambda: 1100, raising=True)
    monkeypatch.setattr(mod, "day_key_utc", lambda _ts: "D", raising=True)

    assert await mod.tick_voice_xp_for_member(g, m) is None
    # buffer_seconds doit être remis à 0 dans cette branche
    assert upserts == [{"day_key": "D", "last_tick_ts": 1100, "buffer_seconds": 0}]
    assert adds == []


@pytest.mark.asyncio
async def test_tick_not_enough_buffer_keeps_buffer_and_returns_none(monkeypatch):
    """
    buffer_seconds < interval => intervals=0 => base_gain<=0 => upsert(buffer_seconds) puis None
    """
    monkeypatch.setattr(mod, "XpConfig", _Cfg)
    g = FakeGuild()
    m = FakeMember(42, bot=False, voice=FakeVoiceState())

    raw = {"enabled": True, "voice_enabled": True, "voice_interval_seconds": 60, "voice_xp_per_interval": 2, "voice_daily_cap_xp": 999}
    progress = {"day_key": "D", "last_tick_ts": 1000, "buffer_seconds": 10, "bonus_cents": 0, "xp_today": 0}
    upserts, adds = _install_repo_mocks(monkeypatch, config_raw=raw, progress=progress)

    monkeypatch.setattr(mod, "now_ts", lambda: 1030, raising=True)  # delta=30 => buffer=40 => intervals=0
    monkeypatch.setattr(mod, "day_key_utc", lambda _ts: "D", raising=True)

    assert await mod.tick_voice_xp_for_member(g, m) is None
    assert upserts == [{"day_key": "D", "last_tick_ts": 1030, "buffer_seconds": 40}]
    assert adds == []


@pytest.mark.asyncio
async def test_tick_bonus_cents_accumulates_and_grants_extra_xp(monkeypatch):
    """
    base_gain=1, bonus_percent=50 => bonus_cents += 50 => pas d'extra (0)
    tick suivant base_gain=1 => bonus_cents 100 => extra=1, remainder=0 => total_gain 2
    """
    monkeypatch.setattr(mod, "XpConfig", _Cfg)
    g = FakeGuild()
    m = FakeMember(42, bot=False, voice=FakeVoiceState())

    raw = {
        "enabled": True,
        "voice_enabled": True,
        "voice_interval_seconds": 10,
        "voice_xp_per_interval": 1,
        "voice_daily_cap_xp": 999,
        "bonus_percent": 50,
    }

    progress = {"day_key": "D", "last_tick_ts": 1000, "buffer_seconds": 0, "bonus_cents": 0, "xp_today": 0}
    upserts, adds = _install_repo_mocks(monkeypatch, config_raw=raw, progress=progress)

    monkeypatch.setattr(mod, "now_ts", lambda: 1010, raising=True)  # delta=10 => 1 interval
    monkeypatch.setattr(mod, "day_key_utc", lambda _ts: "D", raising=True)
    monkeypatch.setattr(mod, "has_active_server_tag_for_guild", lambda *_: True, raising=True)
    monkeypatch.setattr(mod, "compute_level", lambda xp, lvls: 1, raising=True)

    async def _sync(*_a, **_k):
        return None
    monkeypatch.setattr(mod, "sync_member_level_roles", _sync, raising=True)

    # tick1 : base_gain=1, bonus_cents=50, total_gain=1
    res1 = await mod.tick_voice_xp_for_member(g, m)
    assert res1 is not None
    assert adds[-1] == 1
    assert progress["bonus_cents"] == 50

    # Prépare tick2 : last_tick -> 1010 déjà upsert, on avance le temps de 10s
    monkeypatch.setattr(mod, "now_ts", lambda: 1020, raising=True)

    res2 = await mod.tick_voice_xp_for_member(g, m)
    assert res2 is not None
    # tick2 : base_gain=1, bonus_cents 50+50=100 => extra=1 => total_gain=2
    assert adds[-1] == 2
    assert progress["bonus_cents"] == 0


@pytest.mark.asyncio
async def test_tick_caps_total_gain_to_cap_left_and_may_return_none_if_zero(monkeypatch):
    """
    Si cap_left=0 => total_gain devient 0 => upsert puis return None (sans xp_add_xp).
    """
    monkeypatch.setattr(mod, "XpConfig", _Cfg)
    g = FakeGuild()
    m = FakeMember(42, bot=False, voice=FakeVoiceState())

    raw = {"enabled": True, "voice_enabled": True, "voice_interval_seconds": 10, "voice_xp_per_interval": 10, "voice_daily_cap_xp": 5}
    progress = {"day_key": "D", "last_tick_ts": 1000, "buffer_seconds": 0, "bonus_cents": 0, "xp_today": 5}  # cap déjà atteint
    upserts, adds = _install_repo_mocks(monkeypatch, config_raw=raw, progress=progress)

    monkeypatch.setattr(mod, "now_ts", lambda: 1010, raising=True)
    monkeypatch.setattr(mod, "day_key_utc", lambda _ts: "D", raising=True)

    # cap atteint => branche dédiée (buffer reset) déjà testée, ici on force xp_today=4
    progress["xp_today"] = 5  # on garde cap reached, ça part dans branche cap reached
    assert await mod.tick_voice_xp_for_member(g, m) is None
    assert adds == []

    # maintenant cap_left=0 via trim en fin de calcul (xp_today==cap, mais on ne passe pas la branche cap reached)
    # on met xp_today=5? non. Pour éviter branche cap reached, on met xp_today=5 mais cap=5 -> ça trigger.
    # donc on met xp_today=5 et cap=4 par ex
    raw2 = {"enabled": True, "voice_enabled": True, "voice_interval_seconds": 10, "voice_xp_per_interval": 10, "voice_daily_cap_xp": 5}
    progress2 = {"day_key": "D", "last_tick_ts": 1000, "buffer_seconds": 10, "bonus_cents": 0, "xp_today": 5}
    upserts2, adds2 = _install_repo_mocks(monkeypatch, config_raw=raw2, progress=progress2)
    monkeypatch.setattr(mod, "now_ts", lambda: 1010, raising=True)
    monkeypatch.setattr(mod, "day_key_utc", lambda _ts: "D", raising=True)

    # xp_today >= cap => branche cap reached => retourne None sans add
    assert await mod.tick_voice_xp_for_member(g, m) is None
    assert adds2 == []
