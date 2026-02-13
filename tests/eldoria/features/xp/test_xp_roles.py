import pytest

from eldoria.features.xp import roles as roles_mod


class FakeRole:
    def __init__(self, role_id: int, name: str = ""):
        self.id = role_id
        self.name = name or f"role-{role_id}"

    def __repr__(self) -> str:  # pragma: no cover
        return f"<FakeRole id={self.id} name={self.name!r}>"


class FakeGuild:
    def __init__(self, guild_id: int = 123, roles: dict[int, FakeRole] | None = None):
        self.id = guild_id
        self._roles = roles or {}

    def get_role(self, role_id: int | None):
        if not role_id:
            return None
        return self._roles.get(role_id)


class FakeMember:
    def __init__(
        self,
        member_id: int = 42,
        *,
        bot: bool = False,
        roles: list[FakeRole] | None = None,
        forbid_on_remove: bool = False,
        forbid_on_add: bool = False,
    ):
        self.id = member_id
        self.bot = bot
        self.roles = roles or []
        self._forbid_on_remove = forbid_on_remove
        self._forbid_on_add = forbid_on_add

        self.removed: list[FakeRole] = []
        self.added: list[FakeRole] = []

    async def remove_roles(self, *roles: FakeRole, reason: str | None = None):
        # import à l'exécution pour utiliser le stub discord installé par conftest
        import discord

        if self._forbid_on_remove:
            raise discord.Forbidden()
        for r in roles:
            if r in self.roles:
                self.roles.remove(r)
            self.removed.append(r)

    async def add_roles(self, *roles: FakeRole, reason: str | None = None):
        import discord

        if self._forbid_on_add:
            raise discord.Forbidden()
        for r in roles:
            if r not in self.roles:
                self.roles.append(r)
            self.added.append(r)


@pytest.mark.asyncio
async def test_sync_member_level_roles_skips_bots(monkeypatch):
    calls: dict[str, int] = {"xp_get_member": 0}

    def _xp_get_member(_gid: int, _mid: int):
        calls["xp_get_member"] += 1
        return (999, None)

    monkeypatch.setattr(roles_mod, "xp_get_member", _xp_get_member)

    guild = FakeGuild(123)
    member = FakeMember(42, bot=True)

    await roles_mod.sync_member_level_roles(guild, member)

    assert calls["xp_get_member"] == 0
    assert member.added == []
    assert member.removed == []


@pytest.mark.asyncio
async def test_sync_member_level_roles_fetches_xp_and_updates_roles(monkeypatch):
    # DB / logique métier mockées
    monkeypatch.setattr(roles_mod, "xp_get_member", lambda gid, mid: (150, None))
    monkeypatch.setattr(roles_mod, "xp_get_levels", lambda gid: [(0, 0), (100, 1), (200, 2)])
    monkeypatch.setattr(roles_mod, "compute_level", lambda xp, levels: 2)

    role_ids = {1: 111, 2: 222, 3: 333}
    monkeypatch.setattr(roles_mod, "xp_get_role_ids", lambda gid: role_ids)

    r111 = FakeRole(111)
    r222 = FakeRole(222)
    r999 = FakeRole(999)

    guild = FakeGuild(123, roles={111: r111, 222: r222, 333: FakeRole(333)})
    member = FakeMember(42, roles=[r111, r999])

    await roles_mod.sync_member_level_roles(guild, member)

    # r111 (lvl role) doit être retiré, r222 ajouté
    assert r111 in member.removed
    assert r222 in member.added
    assert r111 not in member.roles
    assert r222 in member.roles
    # r999 n'est pas un role de level, il doit rester
    assert r999 in member.roles


@pytest.mark.asyncio
async def test_sync_member_level_roles_no_role_ids_noop(monkeypatch):
    monkeypatch.setattr(roles_mod, "xp_get_member", lambda gid, mid: (50, None))
    monkeypatch.setattr(roles_mod, "xp_get_levels", lambda gid: [(0, 0)])
    monkeypatch.setattr(roles_mod, "compute_level", lambda xp, levels: 1)

    monkeypatch.setattr(roles_mod, "xp_get_role_ids", lambda gid: {})

    guild = FakeGuild(123)
    member = FakeMember(42, roles=[FakeRole(111)])

    await roles_mod.sync_member_level_roles(guild, member)

    assert member.added == []
    assert member.removed == []


