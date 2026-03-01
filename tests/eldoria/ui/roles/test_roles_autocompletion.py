from __future__ import annotations

from types import SimpleNamespace

import pytest

from eldoria.ui.roles import autocompletion as M


def make_role_service(messages):
    calls: list[dict] = []

    def sr_list_messages(*, guild_id: int, channel_id):
        calls.append({"guild_id": guild_id, "channel_id": channel_id})
        return list(messages)

    return SimpleNamespace(messages=list(messages), calls=calls, sr_list_messages=sr_list_messages)


def make_ctx(*, bot, guild_id=123, value=None, channel_id=999):
    return SimpleNamespace(
        value=value,
        options={"channel": channel_id},
        interaction=SimpleNamespace(
            client=bot,
            guild=SimpleNamespace(id=guild_id),
        ),
    )


# ------------------------------------------------------------
# Tests
# ------------------------------------------------------------

@pytest.mark.asyncio
async def test_autocomplete_filters_case_insensitive_and_calls_service():
    role_service = make_role_service(messages=["Alpha", "Beta", "Gamma", "alphabet"])
    bot = SimpleNamespace(services=SimpleNamespace(role=role_service))

    ctx = make_ctx(bot=bot, guild_id=42, value="Al", channel_id=555)

    result = await M.message_secret_role_autocomplete(ctx)

    # filtre insensible à la casse
    assert result == ["Alpha", "alphabet"]

    # service appelé correctement
    assert role_service.calls == [{"guild_id": 42, "channel_id": 555}]


@pytest.mark.asyncio
async def test_autocomplete_limits_to_25_results():
    messages = [f"msg{i}" for i in range(100)]
    role_service = make_role_service(messages)
    bot = SimpleNamespace(services=SimpleNamespace(role=role_service))

    ctx = make_ctx(bot=bot, value="msg")

    result = await M.message_secret_role_autocomplete(ctx)

    assert len(result) == 25


@pytest.mark.asyncio
async def test_autocomplete_handles_none_value_as_empty_string():
    role_service = make_role_service(["One", "Two"])
    bot = SimpleNamespace(services=SimpleNamespace(role=role_service))

    ctx = make_ctx(bot=bot, value=None)

    result = await M.message_secret_role_autocomplete(ctx)

    # value None => filtre vide => retourne tous les messages (limite 25)
    assert result == ["One", "Two"]


@pytest.mark.asyncio
async def test_autocomplete_no_match_returns_empty_list():
    role_service = make_role_service(["Alpha", "Beta"])
    bot = SimpleNamespace(services=SimpleNamespace(role=role_service))

    ctx = make_ctx(bot=bot, value="zzz")

    result = await M.message_secret_role_autocomplete(ctx)

    assert result == []


@pytest.mark.asyncio
async def test_autocomplete_empty_messages_list():
    role_service = make_role_service([])
    bot = SimpleNamespace(services=SimpleNamespace(role=role_service))

    ctx = make_ctx(bot=bot, value="anything")

    result = await M.message_secret_role_autocomplete(ctx)

    assert result == []
