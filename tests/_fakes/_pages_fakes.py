# Fakes utilisés par les tests UI (pages/help, interactions, vues, boutons…)
# On suppose que tests/conftest.py a déjà installé un stub "discord" complet.

from __future__ import annotations

import discord  # type: ignore


# ------------------------------------------------------------
# Fakes Message / Attachment
# ------------------------------------------------------------
class FakeAttachment:
    def __init__(self, *, filename: str, url: str):
        self.filename = filename
        self.url = url


class FakeMessage:
    def __init__(self, attachments=None):
        self.attachments = attachments or []


# ------------------------------------------------------------
# Fakes Interaction / Response / Followup
# ------------------------------------------------------------
class FakeResponse:
    """
    Simule interaction.response :
    - is_done()
    - edit_message()
    - defer()
    - send_message()
    """

    def __init__(self):
        self._done = False
        self.edits: list[dict] = []
        self.deferred = False
        self.sent: list[dict] = []

        # Permet de simuler un cas où Discord refuse un second send_message()
        # (ex: discord.InteractionResponded)
        self.raise_on_send: type[BaseException] | None = None

    def is_done(self) -> bool:
        return self._done

    async def edit_message(self, *, embed=None, view=None):
        self._done = True
        self.edits.append({"embed": embed, "view": view})

    async def defer(self):
        self._done = True
        self.deferred = True

    async def send_message(self, content: str, *, ephemeral: bool = False):
        if self.raise_on_send is not None:
            raise self.raise_on_send
        self._done = True
        self.sent.append({"content": content, "ephemeral": ephemeral})


class FakeFollowup:
    def __init__(self):
        self.sent = []

    async def send(self, content=None, *args, **kwargs):
        # Support discord.py style: send("msg") ou send(content="msg")
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
            }
        )


class FakeUser:
    def __init__(self, user_id: int, *, guild_permissions=None):
        self.id = user_id
        self.guild_permissions = guild_permissions


class FakeInteraction:
    """
    Simule une Interaction discord :
    - .user
    - .message
    - .response
    - .followup
    - edit_original_response()
    """

    def __init__(self, *, user: FakeUser, message=None):
        self.user = user
        self.message = message
        self.response = FakeResponse()
        self.followup = FakeFollowup()

        self.original_edits: list[dict] = []

        # Permet de simuler un edit_original_response qui échoue
        # (ex: discord.NotFound / discord.HTTPException)
        self.raise_on_edit_original: type[BaseException] | None = None

    async def edit_original_response(self, *, embed=None, files=None, view=None):
        if self.raise_on_edit_original is not None:
            raise self.raise_on_edit_original
        self.original_edits.append({"embed": embed, "files": files, "view": view})


# ------------------------------------------------------------
# Fakes ApplicationContext / permissions
# ------------------------------------------------------------
class FakePerms:
    """
    Certains morceaux de code testent guild_permissions.value
    """
    def __init__(self, value: int):
        self.value = value


class FakeCtx:
    """
    Simule un ApplicationContext minimal :
    - .user
    - .followup
    - defer()
    """

    def __init__(self, *, user: FakeUser):
        self.user = user
        self.followup = FakeFollowup()
        self.deferred: list[dict] = []

    async def defer(self, *, ephemeral: bool = False):
        self.deferred.append({"ephemeral": ephemeral})


# ------------------------------------------------------------
# Helpers (facultatif) pour brancher les exceptions du stub discord
# ------------------------------------------------------------
def set_raise_on_second_response_send(interaction: FakeInteraction) -> None:
    """
    Cas courant : interaction.response.send_message lève InteractionResponded
    si on essaye de répondre 2 fois.
    """
    interaction.response.raise_on_send = discord.InteractionResponded  # type: ignore[attr-defined]


def set_raise_on_edit_original_not_found(interaction: FakeInteraction) -> None:
    interaction.raise_on_edit_original = discord.NotFound  # type: ignore[attr-defined]


def set_raise_on_edit_original_http(interaction: FakeInteraction) -> None:
    interaction.raise_on_edit_original = discord.HTTPException  # type: ignore[attr-defined]
