import pytest

from eldoria.features import xp_system

from tests.conftest import (
    FakeGuild,
    FakeMember,
    FakeMessage,
    FakePrimaryGuild,
    FakeVoiceState,
)


# =========================
# Fixtures (DB mock)
# =========================

@pytest.fixture()
def fake_db(monkeypatch):
    """Mock complet de gestionDB pour tester les calculs XP (messages)."""

    members = {}  # (guild_id, member_id) -> {xp:int, last_ts:int}

    config = {
        "enabled": 1,
        "points_per_message": 10,
        "cooldown_seconds": 60,
        "bonus_percent": 20,
        "karuta_k_small_percent": 30,
        # voice (pas utilise ici)
        "voice_enabled": 1,
        "voice_xp_per_interval": 1,
        "voice_interval_seconds": 180,
        "voice_daily_cap_xp": 100,
        "voice_levelup_channel_id": 0,
    }

    levels = [(1, 0), (2, 100), (3, 200), (4, 500), (5, 1000)]

    def xp_get_config(guild_id):
        return dict(config)

    def xp_get_member(guild_id, member_id):
        row = members.get((guild_id, member_id), {"xp": 0, "last_ts": 0})
        return int(row["xp"]), int(row["last_ts"])

    def xp_add_xp(guild_id, member_id, gained, set_last_xp_ts=None):
        row = members.setdefault((guild_id, member_id), {"xp": 0, "last_ts": 0})
        row["xp"] = int(row["xp"]) + int(gained)
        if set_last_xp_ts is not None:
            row["last_ts"] = int(set_last_xp_ts)
        return int(row["xp"])

    def xp_get_levels(guild_id):
        return list(levels)

    monkeypatch.setattr(xp_system.gestionDB, "xp_get_config", xp_get_config)
    monkeypatch.setattr(xp_system.gestionDB, "xp_get_member", xp_get_member)
    monkeypatch.setattr(xp_system.gestionDB, "xp_add_xp", xp_add_xp)
    monkeypatch.setattr(xp_system.gestionDB, "xp_get_levels", xp_get_levels)

    async def _noop_sync_member_level_roles(guild, member, *, xp=None):
        return None

    monkeypatch.setattr(xp_system, "sync_member_level_roles", _noop_sync_member_level_roles)

    now_box = {"now": 1_700_000_000}

    def _fake_now_ts():
        return int(now_box["now"])

    monkeypatch.setattr(xp_system, "_now_ts", _fake_now_ts)

    return {
        "members": members,
        "config": config,
        "levels": levels,
        "now_box": now_box,
    }


