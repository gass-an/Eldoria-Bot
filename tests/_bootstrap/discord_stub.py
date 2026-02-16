from __future__ import annotations

import sys
from types import ModuleType


def install_discord_stub() -> None:
    # wipe toute trace d'un vrai discord déjà importé
    for name in list(sys.modules.keys()):
        if name == "discord" or name.startswith("discord."):
            sys.modules.pop(name, None)

    discord_mod = ModuleType("discord")

    # ---- discord.abc ----
    abc_mod = ModuleType("discord.abc")

    class Messageable:
        pass

    class User:
        pass

    # Base de channel de guild pour les checks isinstance(..., discord.abc.GuildChannel)
    class GuildChannel:
        id: int

    abc_mod.Messageable = Messageable
    abc_mod.User = User
    abc_mod.GuildChannel = GuildChannel

    # ---- discord.utils ----
    utils_mod = ModuleType("discord.utils")

    def _utils_get(iterable, **attrs):
        for item in iterable:
            ok = True
            for k, v in attrs.items():
                if getattr(item, k, None) != v:
                    ok = False
                    break
            if ok:
                return item
        return None

    utils_mod.get = _utils_get

    # ---- Exceptions ----
    class Forbidden(Exception):
        pass

    class NotFound(Exception):
        pass

    class HTTPException(Exception):
        pass

    class InteractionResponded(Exception):
        pass

    # ---- Core ----
    class Client:
        def get_guild(self, guild_id: int):
            return None

        def get_channel(self, channel_id: int):
            return None

        async def fetch_channel(self, channel_id: int):
            return None

    class Guild:
        id: int = 0
        text_channels: list = []

        def get_member(self, member_id: int):
            return None

        async def fetch_member(self, member_id: int):
            raise NotFound()

    class Member:
        id: int = 0
        bot: bool = False

    class Message:
        id: int = 0
        content: str = ""

    class Role:
        id: int = 0
        name: str = ""

    # IMPORTANT: classes bases stables pour isinstance()
    class Interaction:
        guild = None
        user = None

    class ApplicationContext:
        pass

    class Attachment:
        def __init__(self, *, filename: str = ""):
            self.filename = filename

        async def save(self, path: str):
            return None

    # ---- Channels ----
    class TextChannel(Messageable, GuildChannel):
        id: int = 0

        async def fetch_message(self, message_id: int):
            raise NotFound()

    class Thread(Messageable, GuildChannel):
        id: int = 0

    class DMChannel(Messageable):
        id: int = 0

    # Compat: discord.GuildChannel existe aussi mais les checks utilisent surtout discord.abc.GuildChannel
    class GuildChannel(GuildChannel):
        pass

    # ---- UI ----
    class ButtonStyle:
        secondary = "secondary"
        primary = "primary"
        success = "success"
        danger = "danger"

    ui_mod = ModuleType("discord.ui")

    class View:
        def __init__(self, *args, **kwargs):
            self.children = []
            self.timeout = kwargs.get("timeout", None)

        def add_item(self, item):
            # discord.py assigne `item.view` à la view courante.
            setattr(item, "view", self)
            self.children.append(item)

        async def on_timeout(self):  # pragma: no cover
            return None

    class Button:
        def __init__(self, *, label: str = "", style=None, disabled: bool = False, custom_id: str | None = None):
            self.label = label
            self.style = style
            self.disabled = disabled
            self.custom_id = custom_id
            # Ne pas écraser une méthode `callback` définie dans les sous-classes.

    def button(*args, **kwargs):  # pragma: no cover
        def decorator(func):
            return func

        return decorator

    ui_mod.View = View
    ui_mod.Button = Button
    ui_mod.button = button

    # ---- discord.ext.commands ----
    ext_mod = ModuleType("discord.ext")
    commands_mod = ModuleType("discord.ext.commands")

    class Cog:
        @classmethod
        def listener(cls, *_a, **_k):
            def deco(fn):
                return fn

            return deco

    class Bot(Client):
        pass

    class AutoShardedBot(Client):  # pragma: no cover
        pass

    def when_mentioned(*args, **kwargs):  # pragma: no cover
        return []

    class Intents:  # pragma: no cover
        pass

    class AutocompleteContext:
        def __init__(self):
            self.value = None
            self.options = {}
            self.interaction = None

    class AllowedMentions:
        def __init__(self, **kwargs):
            self.kw = dict(kwargs)
            self.users = self.kw.get("users")
            self.roles = self.kw.get("roles")
            self.everyone = self.kw.get("everyone")
            self.replied_user = self.kw.get("replied_user")

        @classmethod
        def none(cls):
            return cls(users=False, roles=False, everyone=False, replied_user=False)

        def __eq__(self, other):
            return isinstance(other, AllowedMentions) and self.kw == other.kw

    commands_mod.Cog = Cog
    commands_mod.Bot = Bot
    commands_mod.AutoShardedBot = AutoShardedBot
    commands_mod.when_mentioned = when_mentioned

    # ---- discord.ext.tasks ----
    tasks_mod = ModuleType("discord.ext.tasks")

    class _FakeLoop:
        def __init__(self, coro):
            self.coro = coro
            self.started = False
            self.cancelled = False
            self._before_loop = None

        def start(self):
            self.started = True

        def cancel(self):
            self.cancelled = True

        def before_loop(self, fn):
            self._before_loop = fn
            return fn

        def __get__(self, obj, objtype=None):
            loop = self

            class _Bound:
                @property
                def started(self):
                    return loop.started

                @property
                def cancelled(self):
                    return loop.cancelled

                def start(self):
                    loop.start()

                def cancel(self):
                    loop.cancel()

                def before_loop(self, fn):
                    return loop.before_loop(fn)

                async def __call__(self, *a, **k):
                    return await loop.coro(obj, *a, **k)

            return _Bound()

    def loop(*_a, **_k):
        def deco(fn):
            return _FakeLoop(fn)

        return deco

    tasks_mod.loop = loop

    # ---- Placeholders Embed/File/Color ----
    class Color(int):
        def __new__(cls, value=0):
            return int.__new__(cls, value)

    class Embed:
        def __init__(self, **kwargs):
            self.kwargs = dict(kwargs)
            self.fields = []
            self.footer = {}
            self.thumbnail = {}
            self.image = {}

        def add_field(self, **kw):
            self.fields.append(dict(kw))
            return None

        def set_footer(self, **kw):
            self.footer = dict(kw)
            return None

        def set_thumbnail(self, **kw):
            self.thumbnail = dict(kw)
            return None

        def set_image(self, **kw):
            self.image = dict(kw)
            return None

    class File:
        def __init__(self, fp=None, filename: str | None = None):
            self.fp = fp
            self.filename = filename

    # ---- Injection sys.modules ----
    discord_mod.abc = abc_mod
    discord_mod.utils = utils_mod

    discord_mod.Forbidden = Forbidden
    discord_mod.NotFound = NotFound
    discord_mod.HTTPException = HTTPException
    discord_mod.InteractionResponded = InteractionResponded

    discord_mod.Client = Client
    discord_mod.Guild = Guild
    discord_mod.Member = Member
    discord_mod.User = User
    discord_mod.Message = Message
    discord_mod.Role = Role
    discord_mod.Interaction = Interaction
    discord_mod.ApplicationContext = ApplicationContext
    discord_mod.Attachment = Attachment
    discord_mod.AutocompleteContext = AutocompleteContext
    discord_mod.AllowedMentions = AllowedMentions

    discord_mod.TextChannel = TextChannel
    discord_mod.Thread = Thread
    discord_mod.DMChannel = DMChannel
    discord_mod.abc.GuildChannel = GuildChannel

    discord_mod.ButtonStyle = ButtonStyle
    discord_mod.ui = ui_mod
    discord_mod.ext = ext_mod
    discord_mod.Intents = Intents

    discord_mod.Color = Color
    discord_mod.Embed = Embed
    discord_mod.File = File

    ext_mod.commands = commands_mod
    ext_mod.tasks = tasks_mod

    sys.modules["discord"] = discord_mod
    sys.modules["discord.abc"] = abc_mod
    sys.modules["discord.utils"] = utils_mod
    sys.modules["discord.ui"] = ui_mod
    sys.modules["discord.ext"] = ext_mod
    sys.modules["discord.ext.commands"] = commands_mod
    sys.modules["discord.ext.tasks"] = tasks_mod

    # Remplace Color/Embed/File par vos fakes (OK, ça ne casse pas isinstance Interaction)
    from tests._fakes import _embed_fakes

    discord_mod.File = _embed_fakes.FakeFile
    discord_mod.Embed = _embed_fakes.FakeEmbed
    discord_mod.Color = _embed_fakes.FakeColor


