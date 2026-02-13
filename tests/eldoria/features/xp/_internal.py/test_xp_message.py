import pytest

from eldoria.features.xp._internal import message_xp as mod


class FakeGuild:
    def __init__(self, guild_id: int = 123):
        self.id = guild_id


class FakeMember:
    def __init__(self, member_id: int = 42, *, bot: bool = False):
        self.id = member_id
        self.bot = bot


class FakeMessage:
    def __init__(self, *, guild, author, content: str | None):
        self.guild = guild
        self.author = author
        self.content = content


class _Cfg:
    """
    Remplace XpConfig(**raw) simplement, pour éviter les dépendances sur defaults.
    """
    def __init__(
        self,
        *,
        enabled: bool = True,
        points_per_message: int = 10,
        cooldown_seconds: int = 60,
        bonus_percent: int = 0,
        karuta_k_small_percent: int = 30,
        **_extra,
    ):
        self.enabled = enabled
        self.points_per_message = points_per_message
        self.cooldown_seconds = cooldown_seconds
        self.bonus_percent = bonus_percent
        self.karuta_k_small_percent = karuta_k_small_percent


@pytest.mark.asyncio
async def test_returns_none_when_no_guild(monkeypatch):
    monkeypatch.setattr(mod, "xp_get_config", lambda _gid: {"enabled": True})
    monkeypatch.setattr(mod, "XpConfig", _Cfg)

    msg = FakeMessage(guild=None, author=FakeMember(), content="hello")
    assert await mod.handle_message_xp(msg) is None


@pytest.mark.asyncio
async def test_returns_none_when_author_is_bot(monkeypatch):
    monkeypatch.setattr(mod, "xp_get_config", lambda _gid: {"enabled": True})
    monkeypatch.setattr(mod, "XpConfig", _Cfg)

    msg = FakeMessage(guild=FakeGuild(), author=FakeMember(bot=True), content="hello")
    assert await mod.handle_message_xp(msg) is None


@pytest.mark.asyncio
async def test_returns_none_when_xp_disabled(monkeypatch):
    monkeypatch.setattr(mod, "xp_get_config", lambda _gid: {"enabled": False})
    monkeypatch.setattr(mod, "XpConfig", _Cfg)

    # Si XP disabled, ne doit pas toucher au reste
    monkeypatch.setattr(mod, "xp_get_member", lambda *_: (_ for _ in ()).throw(AssertionError("should not be called")))
    msg = FakeMessage(guild=FakeGuild(), author=FakeMember(), content="hello")
    assert await mod.handle_message_xp(msg) is None


@pytest.mark.asyncio
async def test_returns_none_when_cooldown_not_passed(monkeypatch):
    guild = FakeGuild(123)
    member = FakeMember(42)

    monkeypatch.setattr(mod, "xp_get_config", lambda _gid: {"enabled": True, "cooldown_seconds": 10, "points_per_message": 5})
    monkeypatch.setattr(mod, "XpConfig", _Cfg)

    monkeypatch.setattr(mod, "now_ts", lambda: 1_000)
    monkeypatch.setattr(mod, "xp_get_member", lambda _gid, _mid: (100, 995))  # now-last = 5 < 10

    # ne doit pas ajouter d'xp
    monkeypatch.setattr(mod, "xp_add_xp", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("should not add xp")))
    msg = FakeMessage(guild=guild, author=member, content="hello")
    assert await mod.handle_message_xp(msg) is None


@pytest.mark.asyncio
async def test_returns_none_when_points_per_message_results_in_zero(monkeypatch):
    guild = FakeGuild(123)
    member = FakeMember(42)

    monkeypatch.setattr(mod, "xp_get_config", lambda _gid: {"enabled": True, "points_per_message": -5})
    monkeypatch.setattr(mod, "XpConfig", _Cfg)

    monkeypatch.setattr(mod, "now_ts", lambda: 1_000)
    monkeypatch.setattr(mod, "xp_get_member", lambda _gid, _mid: (100, 0))

    monkeypatch.setattr(mod, "xp_add_xp", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("should not add xp")))
    msg = FakeMessage(guild=guild, author=member, content="hello")
    assert await mod.handle_message_xp(msg) is None