@pytest.fixture()
def fake_voice_db(monkeypatch):
    """Mock gestionDB pour les tests vocal (progress journalier + XP)."""

    members = {}  # (guild_id, member_id) -> {xp:int, last_ts:int}
    voice_prog = {}  # (guild_id, member_id) -> dict

    config = {
        "enabled": 1,
        "points_per_message": 10,
        "cooldown_seconds": 60,
        "bonus_percent": 20,
        "karuta_k_small_percent": 30,
        "voice_enabled": 1,
        "voice_xp_per_interval": 5,
        "voice_interval_seconds": 60,
        "voice_daily_cap_xp": 50,
        "voice_levelup_channel_id": 0,
    }

    levels = [(1, 0), (2, 100), (3, 200), (4, 500), (5, 1000)]

    def xp_get_config(guild_id):
        return dict(config)

    def xp_get_member(guild_id, member_id):
        row = members.get((guild_id, member_id), {"xp": 0, "last_ts": 0})
        return int(row["xp"]), int(row["last_ts"])

    def xp_add_xp(guild_id, member_id, gained, set_last_xp_ts=None):
        row = members.setdefault((guild_id, member_id), {"xp": 0, "last_ts": 0})
        row["xp"] = int(row["xp"]) + int(gained)
        if set_last_xp_ts is not None:
            row["last_ts"] = int(set_last_xp_ts)
        return int(row["xp"])

    def xp_get_levels(guild_id):
        return list(levels)

    def xp_voice_get_progress(guild_id, member_id):
        return dict(voice_prog.get((guild_id, member_id), {}))

    def xp_voice_upsert_progress(guild_id, member_id, **kwargs):
        cur = voice_prog.setdefault((guild_id, member_id), {})
        cur.update(kwargs)

    monkeypatch.setattr(xp_system.gestionDB, "xp_get_config", xp_get_config)
    monkeypatch.setattr(xp_system.gestionDB, "xp_get_member", xp_get_member)
    monkeypatch.setattr(xp_system.gestionDB, "xp_add_xp", xp_add_xp)
    monkeypatch.setattr(xp_system.gestionDB, "xp_get_levels", xp_get_levels)
    monkeypatch.setattr(xp_system.gestionDB, "xp_voice_get_progress", xp_voice_get_progress)
    monkeypatch.setattr(xp_system.gestionDB, "xp_voice_upsert_progress", xp_voice_upsert_progress)

    async def _noop_sync_member_level_roles(guild, member, *, xp=None):
        return None

    monkeypatch.setattr(xp_system, "sync_member_level_roles", _noop_sync_member_level_roles)

    now_box = {"now": 1_700_000_000}

    def _fake_now_ts():
        return int(now_box["now"])

    monkeypatch.setattr(xp_system, "_now_ts", _fake_now_ts)

    # On stabilise la clef jour, pour ne pas dependre de la timezone
    monkeypatch.setattr(xp_system, "_day_key_utc", lambda ts=None: "20260118")

    return {"members": members, "voice_prog": voice_prog, "config": config, "now_box": now_box}


# =========================
# Helpers
# =========================

def _member_with_tag(guild: FakeGuild) -> FakeMember:
    # Simule l'affichage du Server Tag de CETTE guilde
    pg = FakePrimaryGuild(identity_enabled=True, identity_guild_id=guild.id, tag=guild.tag)
    return FakeMember(primary_guild=pg)


def _active_voice_member(*, with_tag: bool, guild: FakeGuild) -> FakeMember:
    pg = None
    if with_tag:
        pg = FakePrimaryGuild(identity_enabled=True, identity_guild_id=guild.id, tag=guild.tag)

    # channel n'a besoin que d'etre non-None
    vs = FakeVoiceState(channel=object(), mute=False, self_mute=False, deaf=False, self_deaf=False)
    return FakeMember(primary_guild=pg, voice=vs)


# =========================
# Tests - Messages
# =========================

@pytest.mark.asyncio
async def test_message_no_cooldown_no_tag(fake_db):
    guild = FakeGuild()
    member = FakeMember()
    msg = FakeMessage(guild=guild, author=member, content="hello world")

    res = await xp_system.handle_message_xp(msg)
    assert res is not None
    new_xp, new_lvl, old_lvl = res

    assert new_xp == 10
    assert old_lvl == 1
    assert new_lvl == 1


@pytest.mark.asyncio
async def test_message_with_cooldown_blocks_gain(fake_db):
    guild = FakeGuild()
    member = FakeMember()

    msg1 = FakeMessage(guild=guild, author=member, content="hello")
    assert await xp_system.handle_message_xp(msg1) is not None

    fake_db["now_box"]["now"] += 10  # cooldown = 60
    msg2 = FakeMessage(guild=guild, author=member, content="hello again")
    assert await xp_system.handle_message_xp(msg2) is None


@pytest.mark.asyncio
async def test_message_in_dm_returns_none(fake_db):
    member = FakeMember()
    msg = type("Msg", (), {"guild": None, "author": member, "content": "hello"})()
    assert await xp_system.handle_message_xp(msg) is None


