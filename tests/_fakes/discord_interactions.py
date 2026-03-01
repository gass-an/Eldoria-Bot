from __future__ import annotations

"""Fakes pour Interaction/Response/Followup Discord."""

from typing import Any

import discord  # type: ignore

from tests._fakes.discord_entities import FakeUser


class FakeResponse:
    """Simule `interaction.response`.

    Supporte:
    - is_done()
    - edit_message()
    - defer()
    - send_message()
    - send_modal()
    """

    def __init__(self):
        self._done = False
        self.edits: list[dict[str, Any]] = []
        self.deferred = False
        self.sent: list[dict[str, Any]] = []
        self.modals: list[object] = []

        # Permet de simuler une exception au 2e send_message()
        self.raise_on_send: type[BaseException] | None = None

    def is_done(self) -> bool:
        return self._done

    async def edit_message(self, **kwargs):
        self._done = True
        self.edits.append(dict(kwargs))

    async def defer(self):
        self._done = True
        self.deferred = True

    async def send_message(self, content: str, *, ephemeral: bool = False):
        if self.raise_on_send is not None:
            raise self.raise_on_send
        self._done = True
        self.sent.append({"content": content, "ephemeral": ephemeral})

    async def send_modal(self, modal):
        self._done = True
        self.modals.append(modal)


class FakeFollowup:
    def __init__(self):
        self.sent: list[dict[str, Any]] = []

    async def send(self, content=None, *args, **kwargs):
        # Support discord.py: send("msg") ou send(content="msg")
        if content is None:
            content = kwargs.get("content")
        if content is None and args:
            content = args[0]

        self.sent.append(
            {
                "content": content,
                "ephemeral": kwargs.get("ephemeral"),
                "embed": kwargs.get("embed"),
                "embeds": kwargs.get("embeds"),
                "files": kwargs.get("files"),
                "view": kwargs.get("view"),
                **{k: v for k, v in kwargs.items() if k not in {"content", "ephemeral", "embed", "embeds", "files", "view"}},
            }
        )


class FakeInteraction:
    """Simule `discord.Interaction` minimal."""

    def __init__(self, *, user: FakeUser, message=None, data: dict | None = None):
        self.user = user
        self.message = message
        self.data = data or {}
        self.response = FakeResponse()
        self.followup = FakeFollowup()

        self.original_edits: list[dict[str, Any]] = []
        self.raise_on_edit_original: type[BaseException] | None = None

    async def edit_original_response(
        self,
        *,
        # API "discord.py" (souvent utilisé)
        embed=None,
        embeds=None,
        files=None,
        attachments=None,
        view=None,
        # Compat: certaines vues appellent `edit_original_response(content=...)`.
        content=None,
        **_ignored,
    ):
        if self.raise_on_edit_original is not None:
            raise self.raise_on_edit_original
        # On capture tout ce que le code UI peut envoyer afin d'éviter des
        # "CompatInteraction" ad-hoc dans les tests.
        self.original_edits.append(
            {
                "content": content,
                "embed": embed,
                "embeds": embeds,
                "files": files,
                "attachments": attachments,
                "view": view,
            }
        )


class FakePerms:
    """Permissions minimalistes: certains bouts de code lisent `.value`."""

    def __init__(self, value: int):
        self.value = value


def set_raise_on_second_response_send(interaction: FakeInteraction) -> None:
    interaction.response.raise_on_send = discord.InteractionResponded  # type: ignore[attr-defined]


def set_raise_on_edit_original_not_found(interaction: FakeInteraction) -> None:
    interaction.raise_on_edit_original = discord.NotFound  # type: ignore[attr-defined]


def set_raise_on_edit_original_http(interaction: FakeInteraction) -> None:
    interaction.raise_on_edit_original = discord.HTTPException  # type: ignore[attr-defined]
