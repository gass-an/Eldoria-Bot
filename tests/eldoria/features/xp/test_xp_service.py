import pytest

import eldoria.features.xp.xp_service as svc_mod


@pytest.fixture()
def svc():
    return svc_mod.XpService()


# --------------------------
# Sync methods (delegation)
# --------------------------

def test_is_voice_member_active_delegates(svc, monkeypatch):
    called = {}

    def fake(member):
        called["member"] = member
        return True

    monkeypatch.setattr(svc_mod.voice_xp, "is_voice_member_active", fake)

    m = object()
    assert svc.is_voice_member_active(m) is True
    assert called["member"] is m


def test_compute_level_delegates(svc, monkeypatch):
    called = {}

    def fake(xp, level):
        called["xp"] = xp
        called["level"] = list(level)
        return 7

    monkeypatch.setattr(svc_mod.levels, "compute_level", fake)

    assert svc.compute_level(123, [(0, 0), (10, 1)]) == 7
    assert called == {"xp": 123, "level": [(0, 0), (10, 1)]}


def test_build_snapshot_for_xp_profile_delegates(svc, monkeypatch):
    guild = object()
    called = {}

    def fake(g, uid):
        called["args"] = (g, uid)
        return {"ok": True}

    monkeypatch.setattr(svc_mod.snapshot, "build_snapshot_for_xp_profile", fake)

    assert svc.build_snapshot_for_xp_profile(guild, 42) == {"ok": True}
    assert called["args"] == (guild, 42)


def test_get_leaderboard_items_delegates_with_defaults(svc, monkeypatch):
    guild = object()
    called = {}

    def fake(g, *, limit, offset):
        called["args"] = (g, limit, offset)
        return [(1, 10, 1, "u")]

    monkeypatch.setattr(svc_mod.snapshot, "get_leaderboard_items", fake)

    out = svc.get_leaderboard_items(guild)
    assert out == [(1, 10, 1, "u")]
    assert called["args"] == (guild, 200, 0)


def test_get_leaderboard_items_delegates_with_custom_params(svc, monkeypatch):
    guild = object()
    called = {}

    def fake(g, *, limit, offset):
        called["args"] = (g, limit, offset)
        return []

    monkeypatch.setattr(svc_mod.snapshot, "get_leaderboard_items", fake)

    svc.get_leaderboard_items(guild, limit=50, offset=100)
    assert called["args"] == (guild, 50, 100)


def test_is_enabled_delegates(svc, monkeypatch):
    monkeypatch.setattr(svc_mod.xp_repo, "xp_is_enabled", lambda gid: gid == 1)
    assert svc.is_enabled(1) is True
    assert svc.is_enabled(2) is False


def test_ensure_defaults_delegates(svc, monkeypatch):
    called = {}

    def fake(gid, default_levels):
        called["args"] = (gid, default_levels)

    monkeypatch.setattr(svc_mod.xp_repo, "xp_ensure_defaults", fake)

    svc.ensure_defaults(10, {1: 0})
    assert called["args"] == (10, {1: 0})


def test_get_config_delegates(svc, monkeypatch):
    monkeypatch.setattr(svc_mod.xp_repo, "xp_get_config", lambda gid: {"gid": gid})
    assert svc.get_config(99) == {"gid": 99}


def test_get_role_ids_delegates(svc, monkeypatch):
    monkeypatch.setattr(svc_mod.xp_repo, "xp_get_role_ids", lambda gid: {1: 111})
    assert svc.get_role_ids(10) == {1: 111}


def test_get_levels_with_roles_delegates(svc, monkeypatch):
    monkeypatch.setattr(
        svc_mod.xp_repo,
        "xp_get_levels_with_roles",
        lambda gid: [(1, 0, None), (2, 10, 222)],
    )
    assert svc.get_levels_with_roles(10) == [(1, 0, None), (2, 10, 222)]


def test_set_level_threshold_delegates(svc, monkeypatch):
    called = {}

    def fake(gid, level, xp_required):
        called["args"] = (gid, level, xp_required)

    monkeypatch.setattr(svc_mod.xp_repo, "xp_set_level_threshold", fake)

    svc.set_level_threshold(10, 3, 1234)
    assert called["args"] == (10, 3, 1234)


def test_upsert_role_id_delegates(svc, monkeypatch):
    called = {}

    def fake(gid, level, role_id):
        called["args"] = (gid, level, role_id)

    monkeypatch.setattr(svc_mod.xp_repo, "xp_upsert_role_id", fake)

    svc.upsert_role_id(10, 3, 999)
    assert called["args"] == (10, 3, 999)


def test_get_levels_delegates(svc, monkeypatch):
    monkeypatch.setattr(svc_mod.xp_repo, "xp_get_levels", lambda gid: [(1, 0), (2, 10)])
    assert svc.get_levels(10) == [(1, 0), (2, 10)]