@pytest.mark.asyncio
async def test_message_from_bot_returns_none(fake_db):
    guild = FakeGuild()
    bot_member = FakeMember(bot=True)
    msg = FakeMessage(guild=guild, author=bot_member, content="hello")
    assert await xp_system.handle_message_xp(msg) is None


@pytest.mark.asyncio
async def test_message_xp_disabled_returns_none(fake_db):
    fake_db["config"]["enabled"] = 0
    guild = FakeGuild()
    member = FakeMember()
    msg = FakeMessage(guild=guild, author=member, content="hello")
    assert await xp_system.handle_message_xp(msg) is None


@pytest.mark.asyncio
async def test_message_points_per_message_zero_returns_none(fake_db):
    fake_db["config"]["points_per_message"] = 0
    guild = FakeGuild()
    member = FakeMember()
    msg = FakeMessage(guild=guild, author=member, content="hello")
    assert await xp_system.handle_message_xp(msg) is None


@pytest.mark.asyncio
async def test_message_points_per_message_negative_returns_none(fake_db):
    fake_db["config"]["points_per_message"] = -10
    guild = FakeGuild()
    member = FakeMember()
    msg = FakeMessage(guild=guild, author=member, content="hello")
    assert await xp_system.handle_message_xp(msg) is None


@pytest.mark.asyncio
async def test_message_bonus_percent_zero_disables_bonus_even_with_tag(fake_db):
    fake_db["config"]["bonus_percent"] = 0
    guild = FakeGuild(tag="ELD")
    member = _member_with_tag(guild)
    msg = FakeMessage(guild=guild, author=member, content="hello")
    res = await xp_system.handle_message_xp(msg)
    assert res is not None
    new_xp, *_ = res
    assert new_xp == 10


@pytest.mark.asyncio
async def test_message_whitespace_only_not_treated_as_karuta(fake_db):
    guild = FakeGuild()
    member = FakeMember()
    msg = FakeMessage(guild=guild, author=member, content="   ")
    res = await xp_system.handle_message_xp(msg)
    assert res is not None
    new_xp, *_ = res
    assert new_xp == 10


@pytest.mark.asyncio
async def test_message_karuta_small_percent_zero_results_in_no_xp_gain_but_updates_timestamp(fake_db):
    """Comportement actuel: si le % Karuta force gained=0, on enregistre quand meme le ts."""
    fake_db["config"]["karuta_k_small_percent"] = 0
    guild = FakeGuild()
    member = FakeMember()

    # premier message (karuta) -> gained 0
    msg1 = FakeMessage(guild=guild, author=member, content="k")
    res1 = await xp_system.handle_message_xp(msg1)
    assert res1 is not None
    new_xp, new_lvl, old_lvl = res1
    assert new_xp == 0
    assert new_lvl == old_lvl == 1

    # cooldown doit bloquer grace au timestamp mis a jour
    fake_db["now_box"]["now"] += 1
    msg2 = FakeMessage(guild=guild, author=member, content="hello")
    assert await xp_system.handle_message_xp(msg2) is None


# =========================
# Karuta — détection pure
# =========================

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content",
    [
        "k",
        "kd",
        "kcd",
        "K",
        "KCD",
        "k 123",
        "K 123",
        "kabcdefghi",  # len = 9
        "karuta",
        "Karuta",      # majuscule + len < 10
    ],
)
async def test_karuta_messages_apply_small_percent(fake_db, content):
    """Tout message commençant par 'k' et <= 10 chars est Karuta."""
    guild = FakeGuild()
    member = FakeMember()

    msg = FakeMessage(guild=guild, author=member, content=content)
    res = await xp_system.handle_message_xp(msg)

    assert res is not None
    gained_xp, *_ = res

    # base 10 * 30% = 3
    assert gained_xp == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content",
    [
        "kabcdefghiX",   # len = 10
        "Kabcdefghij",   # len = 10
        "karut aaaaaaaaa",   # len > 10
        "Karut aaaaaaaaa",   # len > 10
    ],
)
async def test_non_karuta_length_10_or_more(fake_db, content):
    """Longueur >= 10 => PAS Karuta."""
    guild = FakeGuild()
    member = FakeMember()

    assert len(content) >= 10

    msg = FakeMessage(guild=guild, author=member, content=content)
    res = await xp_system.handle_message_xp(msg)

    assert res is not None
    gained_xp, *_ = res

    # message normal
    assert gained_xp == 10


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content",
    [
        "d",
        "hello",
        "xk",
        " ak",
    ],
)
async def test_non_karuta_not_starting_with_k(fake_db, content):
    """Ne commence pas par 'k' => PAS Karuta."""
    guild = FakeGuild()
    member = FakeMember()

    msg = FakeMessage(guild=guild, author=member, content=content)
    res = await xp_system.handle_message_xp(msg)

    assert res is not None
    gained_xp, *_ = res

    assert gained_xp == 10


