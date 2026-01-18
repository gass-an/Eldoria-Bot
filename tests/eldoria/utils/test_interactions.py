import sys
import types

import pytest


if "discord" not in sys.modules:
    sys.modules["discord"] = types.SimpleNamespace()


from eldoria.utils.interactions import reply_ephemeral  # noqa: E402


class FakeResponse:
    def __init__(self, *, done: bool):
        self._done = done
        self.sent = []

    def is_done(self):
        return self._done

    async def send_message(self, content: str, *, ephemeral: bool = False):
        self.sent.append(("response.send_message", content, ephemeral))


class FakeFollowup:
    def __init__(self):
        self.sent = []

    async def send(self, content: str, *, ephemeral: bool = False):
        self.sent.append(("followup.send", content, ephemeral))


class FakeInteraction:
    def __init__(self, *, response_done: bool):
        self.response = FakeResponse(done=response_done)
        self.followup = FakeFollowup()


@pytest.mark.asyncio
async def test_reply_ephemeral_uses_response_send_message_when_not_done():
    inter = FakeInteraction(response_done=False)

    await reply_ephemeral(inter, "hello")

    assert inter.response.sent == [("response.send_message", "hello", True)]
    assert inter.followup.sent == []


@pytest.mark.asyncio
async def test_reply_ephemeral_uses_followup_send_when_done():
    inter = FakeInteraction(response_done=True)

    await reply_ephemeral(inter, "hello")

    assert inter.response.sent == []
    assert inter.followup.sent == [("followup.send", "hello", True)]
