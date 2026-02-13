from __future__ import annotations

import pytest

from eldoria.ui.xp import autocompletion as M

# -----------------------------
# Fakes
# -----------------------------

class FakeRole:
    def __init__(self, role_id: int, name: str):
        self.id = role_id
        self.name = name


class FakeGuild:
    def __init__(self, roles: dict[int, FakeRole] | None = None):
        self.id = 123
        self._roles = roles or {}

    def get_role(self, role_id: int):
        return self._roles.get(role_id)


class FakeXpService:
    def __init__(self, role_ids: dict[int, int]):
        self._role_ids = role_ids
        self.calls: list[int] = []

    def get_role_ids(self, guild_id: int):
        self.calls.append(guild_id)
        return self._role_ids


class FakeServices:
    def __init__(self, xp):
        self.xp = xp


class FakeBot:
    def __init__(self, xp):
        self.services = FakeServices(xp)


class FakeInnerInteraction:
    def __init__(self, guild, bot):
        self.guild = guild
        self.client = bot


class FakeAutocompleteContext:
    def __init__(self, guild, bot, value: str | None = None):
        self.interaction = FakeInnerInteraction(guild, bot)
        self.value = value


# -----------------------------
# Tests
# -----------------------------

@pytest.mark.asyncio
async def test_xp_level_role_autocomplete_guild_none():
    ctx = FakeAutocompleteContext(guild=None, bot=None)
    result = await M.xp_level_role_autocomplete(ctx)
    assert result == []


@pytest.mark.asyncio
async def test_xp_level_role_autocomplete_no_roles():
    guild = FakeGuild()
    xp = FakeXpService(role_ids={})
    bot = FakeBot(xp)

    ctx = FakeAutocompleteContext(guild=guild, bot=bot)

    result = await M.xp_level_role_autocomplete(ctx)

    assert result == []
    assert xp.calls == [guild.id]


@pytest.mark.asyncio
async def test_xp_level_role_autocomplete_sorted_and_formatted():
    roles = {
        1: FakeRole(1, "Bronze"),
        2: FakeRole(2, "Silver"),
        3: FakeRole(3, "Gold"),
    }
    guild = FakeGuild(roles=roles)

    # level -> role_id (non trié volontairement)
    xp = FakeXpService(role_ids={3: 3, 1: 1, 2: 2})
    bot = FakeBot(xp)

    ctx = FakeAutocompleteContext(guild=guild, bot=bot)

    result = await M.xp_level_role_autocomplete(ctx)

    assert result == [
        "Level 1 — Bronze",
        "Level 2 — Silver",
        "Level 3 — Gold",
    ]


@pytest.mark.asyncio
async def test_xp_level_role_autocomplete_skips_missing_role():
    guild = FakeGuild(roles={
        1: FakeRole(1, "Bronze"),
        # role_id 2 missing
    })

    xp = FakeXpService(role_ids={1: 1, 2: 2})
    bot = FakeBot(xp)

    ctx = FakeAutocompleteContext(guild=guild, bot=bot)

    result = await M.xp_level_role_autocomplete(ctx)

    assert result == ["Level 1 — Bronze"]


@pytest.mark.asyncio
async def test_xp_level_role_autocomplete_filters_by_user_input():
    roles = {
        1: FakeRole(1, "Bronze"),
        2: FakeRole(2, "Silver"),
        3: FakeRole(3, "Gold"),
    }
    guild = FakeGuild(roles=roles)

    xp = FakeXpService(role_ids={1: 1, 2: 2, 3: 3})
    bot = FakeBot(xp)

    ctx = FakeAutocompleteContext(guild=guild, bot=bot, value="sil")

    result = await M.xp_level_role_autocomplete(ctx)

    assert result == ["Level 2 — Silver"]


@pytest.mark.asyncio
async def test_xp_level_role_autocomplete_limit_25():
    roles = {}
    role_ids = {}

    # 30 niveaux → doit couper à 25
    for i in range(30):
        roles[i] = FakeRole(i, f"Role{i}")
        role_ids[i] = i

    guild = FakeGuild(roles=roles)
    xp = FakeXpService(role_ids=role_ids)
    bot = FakeBot(xp)

    ctx = FakeAutocompleteContext(guild=guild, bot=bot)

    result = await M.xp_level_role_autocomplete(ctx)

    assert len(result) == 25
    assert result[0] == "Level 0 — Role0"
    assert result[-1] == "Level 24 — Role24"