# =========================
# Karuta + Tag
# =========================

@pytest.mark.asyncio
async def test_karuta_with_tag_applies_bonus_then_small_percent(fake_db):
    """Bonus tag puis réduction Karuta (ordre important)."""
    guild = FakeGuild(tag="ELD")
    member = _member_with_tag(guild)

    msg = FakeMessage(guild=guild, author=member, content="kcd")
    res = await xp_system.handle_message_xp(msg)

    assert res is not None
    gained_xp, *_ = res

    # base 10 +20% = 12
    # karuta 30% => round(12 * 0.3) = 4
    assert gained_xp == 4


# =========================
# Karuta + Cooldown
# =========================

@pytest.mark.asyncio
async def test_karuta_respects_cooldown(fake_db):
    """Le cooldown s'applique aussi aux messages Karuta."""
    guild = FakeGuild()
    member = FakeMember()

    msg1 = FakeMessage(guild=guild, author=member, content="kcd")
    assert await xp_system.handle_message_xp(msg1) is not None

    # cooldown = 60s
    fake_db["now_box"]["now"] += 1

    msg2 = FakeMessage(guild=guild, author=member, content="kcd")
    assert await xp_system.handle_message_xp(msg2) is None


@pytest.mark.asyncio
async def test_karuta_with_tag_and_cooldown(fake_db):
    """Karuta + tag n'ignore PAS le cooldown."""
    guild = FakeGuild(tag="ELD")
    member = _member_with_tag(guild)

    msg1 = FakeMessage(guild=guild, author=member, content="kcd")
    assert await xp_system.handle_message_xp(msg1) is not None

    fake_db["now_box"]["now"] += 5

    msg2 = FakeMessage(guild=guild, author=member, content="kcd")
    assert await xp_system.handle_message_xp(msg2) is None


@pytest.mark.asyncio
async def test_message_no_cooldown_with_tag_bonus(fake_db):
    guild = FakeGuild(tag="ELD")
    member = _member_with_tag(guild)
    msg = FakeMessage(guild=guild, author=member, content="hello")

    res = await xp_system.handle_message_xp(msg)
    assert res is not None
    new_xp, *_ = res

    # base 10 +20% => 12
    assert new_xp == 12


@pytest.mark.asyncio
async def test_message_with_cooldown_with_tag_blocks_gain(fake_db):
    guild = FakeGuild(tag="ELD")
    member = _member_with_tag(guild)

    msg1 = FakeMessage(guild=guild, author=member, content="hello")
    assert await xp_system.handle_message_xp(msg1) is not None

    fake_db["now_box"]["now"] += 30
    msg2 = FakeMessage(guild=guild, author=member, content="hello again")
    assert await xp_system.handle_message_xp(msg2) is None


