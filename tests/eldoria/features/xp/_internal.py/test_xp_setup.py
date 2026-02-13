import pytest

from eldoria.features.xp._internal import setup as mod


class FakeRole:
    def __init__(self, role_id: int, name: str):
        self.id = role_id
        self.name = name

    def __repr__(self) -> str:  # pragma: no cover
        return f"<FakeRole id={self.id} name={self.name!r}>"


class FakeGuild:
    def __init__(self, guild_id: int = 123, roles: list[FakeRole] | None = None):
        self.id = guild_id
        self.roles = roles or []
        self.created: list[str] = []
        self._forbidden_on_create = False
        self._next_id = 10_000

    async def create_role(self, *, name: str, reason: str):
        import discord

        if self._forbidden_on_create:
            raise discord.Forbidden()

        self.created.append(name)
        self._next_id += 1
        role = FakeRole(self._next_id, name)
        # discord crée le rôle dans guild.roles, on simule pareil
        self.roles.append(role)
        return role


def _patch_discord_utils_get(monkeypatch):
    """
    ensure_guild_xp_setup() utilise discord.utils.get(guild.roles, name="levelX").
    On patch discord.utils.get avec une impl simple.
    """
    import discord

    def fake_get(iterable, **attrs):
        # uniquement 'name' dans notre cas
        name = attrs.get("name")
        for r in iterable:
            if getattr(r, "name", None) == name:
                return r
        return None

    monkeypatch.setattr(discord.utils, "get", fake_get, raising=True)


@pytest.mark.asyncio
async def test_ensure_calls_ensure_defaults(monkeypatch):
    guild = FakeGuild(123, roles=[])

    calls = {"ensure": []}

    def fake_ensure_defaults(gid, defaults):
        calls["ensure"].append((gid, defaults))

    monkeypatch.setattr(mod, "xp_ensure_defaults", fake_ensure_defaults, raising=True)
    monkeypatch.setattr(mod, "xp_get_role_ids", lambda _gid: {}, raising=True)
    monkeypatch.setattr(mod, "xp_upsert_role_id", lambda *_a, **_k: None, raising=True)

    _patch_discord_utils_get(monkeypatch)

    await mod.ensure_guild_xp_setup(guild)

    assert len(calls["ensure"]) == 1
    assert calls["ensure"][0][0] == 123
    assert calls["ensure"][0][1] is mod.XP_LEVELS_DEFAULTS


@pytest.mark.asyncio
async def test_ensure_prefers_db_role_id_when_role_exists(monkeypatch):
    # DB dit: lvl5 => role id 555
    r555 = FakeRole(555, "some-other-name")
    guild = FakeGuild(123, roles=[r555])

    monkeypatch.setattr(mod, "xp_ensure_defaults", lambda *_: None, raising=True)
    monkeypatch.setattr(mod, "xp_get_role_ids", lambda _gid: {5: 555}, raising=True)

    upserts = []

    def fake_upsert(gid, lvl, rid):
        upserts.append((gid, lvl, rid))

    monkeypatch.setattr(mod, "xp_upsert_role_id", fake_upsert, raising=True)

    _patch_discord_utils_get(monkeypatch)

    await mod.ensure_guild_xp_setup(guild)

    # lvl5 doit prendre r555 (pas besoin de name level5)
    assert (123, 5, 555) in upserts
    # les autres doivent être créés car absents (et donc upsert avec leurs ids)
    assert len(upserts) == 5


@pytest.mark.asyncio
async def test_ensure_fallback_by_name_when_db_id_missing_or_not_found(monkeypatch):
    # DB donne un id introuvable pour lvl4, mais on a un role nommé level4
    r_level4 = FakeRole(444, "level4")
    guild = FakeGuild(123, roles=[r_level4])

    monkeypatch.setattr(mod, "xp_ensure_defaults", lambda *_: None, raising=True)
    monkeypatch.setattr(mod, "xp_get_role_ids", lambda _gid: {4: 9999}, raising=True)

    upserts = []
    monkeypatch.setattr(mod, "xp_upsert_role_id", lambda gid, lvl, rid: upserts.append((lvl, rid)), raising=True)

    _patch_discord_utils_get(monkeypatch)

    await mod.ensure_guild_xp_setup(guild)

    # lvl4 doit matcher par nom et upsert l'id 444
    assert (4, 444) in upserts
    assert len(upserts) == 5