@pytest.mark.asyncio
async def test_happy_path_adds_xp_computes_levels_and_syncs_roles(monkeypatch):
    guild = FakeGuild(123)
    member = FakeMember(42)

    monkeypatch.setattr(mod, "xp_get_config", lambda _gid: {"enabled": True, "points_per_message": 8, "cooldown_seconds": 0, "bonus_percent": 0})
    monkeypatch.setattr(mod, "XpConfig", _Cfg)

    monkeypatch.setattr(mod, "now_ts", lambda: 1_000)
    monkeypatch.setattr(mod, "xp_get_member", lambda _gid, _mid: (100, 0))

    add_calls = []

    def _xp_add_xp(gid, mid, gained, *, set_last_xp_ts):
        add_calls.append((gid, mid, gained, set_last_xp_ts))
        return 108

    monkeypatch.setattr(mod, "xp_add_xp", _xp_add_xp)

    monkeypatch.setattr(mod, "xp_get_levels", lambda _gid: [(1, 0), (2, 100), (3, 200)])

    compute_calls = []

    def _compute_level(xp, levels):
        compute_calls.append((xp, list(levels)))
        # simple: lvl 1 <100, lvl 2 <200, lvl3 >=200
        return 3 if xp >= 200 else 2 if xp >= 100 else 1

    monkeypatch.setattr(mod, "compute_level", _compute_level)

    sync_calls = []

    async def _sync_member_level_roles(g, m, *, xp=None):
        sync_calls.append((g.id, m.id, xp))

    monkeypatch.setattr(mod, "sync_member_level_roles", _sync_member_level_roles)

    # bonus tag off
    monkeypatch.setattr(mod, "has_active_server_tag_for_guild", lambda *_: False)

    msg = FakeMessage(guild=guild, author=member, content="hello")
    res = await mod.handle_message_xp(msg)

    assert res == (108, 2, 2)
    assert add_calls == [(123, 42, 8, 1_000)]
    assert compute_calls[0][0] == 100  # old_xp
    assert compute_calls[1][0] == 108  # new_xp
    assert sync_calls == [(123, 42, 108)]


@pytest.mark.asyncio
async def test_bonus_applied_when_server_tag_active(monkeypatch):
    guild = FakeGuild(123)
    member = FakeMember(42)

    monkeypatch.setattr(
        mod,
        "xp_get_config",
        lambda _gid: {"enabled": True, "points_per_message": 10, "cooldown_seconds": 0, "bonus_percent": 50},
    )
    monkeypatch.setattr(mod, "XpConfig", _Cfg)

    monkeypatch.setattr(mod, "now_ts", lambda: 1_000)
    monkeypatch.setattr(mod, "xp_get_member", lambda _gid, _mid: (0, 0))

    add_calls = []

    def _xp_add_xp(gid, mid, gained, *, set_last_xp_ts):
        add_calls.append(gained)
        return gained

    monkeypatch.setattr(mod, "xp_add_xp", _xp_add_xp)
    monkeypatch.setattr(mod, "xp_get_levels", lambda _gid: [(1, 0)])
    monkeypatch.setattr(mod, "compute_level", lambda xp, levels: 1)

    async def _sync(*_a, **_k):
        return None

    monkeypatch.setattr(mod, "sync_member_level_roles", _sync)
    monkeypatch.setattr(mod, "has_active_server_tag_for_guild", lambda *_: True)

    msg = FakeMessage(guild=guild, author=member, content="hello")
    res = await mod.handle_message_xp(msg)

    assert res == (15, 1, 1)  # 10 * 1.5 = 15
    assert add_calls == [15]