@pytest.mark.asyncio
async def test_sync_member_level_roles_fallback_to_defaults_when_no_levels(monkeypatch):
    # levels vides => fallback sur XP_LEVELS_DEFAULTS
    monkeypatch.setattr(roles_mod, "xp_get_levels", lambda gid: [])

    # on force des defaults minimalistes (ordre garanti via list(dict.items()))
    monkeypatch.setattr(roles_mod, "XP_LEVELS_DEFAULTS", {1: 0, 2: 100})

    seen: dict[str, object] = {}

    def _compute_level(xp, levels):
        seen["levels"] = levels
        return 1

    monkeypatch.setattr(roles_mod, "compute_level", _compute_level)

    monkeypatch.setattr(roles_mod, "xp_get_member", lambda gid, mid: (10, None))
    monkeypatch.setattr(roles_mod, "xp_get_role_ids", lambda gid: {1: 111})

    r111 = FakeRole(111)
    guild = FakeGuild(123, roles={111: r111})
    member = FakeMember(42, roles=[])

    await roles_mod.sync_member_level_roles(guild, member)

    assert seen["levels"] == list({1: 0, 2: 100}.items())
    assert r111 in member.roles


@pytest.mark.asyncio
async def test_sync_member_level_roles_handles_discord_forbidden(monkeypatch):
    monkeypatch.setattr(roles_mod, "xp_get_member", lambda gid, mid: (150, None))
    monkeypatch.setattr(roles_mod, "xp_get_levels", lambda gid: [(0, 0)])
    monkeypatch.setattr(roles_mod, "compute_level", lambda xp, levels: 2)
    monkeypatch.setattr(roles_mod, "xp_get_role_ids", lambda gid: {2: 222, 1: 111})

    r111 = FakeRole(111)
    r222 = FakeRole(222)
    guild = FakeGuild(123, roles={111: r111, 222: r222})

    member = FakeMember(42, roles=[r111], forbid_on_remove=True)

    # ne doit PAS lever
    await roles_mod.sync_member_level_roles(guild, member)


@pytest.mark.asyncio
async def test_sync_xp_roles_for_users_returns_when_disabled(monkeypatch):
    calls: dict[str, int] = {"get_member": 0, "sync": 0}

    monkeypatch.setattr(roles_mod, "xp_is_enabled", lambda gid: False)

    async def _get_member_by_id_or_raise(*, guild, member_id: int):
        calls["get_member"] += 1
        raise AssertionError("Ne devrait pas être appelé si XP disabled")

    async def _sync_member_level_roles(guild, member, *, xp=None):
        calls["sync"] += 1

    monkeypatch.setattr(roles_mod, "get_member_by_id_or_raise", _get_member_by_id_or_raise)
    monkeypatch.setattr(roles_mod, "sync_member_level_roles", _sync_member_level_roles)

    guild = FakeGuild(123)
    await roles_mod.sync_xp_roles_for_users(guild, [1, 2, 3])

    assert calls == {"get_member": 0, "sync": 0}


@pytest.mark.asyncio
async def test_sync_xp_roles_for_users_processes_each_user_and_continues_on_errors(monkeypatch):
    monkeypatch.setattr(roles_mod, "xp_is_enabled", lambda gid: True)

    members = {
        1: FakeMember(1),
        2: FakeMember(2),
    }

    async def _get_member_by_id_or_raise(*, guild, member_id: int):
        if member_id == 99:
            raise RuntimeError("user not found")
        return members[member_id]

    seen: list[int] = []

    async def _sync_member_level_roles(guild, member, *, xp=None):
        assert xp is None  # doit relire en DB selon la docstring
        seen.append(member.id)

    monkeypatch.setattr(roles_mod, "get_member_by_id_or_raise", _get_member_by_id_or_raise)
    monkeypatch.setattr(roles_mod, "sync_member_level_roles", _sync_member_level_roles)

    guild = FakeGuild(123)
    await roles_mod.sync_xp_roles_for_users(guild, [1, 99, 2])

    assert seen == [1, 2]


def test_get_xp_role_ids_returns_empty_when_guild_id_missing():
    assert roles_mod.get_xp_role_ids(None) == {}
    assert roles_mod.get_xp_role_ids(0) == {}


def test_get_xp_role_ids_returns_empty_on_none_result(monkeypatch):
    monkeypatch.setattr(roles_mod, "xp_get_role_ids", lambda gid: None)
    assert roles_mod.get_xp_role_ids(123) == {}


def test_get_xp_role_ids_returns_empty_on_exception(monkeypatch):
    def _boom(_gid: int):
        raise RuntimeError("db down")

    monkeypatch.setattr(roles_mod, "xp_get_role_ids", _boom)
    assert roles_mod.get_xp_role_ids(123) == {}