@pytest.mark.asyncio
async def test_message_karuta_kd_no_cooldown_with_tag_bonus_then_small_percent(fake_db):
    guild = FakeGuild(tag="ELD")
    member = _member_with_tag(guild)
    msg = FakeMessage(guild=guild, author=member, content="kd")

    res = await xp_system.handle_message_xp(msg)
    assert res is not None
    new_xp, *_ = res

    # base 10 +20% => 12, puis karuta 30% => round(12*0.3)=4
    assert new_xp == 4


@pytest.mark.asyncio
async def test_message_karuta_kd_with_cooldown_with_tag_blocks_gain(fake_db):
    guild = FakeGuild(tag="ELD")
    member = _member_with_tag(guild)

    msg1 = FakeMessage(guild=guild, author=member, content="kd")
    assert await xp_system.handle_message_xp(msg1) is not None

    fake_db["now_box"]["now"] += 5
    msg2 = FakeMessage(guild=guild, author=member, content="kd")
    assert await xp_system.handle_message_xp(msg2) is None


# =========================
# Tests - Vocal
# =========================

def test_is_voice_member_active_basic():
    guild = FakeGuild()
    m = _active_voice_member(with_tag=False, guild=guild)
    assert xp_system.is_voice_member_active(m) is True


def test_is_voice_member_active_false_when_muted():
    m = FakeMember(voice=FakeVoiceState(channel=object(), self_mute=True))
    assert xp_system.is_voice_member_active(m) is False


def test_is_voice_eligible_in_channel_requires_two_actives():
    guild = FakeGuild()
    m = _active_voice_member(with_tag=False, guild=guild)
    assert xp_system.is_voice_eligible_in_channel(m, active_count=1) is False  # vocal seul
    assert xp_system.is_voice_eligible_in_channel(m, active_count=2) is True


# =========================
# Tests - Server Tag bonus (fonction interne)
# =========================

def test_has_active_server_tag_false_when_primary_guild_missing():
    guild = FakeGuild(tag="ELD")
    member = FakeMember(primary_guild=None)
    assert xp_system._has_active_server_tag_for_guild(member, guild) is False


def test_has_active_server_tag_false_when_identity_disabled():
    guild = FakeGuild(tag="ELD")
    pg = FakePrimaryGuild(identity_enabled=False, identity_guild_id=guild.id, tag=guild.tag)
    member = FakeMember(primary_guild=pg)
    assert xp_system._has_active_server_tag_for_guild(member, guild) is False


def test_has_active_server_tag_false_when_identity_guild_mismatch():
    guild = FakeGuild(tag="ELD")
    pg = FakePrimaryGuild(identity_enabled=True, identity_guild_id=999, tag=guild.tag)
    member = FakeMember(primary_guild=pg)
    assert xp_system._has_active_server_tag_for_guild(member, guild) is False


def test_has_active_server_tag_true_when_tags_match_case_insensitive():
    guild = FakeGuild(tag="eLd")
    pg = FakePrimaryGuild(identity_enabled=True, identity_guild_id=guild.id, tag="ELD")
    member = FakeMember(primary_guild=pg)
    assert xp_system._has_active_server_tag_for_guild(member, guild) is True


def test_has_active_server_tag_false_when_tags_differ_and_both_present():
    guild = FakeGuild(tag="ELD")
    pg = FakePrimaryGuild(identity_enabled=True, identity_guild_id=guild.id, tag="NOPE")
    member = FakeMember(primary_guild=pg)
    assert xp_system._has_active_server_tag_for_guild(member, guild) is False


def test_has_active_server_tag_fallback_via_member__user_primary_guild():
    guild = FakeGuild(tag="ELD")
    pg = FakePrimaryGuild(identity_enabled=True, identity_guild_id=guild.id, tag=guild.tag)

    class _User:
        def __init__(self, primary_guild):
            self.primary_guild = primary_guild

    member = FakeMember(primary_guild=None)
    member._user = _User(primary_guild=pg)

    assert xp_system._has_active_server_tag_for_guild(member, guild) is True


# =========================
# Tests - compute_level
# =========================

