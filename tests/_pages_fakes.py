import sys
import types


# Ensure base "discord" module exists (your conftest already does, but keep it safe)
if "discord" not in sys.modules:
    sys.modules["discord"] = types.SimpleNamespace()

import discord  # type: ignore


# -------------------------
# Types used in annotations/imports
# -------------------------
if not hasattr(discord, "ApplicationContext"):
    discord.ApplicationContext = object  # type: ignore[attr-defined]
if not hasattr(discord, "Interaction"):
    discord.Interaction = object  # type: ignore[attr-defined]


# -------------------------
# Exceptions
# -------------------------
class InteractionResponded(Exception):
    pass


class HTTPException(Exception):
    pass


class NotFound(Exception):
    pass


if not hasattr(discord, "InteractionResponded"):
    discord.InteractionResponded = InteractionResponded  # type: ignore[attr-defined]
if not hasattr(discord, "HTTPException"):
    discord.HTTPException = HTTPException  # type: ignore[attr-defined]
if not hasattr(discord, "NotFound"):
    discord.NotFound = NotFound  # type: ignore[attr-defined]


# -------------------------
# ButtonStyle stub
# -------------------------
class _ButtonStyle:
    secondary = "secondary"
    primary = "primary"
    success = "success"
    danger = "danger"


if not hasattr(discord, "ButtonStyle"):
    discord.ButtonStyle = _ButtonStyle  # type: ignore[attr-defined]


# -------------------------
# discord.ui module stub (IMPORTANT: must be a module for "from discord.ui import X")
# -------------------------
ui_module = sys.modules.get("discord.ui")
if ui_module is None:
    ui_module = types.ModuleType("discord.ui")
    sys.modules["discord.ui"] = ui_module

# Expose as attribute too
discord.ui = ui_module  # type: ignore[attr-defined]


class FakeButton:
    def __init__(self, *, label: str = "", style=None, disabled: bool = False):
        self.label = label
        self.style = style
        self.disabled = disabled
        self.callback = None  # assigned later


class FakeView:
    def __init__(self, *, timeout=None):
        self.timeout = timeout
        self.children: list[object] = []

    def add_item(self, item):
        self.children.append(item)


# Install into discord.ui module
if not hasattr(ui_module, "View"):
    ui_module.View = FakeView  # type: ignore[attr-defined]
if not hasattr(ui_module, "Button"):
    ui_module.Button = FakeButton  # type: ignore[attr-defined]


# -------------------------
# Fake message/attachments
# -------------------------
class FakeAttachment:
    def __init__(self, *, filename: str, url: str):
        self.filename = filename
        self.url = url


class FakeMessage:
    def __init__(self, attachments=None):
        self.attachments = attachments or []


# -------------------------
# Fake interaction / response / followup
# -------------------------
class FakeResponse:
    def __init__(self):
        self._done = False
        self.edits: list[dict] = []
        self.deferred = False
        self.sent: list[dict] = []
        self.raise_on_send = None  # set to discord.InteractionResponded if needed

    def is_done(self):
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
        self.sent: list[dict] = []

    async def send(self, content: str | None = None, *, ephemeral: bool = False, embed=None, files=None, view=None):
        self.sent.append(
            {
                "content": content,
                "ephemeral": ephemeral,
                "embed": embed,
                "files": files,
                "view": view,
            }
        )



class FakeUser:
    def __init__(self, user_id: int, *, guild_permissions=None):
        self.id = user_id
        self.guild_permissions = guild_permissions


class FakeInteraction:
    def __init__(self, *, user: FakeUser, message=None):
        self.user = user
        self.message = message
        self.response = FakeResponse()
        self.followup = FakeFollowup()
        self.original_edits: list[dict] = []
        self.raise_on_edit_original = None  # set to discord.NotFound / discord.HTTPException if needed

    async def edit_original_response(self, *, embed=None, files=None, view=None):
        if self.raise_on_edit_original is not None:
            raise self.raise_on_edit_original
        self.original_edits.append({"embed": embed, "files": files, "view": view})


# -------------------------
# Fake ApplicationContext + perms
# -------------------------
class FakePerms:
    def __init__(self, value: int):
        self.value = value


class FakeCtx:
    def __init__(self, *, user: FakeUser):
        self.user = user
        self.followup = FakeFollowup()
        self.deferred: list[dict] = []

    async def defer(self, *, ephemeral: bool = False):
        self.deferred.append({"ephemeral": ephemeral})