@pytest.mark.asyncio
async def test_ensure_creates_missing_roles_and_upserts(monkeypatch):
    guild = FakeGuild(123, roles=[])

    monkeypatch.setattr(mod, "xp_ensure_defaults", lambda *_: None, raising=True)
    monkeypatch.setattr(mod, "xp_get_role_ids", lambda _gid: {}, raising=True)

    upserts = []
    monkeypatch.setattr(mod, "xp_upsert_role_id", lambda gid, lvl, rid: upserts.append((lvl, rid)), raising=True)

    _patch_discord_utils_get(monkeypatch)

    await mod.ensure_guild_xp_setup(guild)

    # créé level5..level1 dans cet ordre
    assert guild.created == ["level5", "level4", "level3", "level2", "level1"]

    # upsert appelé pour chaque lvl (5..1)
    assert [lvl for (lvl, _rid) in upserts] == [5, 4, 3, 2, 1]
    assert len({rid for (_lvl, rid) in upserts}) == 5  # IDs distincts
    # et les rôles existent dans guild.roles maintenant
    assert {r.name for r in guild.roles} == {"level5", "level4", "level3", "level2", "level1"}


@pytest.mark.asyncio
async def test_ensure_stops_cleanly_on_forbidden_create(monkeypatch):
    # Aucun role existant => il essaie de créer level5 en premier, et Forbidden => return
    guild = FakeGuild(123, roles=[])
    guild._forbidden_on_create = True

    monkeypatch.setattr(mod, "xp_ensure_defaults", lambda *_: None, raising=True)
    monkeypatch.setattr(mod, "xp_get_role_ids", lambda _gid: {}, raising=True)

    upserts = []
    monkeypatch.setattr(mod, "xp_upsert_role_id", lambda gid, lvl, rid: upserts.append((lvl, rid)), raising=True)

    _patch_discord_utils_get(monkeypatch)

    await mod.ensure_guild_xp_setup(guild)

    # rien créé, rien upsert
    assert guild.created == []
    assert upserts == []


@pytest.mark.asyncio
async def test_ensure_no_duplicate_create_if_role_exists_by_name(monkeypatch):
    # Les roles level1..level5 existent déjà => aucune création
    roles = [FakeRole(100 + i, f"level{i}") for i in range(1, 6)]
    guild = FakeGuild(123, roles=roles)

    monkeypatch.setattr(mod, "xp_ensure_defaults", lambda *_: None, raising=True)
    monkeypatch.setattr(mod, "xp_get_role_ids", lambda _gid: {}, raising=True)

    upserts = []
    monkeypatch.setattr(mod, "xp_upsert_role_id", lambda gid, lvl, rid: upserts.append((lvl, rid)), raising=True)

    _patch_discord_utils_get(monkeypatch)

    await mod.ensure_guild_xp_setup(guild)

    assert guild.created == []  # rien créé
    # upsert pour 5..1 avec les ids correspondants
    assert [lvl for (lvl, _rid) in upserts] == [5, 4, 3, 2, 1]
    # check un exemple : lvl3 => role "level3" => id 103
    assert (3, 103) in upserts


@pytest.mark.asyncio
async def test_ensure_db_role_id_takes_precedence_over_name(monkeypatch):
    # Cas important : DB dit lvl2 => role id 222, mais il existe aussi un role nommé level2 avec autre id.
    # L'impl doit prendre d'abord l'ID DB.
    r_db = FakeRole(222, "not-level2")
    r_name = FakeRole(999, "level2")
    guild = FakeGuild(123, roles=[r_db, r_name])

    monkeypatch.setattr(mod, "xp_ensure_defaults", lambda *_: None, raising=True)
    monkeypatch.setattr(mod, "xp_get_role_ids", lambda _gid: {2: 222}, raising=True)

    upserts = []
    monkeypatch.setattr(mod, "xp_upsert_role_id", lambda gid, lvl, rid: upserts.append((lvl, rid)), raising=True)

    _patch_discord_utils_get(monkeypatch)

    await mod.ensure_guild_xp_setup(guild)

    # lvl2 doit pointer vers 222 et non 999
    assert (2, 222) in upserts
    assert (2, 999) not in upserts