def test_compute_level_thresholds():
    levels = [(1, 0), (2, 100), (3, 200)]
    assert xp_system.compute_level(0, levels) == 1
    assert xp_system.compute_level(99, levels) == 1
    assert xp_system.compute_level(100, levels) == 2
    assert xp_system.compute_level(199, levels) == 2
    assert xp_system.compute_level(200, levels) == 3


@pytest.mark.asyncio
async def test_voice_first_tick_initializes_progress(fake_voice_db):
    guild = FakeGuild(tag="ELD")
    member = _active_voice_member(with_tag=False, guild=guild)

    res = await xp_system.tick_voice_xp_for_member(guild, member)
    assert res is None

    prog = fake_voice_db["voice_prog"][(guild.id, member.id)]
    assert int(prog.get("last_tick_ts", 0)) == fake_voice_db["now_box"]["now"]


@pytest.mark.asyncio
async def test_voice_gain_after_interval_without_tag(fake_voice_db):
    guild = FakeGuild(tag="ELD")
    member = _active_voice_member(with_tag=False, guild=guild)

    assert await xp_system.tick_voice_xp_for_member(guild, member) is None

    fake_voice_db["now_box"]["now"] += 60
    res = await xp_system.tick_voice_xp_for_member(guild, member)
    assert res is not None

    new_xp, new_lvl, old_lvl = res
    assert new_xp == 5
    assert old_lvl == 1
    assert new_lvl == 1


@pytest.mark.asyncio
async def test_voice_gain_with_tag_applies_bonus_over_time(fake_voice_db):
    guild = FakeGuild(tag="ELD")
    member = _active_voice_member(with_tag=True, guild=guild)

    assert await xp_system.tick_voice_xp_for_member(guild, member) is None

    fake_voice_db["now_box"]["now"] += 60
    res = await xp_system.tick_voice_xp_for_member(guild, member)
    assert res is not None

    new_xp, *_ = res
    assert new_xp == 6


@pytest.mark.asyncio
async def test_voice_daily_cap_limits_gain(fake_voice_db):
    guild = FakeGuild(tag="ELD")
    member = _active_voice_member(with_tag=False, guild=guild)

    assert await xp_system.tick_voice_xp_for_member(guild, member) is None

    fake_voice_db["now_box"]["now"] += 600  # 10 intervals => 50 xp (cap=50)
    res = await xp_system.tick_voice_xp_for_member(guild, member)
    assert res is not None
    assert res[0] == 50

    fake_voice_db["now_box"]["now"] += 60
    assert await xp_system.tick_voice_xp_for_member(guild, member) is None


@pytest.mark.asyncio
async def test_voice_inactive_member_updates_last_tick_but_gives_no_xp(fake_voice_db):
    guild = FakeGuild(tag="ELD")
    member = _active_voice_member(with_tag=False, guild=guild)

    assert await xp_system.tick_voice_xp_for_member(guild, member) is None
    # rend le membre inactif (mute)
    member.voice = FakeVoiceState(channel=object(), self_mute=True)

    fake_voice_db["now_box"]["now"] += 120
    assert await xp_system.tick_voice_xp_for_member(guild, member) is None

    prog = fake_voice_db["voice_prog"][(guild.id, member.id)]
    assert int(prog.get("last_tick_ts", 0)) == fake_voice_db["now_box"]["now"]
    # pas de xp_today en plus
    assert int(prog.get("xp_today", 0) or 0) == 0