@pytest.mark.asyncio
async def test_karuta_small_k_message_applies_malus(monkeypatch):
    guild = FakeGuild(123)
    member = FakeMember(42)

    monkeypatch.setattr(
        mod,
        "xp_get_config",
        lambda _gid: {"enabled": True, "points_per_message": 10, "cooldown_seconds": 0, "bonus_percent": 0, "karuta_k_small_percent": 30},
    )
    monkeypatch.setattr(mod, "XpConfig", _Cfg)

    monkeypatch.setattr(mod, "now_ts", lambda: 1_000)
    monkeypatch.setattr(mod, "xp_get_member", lambda _gid, _mid: (0, 0))

    add_calls = []

    def _xp_add_xp(gid, mid, gained, *, set_last_xp_ts):
        add_calls.append(gained)
        return gained

    monkeypatch.setattr(mod, "xp_add_xp", _xp_add_xp)
    monkeypatch.setattr(mod, "xp_get_levels", lambda _gid: [(1, 0)])
    monkeypatch.setattr(mod, "compute_level", lambda xp, levels: 1)

    async def _sync(*_a, **_k):
        return None

    monkeypatch.setattr(mod, "sync_member_level_roles", _sync)
    monkeypatch.setattr(mod, "has_active_server_tag_for_guild", lambda *_: False)

    msg = FakeMessage(guild=guild, author=member, content="k")
    res = await mod.handle_message_xp(msg)

    assert res == (3, 1, 1)  # 10 * 0.30 = 3
    assert add_calls == [3]


@pytest.mark.asyncio
async def test_bonus_then_karuta_malus_order(monkeypatch):
    """
    L'impl applique d'abord le bonus, puis le malus karuta.
    """
    guild = FakeGuild(123)
    member = FakeMember(42)

    monkeypatch.setattr(
        mod,
        "xp_get_config",
        lambda _gid: {
            "enabled": True,
            "points_per_message": 10,
            "cooldown_seconds": 0,
            "bonus_percent": 50,            # => 15
            "karuta_k_small_percent": 30,   # => 4.5 arrondi => 4 (round banker's)
        },
    )
    monkeypatch.setattr(mod, "XpConfig", _Cfg)

    monkeypatch.setattr(mod, "now_ts", lambda: 1_000)
    monkeypatch.setattr(mod, "xp_get_member", lambda _gid, _mid: (0, 0))

    add_calls = []

    def _xp_add_xp(gid, mid, gained, *, set_last_xp_ts):
        add_calls.append(gained)
        return gained

    monkeypatch.setattr(mod, "xp_add_xp", _xp_add_xp)
    monkeypatch.setattr(mod, "xp_get_levels", lambda _gid: [(1, 0)])
    monkeypatch.setattr(mod, "compute_level", lambda xp, levels: 1)

    async def _sync(*_a, **_k):
        return None

    monkeypatch.setattr(mod, "sync_member_level_roles", _sync)
    monkeypatch.setattr(mod, "has_active_server_tag_for_guild", lambda *_: True)

    msg = FakeMessage(guild=guild, author=member, content="kcd")  # len<=10 + startswith k
    res = await mod.handle_message_xp(msg)

    # 10 -> bonus 50% => 15 -> malus 30% => 4.5 -> round(4.5)=4 (banker's rounding)
    assert res == (4, 1, 1)
    assert add_calls == [4]


@pytest.mark.asyncio
async def test_content_none_or_blank_does_not_trigger_karuta(monkeypatch):
    guild = FakeGuild(123)
    member = FakeMember(42)

    monkeypatch.setattr(
        mod,
        "xp_get_config",
        lambda _gid: {"enabled": True, "points_per_message": 10, "cooldown_seconds": 0, "bonus_percent": 0, "karuta_k_small_percent": 30},
    )
    monkeypatch.setattr(mod, "XpConfig", _Cfg)

    monkeypatch.setattr(mod, "now_ts", lambda: 1_000)
    monkeypatch.setattr(mod, "xp_get_member", lambda _gid, _mid: (0, 0))

    add_calls = []

    def _xp_add_xp(gid, mid, gained, *, set_last_xp_ts):
        add_calls.append(gained)
        return gained

    monkeypatch.setattr(mod, "xp_add_xp", _xp_add_xp)
    monkeypatch.setattr(mod, "xp_get_levels", lambda _gid: [(1, 0)])
    monkeypatch.setattr(mod, "compute_level", lambda xp, levels: 1)

    async def _sync(*_a, **_k):
        return None

    monkeypatch.setattr(mod, "sync_member_level_roles", _sync)
    monkeypatch.setattr(mod, "has_active_server_tag_for_guild", lambda *_: False)

    msg1 = FakeMessage(guild=guild, author=member, content=None)
    msg2 = FakeMessage(guild=guild, author=member, content="   ")

    assert await mod.handle_message_xp(msg1) == (10, 1, 1)
    assert await mod.handle_message_xp(msg2) == (10, 1, 1)
    assert add_calls == [10, 10]
