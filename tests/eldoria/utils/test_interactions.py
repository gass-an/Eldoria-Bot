import pytest

from eldoria.utils.interactions import reply_ephemeral
from tests._fakes import FakeInteraction, FakeUser


@pytest.mark.asyncio
async def test_reply_ephemeral_uses_response_send_message_when_not_done():
    inter = FakeInteraction(user=FakeUser(1))

    await reply_ephemeral(inter, "hello")  # type: ignore[arg-type]

    assert inter.response.sent == [{"content": "hello", "ephemeral": True}]
    assert inter.followup.sent == []


@pytest.mark.asyncio
async def test_reply_ephemeral_uses_followup_send_when_done():
    inter = FakeInteraction(user=FakeUser(1))
    inter.response._done = True

    await reply_ephemeral(inter, "hello")  # type: ignore[arg-type]

    assert inter.response.sent == []
    assert inter.followup.sent and inter.followup.sent[-1]["content"] == "hello"
    assert inter.followup.sent[-1]["ephemeral"] is True