@pytest.mark.asyncio
async def test_voice_daily_reset_resets_progress_and_reinitializes_last_tick(fake_voice_db, monkeypatch):
    guild = FakeGuild(tag="ELD")
    member = _active_voice_member(with_tag=False, guild=guild)

    # init jour 20260118
    assert await xp_system.tick_voice_xp_for_member(guild, member) is None
    fake_voice_db["now_box"]["now"] += 60
    assert await xp_system.tick_voice_xp_for_member(guild, member) is not None

    # change de jour
    monkeypatch.setattr(xp_system, "_day_key_utc", lambda ts=None: "20260119")
    fake_voice_db["now_box"]["now"] += 60

    # reset -> None (car last_tick_ts repasse a 0 puis init)
    assert await xp_system.tick_voice_xp_for_member(guild, member) is None

    prog = fake_voice_db["voice_prog"][(guild.id, member.id)]
    assert prog["day_key"] == "20260119"
    assert int(prog.get("xp_today", 0)) == 0
    assert int(prog.get("buffer_seconds", 0)) == 0
    assert int(prog.get("bonus_cents", 0)) == 0
    assert int(prog.get("last_tick_ts", 0)) == fake_voice_db["now_box"]["now"]


@pytest.mark.asyncio
async def test_voice_delta_is_clamped_to_600_seconds(fake_voice_db):
    # pour isoler le clamp, on pousse le cap tres haut
    fake_voice_db["config"]["voice_daily_cap_xp"] = 10_000

    guild = FakeGuild(tag="ELD")
    member = _active_voice_member(with_tag=False, guild=guild)

    assert await xp_system.tick_voice_xp_for_member(guild, member) is None

    # delta enorme, mais clamp a 600 => 10 intervals (60s) => 10*5=50
    fake_voice_db["now_box"]["now"] += 10_000
    res = await xp_system.tick_voice_xp_for_member(guild, member)
    assert res is not None
    assert res[0] == 50


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value",
    [
        ("voice_daily_cap_xp", 0),
        ("voice_daily_cap_xp", -1),
        ("voice_interval_seconds", 0),
        ("voice_interval_seconds", -10),
        ("voice_xp_per_interval", 0),
        ("voice_xp_per_interval", -5),
    ],
)
async def test_voice_invalid_config_values_give_no_xp(fake_voice_db, field, value):
    fake_voice_db["config"][field] = value

    guild = FakeGuild(tag="ELD")
    member = _active_voice_member(with_tag=False, guild=guild)

    assert await xp_system.tick_voice_xp_for_member(guild, member) is None

    fake_voice_db["now_box"]["now"] += 60
    assert await xp_system.tick_voice_xp_for_member(guild, member) is None


@pytest.mark.asyncio
async def test_voice_buffer_less_than_interval_persists_no_xp(fake_voice_db):
    # interval=60, on avance que de 30s
    guild = FakeGuild(tag="ELD")
    member = _active_voice_member(with_tag=False, guild=guild)

    assert await xp_system.tick_voice_xp_for_member(guild, member) is None
    fake_voice_db["now_box"]["now"] += 30
    assert await xp_system.tick_voice_xp_for_member(guild, member) is None

    prog = fake_voice_db["voice_prog"][(guild.id, member.id)]
    assert int(prog.get("buffer_seconds", 0)) == 30


@pytest.mark.asyncio
async def test_voice_bonus_cents_accumulates_across_ticks(fake_voice_db):
    """Bonus vocal en % cumule en 'cents' jusqu'a atteindre +1 XP."""
    # 1 XP / 60s, bonus 20% => +1 XP tous les 5 ticks
    fake_voice_db["config"].update(
        {
            "voice_xp_per_interval": 1,
            "voice_interval_seconds": 60,
            "voice_daily_cap_xp": 10_000,
            "bonus_percent": 20,
        }
    )
    guild = FakeGuild(tag="ELD")
    member = _active_voice_member(with_tag=True, guild=guild)

    # init
    assert await xp_system.tick_voice_xp_for_member(guild, member) is None

    gained_total = 0
    for _ in range(5):
        fake_voice_db["now_box"]["now"] += 60
        res = await xp_system.tick_voice_xp_for_member(guild, member)
        assert res is not None
        gained_total = res[0]

    # Apres 5 ticks: base=5, bonus=+1 => total 6
    assert gained_total == 6