def test_add_xp_delegates_all_kwargs(svc, monkeypatch):
    called = {}

    def fake(*, guild_id, user_id, delta, set_last_xp_ts=None, conn=None):
        called["args"] = (guild_id, user_id, delta, set_last_xp_ts, conn)
        return 123

    monkeypatch.setattr(svc_mod.xp_repo, "xp_add_xp", fake)

    conn = object()
    out = svc.add_xp(10, 42, 5, set_last_xp_ts=777, conn=conn)

    assert out == 123
    assert called["args"] == (10, 42, 5, 777, conn)


def test_voice_upsert_progress_delegates(svc, monkeypatch):
    called = {}

    def fake(gid, uid, *, day_key=None, last_tick_ts=None, buffer_seconds=None, bonus_cents=None, xp_today=None):
        called["args"] = (gid, uid, day_key, last_tick_ts, buffer_seconds, bonus_cents, xp_today)

    monkeypatch.setattr(svc_mod.xp_repo, "xp_voice_upsert_progress", fake)

    svc.voice_upsert_progress(
        10,
        42,
        day_key="2026-02-12",
        last_tick_ts=100,
        buffer_seconds=20,
        bonus_cents=15,
        xp_today=9,
    )

    assert called["args"] == (10, 42, "2026-02-12", 100, 20, 15, 9)


def test_set_config_delegates(svc, monkeypatch):
    called = {}

    def fake(gid, **kwargs):
        called["gid"] = gid
        called["kwargs"] = dict(kwargs)

    monkeypatch.setattr(svc_mod.xp_repo, "xp_set_config", fake)

    svc.set_config(
        10,
        enabled=True,
        points_per_message=2,
        cooldown_seconds=3,
        bonus_percent=4,
        karuta_k_small_percent=5,
        voice_enabled=True,
        voice_xp_per_interval=6,
        voice_interval_seconds=7,
        voice_daily_cap_xp=8,
        voice_levelup_channel_id=9,
    )

    assert called["gid"] == 10
    assert called["kwargs"] == {
        "enabled": True,
        "points_per_message": 2,
        "cooldown_seconds": 3,
        "bonus_percent": 4,
        "karuta_k_small_percent": 5,
        "voice_enabled": True,
        "voice_xp_per_interval": 6,
        "voice_interval_seconds": 7,
        "voice_daily_cap_xp": 8,
        "voice_levelup_channel_id": 9,
    }


# --------------------------
# Async methods (delegation)
# --------------------------

@pytest.mark.asyncio
async def test_handle_message_xp_delegates(svc, monkeypatch):
    called = {}

    async def fake(message):
        called["message"] = message
        return (1, 2, 3)

    monkeypatch.setattr(svc_mod.message_xp, "handle_message_xp", fake)

    msg = object()
    assert await svc.handle_message_xp(msg) == (1, 2, 3)
    assert called["message"] is msg


@pytest.mark.asyncio
async def test_sync_xp_roles_for_users_delegates(svc, monkeypatch):
    called = {}

    async def fake(guild, user_ids):
        called["args"] = (guild, list(user_ids))

    monkeypatch.setattr(svc_mod.roles, "sync_xp_roles_for_users", fake)

    g = object()
    await svc.sync_xp_roles_for_users(g, [1, 2, 3])
    assert called["args"] == (g, [1, 2, 3])


@pytest.mark.asyncio
async def test_sync_member_level_roles_delegates(svc, monkeypatch):
    called = {}

    async def fake(guild, member, *, xp=None):
        called["args"] = (guild, member, xp)

    monkeypatch.setattr(svc_mod.roles, "sync_member_level_roles", fake)

    g = object()
    m = object()

    await svc.sync_member_level_roles(g, m, xp=123)
    assert called["args"] == (g, m, 123)


@pytest.mark.asyncio
async def test_tick_voice_xp_for_member_delegates(svc, monkeypatch):
    called = {}

    async def fake(guild, member):
        called["args"] = (guild, member)
        return (10, 20, 30)

    monkeypatch.setattr(svc_mod.voice_xp, "tick_voice_xp_for_member", fake)

    g = object()
    m = object()

    assert await svc.tick_voice_xp_for_member(g, m) == (10, 20, 30)
    assert called["args"] == (g, m)


@pytest.mark.asyncio
async def test_ensure_guild_xp_setup_delegates(svc, monkeypatch):
    called = {}

    async def fake(guild):
        called["guild"] = guild

    monkeypatch.setattr(svc_mod.setup, "ensure_guild_xp_setup", fake)

    g = object()
    await svc.ensure_guild_xp_setup(g)
    assert called["guild"] is g
