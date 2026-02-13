from __future__ import annotations

import pytest

# ⚠️ adapte si ton module n’est pas exactement là
from eldoria.ui.roles import autocompletion as M

# ------------------------------------------------------------
# Fakes
# ------------------------------------------------------------

class FakeRoleService:
    def __init__(self, messages):
        self.messages = messages
        self.calls: list[dict] = []

    def sr_list_messages(self, *, guild_id: int, channel_id):
        self.calls.append({"guild_id": guild_id, "channel_id": channel_id})
        return self.messages


class FakeServices:
    def __init__(self, role):
        self.role = role


class FakeBot:
    def __init__(self, role_service):
        self.services = FakeServices(role_service)


class FakeGuild:
    def __init__(self, gid: int):
        self.id = gid


class FakeInteractionInner:
    def __init__(self, *, bot, guild):
        self.client = bot
        self.guild = guild


class FakeAutocompleteContext:
    def __init__(self, *, bot, guild_id=123, value=None, channel_id=999):
        self.value = value
        self.options = {"channel": channel_id}
        self.interaction = FakeInteractionInner(
            bot=bot,
            guild=FakeGuild(guild_id),
        )


# ------------------------------------------------------------
# Tests
# ------------------------------------------------------------

@pytest.mark.asyncio
async def test_autocomplete_filters_case_insensitive_and_calls_service():
    role_service = FakeRoleService(
        messages=["Alpha", "Beta", "Gamma", "alphabet"]
    )
    bot = FakeBot(role_service)

    ctx = FakeAutocompleteContext(
        bot=bot,
        guild_id=42,
        value="Al",
        channel_id=555,
    )

    result = await M.message_secret_role_autocomplete(ctx)

    # filtre insensible à la casse
    assert result == ["Alpha", "alphabet"]

    # service appelé correctement
    assert role_service.calls == [{"guild_id": 42, "channel_id": 555}]


@pytest.mark.asyncio
async def test_autocomplete_limits_to_25_results():
    messages = [f"msg{i}" for i in range(100)]
    role_service = FakeRoleService(messages)
    bot = FakeBot(role_service)

    ctx = FakeAutocompleteContext(bot=bot, value="msg")

    result = await M.message_secret_role_autocomplete(ctx)

    assert len(result) == 25


@pytest.mark.asyncio
async def test_autocomplete_handles_none_value_as_empty_string():
    role_service = FakeRoleService(["One", "Two"])
    bot = FakeBot(role_service)

    ctx = FakeAutocompleteContext(bot=bot, value=None)

    result = await M.message_secret_role_autocomplete(ctx)

    # value None => filtre vide => retourne tous les messages (limite 25)
    assert result == ["One", "Two"]


@pytest.mark.asyncio
async def test_autocomplete_no_match_returns_empty_list():
    role_service = FakeRoleService(["Alpha", "Beta"])
    bot = FakeBot(role_service)

    ctx = FakeAutocompleteContext(bot=bot, value="zzz")

    result = await M.message_secret_role_autocomplete(ctx)

    assert result == []


@pytest.mark.asyncio
async def test_autocomplete_empty_messages_list():
    role_service = FakeRoleService([])
    bot = FakeBot(role_service)

    ctx = FakeAutocompleteContext(bot=bot, value="anything")

    result = await M.message_secret_role_autocomplete(ctx)

    assert result == []
