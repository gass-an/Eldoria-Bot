from __future__ import annotations

from datetime import UTC, datetime, time
from pathlib import Path
from types import SimpleNamespace

import pytest

# -----------------------------
# Fakes Discord-like
# -----------------------------

class FakeChannel:
    def __init__(self):
        self.sent = []
        self.fetch_map = {}  # message_id -> message
        self.raise_on_fetch = None

    async def send(self, content=None, *, file=None):
        self.sent.append({"content": content, "file": file})

    async def fetch_message(self, mid: int):
        if self.raise_on_fetch:
            raise self.raise_on_fetch
        return self.fetch_map.get(mid)


class FakeGuild:
    def __init__(self, channel: FakeChannel | None):
        self._channel = channel

    def get_channel(self, cid: int):
        return self._channel


class FakeFollowup:
    def __init__(self):
        self.sent = []

    async def send(self, *, content: str, ephemeral: bool = False, **kwargs):
        self.sent.append({"content": content, "ephemeral": ephemeral, **kwargs})


class FakeUser:
    def __init__(self, uid: int):
        self.id = uid


class FakeCtx:
    def __init__(self, uid: int):
        self.user = FakeUser(uid)
        self.followup = FakeFollowup()
        self.deferred = []

    async def defer(self, *, ephemeral: bool = False):
        self.deferred.append({"ephemeral": ephemeral})


class FakeAttachment:
    def __init__(self, filename="db.db"):
        self.filename = filename
        self.saved_to = []

    async def save(self, path):
        # Le code prod peut passer un `pathlib.Path`.
        self.saved_to.append(str(path))


class FakeMessage:
    def __init__(self, attachments):
        self.attachments = attachments


# -----------------------------
# Fake services (save/temp_voice)
# -----------------------------

class FakeSaveService:
    def __init__(self, db_path="./data/eldoria.db"):
        self._db_path = db_path
        self.backup_calls = []
        self.replace_calls = []
        self.init_db_calls = 0

    def get_db_path(self):
        return self._db_path

    def backup_to_file(self, dst: str):
        self.backup_calls.append(dst)

    def replace_db_file(self, tmp_new: str):
        self.replace_calls.append(tmp_new)

    def init_db(self):
        self.init_db_calls += 1


class FakeTempVoiceService:
    def __init__(self):
        self.list_calls = []
        self.remove_calls = []

    def list_active_all(self, guild_id: int):
        self.list_calls.append(guild_id)
        # parent_id, channel_id
        return [(1, 111), (1, 222)]

    def remove_active(self, guild_id: int, parent_id: int, channel_id: int):
        self.remove_calls.append((guild_id, parent_id, channel_id))


class FakeBot:
    def __init__(self, *, guild: FakeGuild | None, save: FakeSaveService, temp_voice: FakeTempVoiceService):
        self._guild = guild
        self.services = SimpleNamespace(save=save, temp_voice=temp_voice)
        self.guilds = []  # used by insert_db cleanup

    def get_guild(self, gid: int):
        return self._guild

    async def wait_until_ready(self):
        return None


class FakeBotGuild:
    """Guild objects inside bot.guilds for cleanup loop."""
    def __init__(self, gid: int, existing_channel_ids: set[int]):
        self.id = gid
        self._existing = existing_channel_ids

    def get_channel(self, cid: int):
        return object() if cid in self._existing else None


# -----------------------------
# Helpers: patch decorators + import module
# -----------------------------

def _import_module_with_patched_decorators(monkeypatch):
    import sys
    import types

    import discord  # type: ignore

    # --- slash_command decorator -> identity
    def slash_command(**kwargs):
        def deco(fn):
            return fn
        return deco

    # --- discord.option decorator -> identity
    def option(*args, **kwargs):
        def deco(fn):
            return fn
        return deco

    # --- tasks.loop -> FakeLoop wrapper
    class FakeLoop:
        def __init__(self, coro):
            self._coro = coro
            self.started = False
            self.canceled = False

        def start(self):
            self.started = True

        def cancel(self):
            self.canceled = True

        def before_loop(self, fn):
            return fn

        # ✅ IMPORTANT: binding à l'instance (descriptor protocol)
        def __get__(self, obj, objtype=None):
            if obj is None:
                return self

            async def bound(*a, **k):
                # ici on injecte l'instance du cog
                return await self._coro(obj, *a, **k)

            # on expose aussi start/cancel sur la version "bound"
            bound.start = self.start  # type: ignore[attr-defined]
            bound.cancel = self.cancel  # type: ignore[attr-defined]
            bound.before_loop = self.before_loop  # type: ignore[attr-defined]
            return bound


    def loop(**kwargs):
        def deco(coro):
            return FakeLoop(coro)
        return deco

    # ------------------------------------------------------------
    # Récupère les stubs installés par conftest
    # ------------------------------------------------------------
    commands_mod = sys.modules.get("discord.ext.commands")
    ext_mod = sys.modules.get("discord.ext")

    assert commands_mod is not None, "discord.ext.commands stub missing"
    assert ext_mod is not None, "discord.ext stub missing"

    # ✅ Ajoute Cog si absent (c’est ce qui casse chez toi)
    if not hasattr(commands_mod, "Cog"):
        class Cog:  # minimal base class
            pass
        monkeypatch.setattr(commands_mod, "Cog", Cog, raising=False)

    # Patch des decorators commands + discord.option
    monkeypatch.setattr(commands_mod, "slash_command", slash_command, raising=False)
    monkeypatch.setattr(discord, "option", option, raising=False)

    # ------------------------------------------------------------
    # Stub discord.ext.tasks.loop (+ rendre accessible via discord.ext.tasks)
    # car le module fait: from discord.ext import commands, tasks
    # ------------------------------------------------------------
    tasks_mod = sys.modules.get("discord.ext.tasks")
    if tasks_mod is None:
        tasks_mod = types.ModuleType("discord.ext.tasks")
        sys.modules["discord.ext.tasks"] = tasks_mod

    monkeypatch.setattr(tasks_mod, "loop", loop, raising=False)
    monkeypatch.setattr(ext_mod, "tasks", tasks_mod, raising=False)

    # ------------------------------------------------------------
    # IMPORTANT: si le module a déjà été importé avant un autre test,
    # il faut le "décharger" pour que nos patches soient pris.
    # ------------------------------------------------------------
    sys.modules.pop("eldoria.extensions.saves", None)

    from eldoria.extensions import saves as M
    return M



# -----------------------------
# Tests: _parse_auto_time
# -----------------------------

def test_parse_auto_time_valid(monkeypatch):
    M = _import_module_with_patched_decorators(monkeypatch)

    monkeypatch.setattr(M, "AUTO_SAVE_TZ", "UTC")
    cog = M.Saves.__new__(M.Saves)  # avoid __init__
    t = cog._parse_auto_time("08:30")
    assert isinstance(t, time)
    assert t.hour == 8 and t.minute == 30
    assert t.tzinfo is not None


def test_parse_auto_time_invalid_returns_none(monkeypatch):
    M = _import_module_with_patched_decorators(monkeypatch)

    monkeypatch.setattr(M, "AUTO_SAVE_TZ", "UTC")
    cog = M.Saves.__new__(M.Saves)
    assert cog._parse_auto_time("bad") is None
    assert cog._parse_auto_time("") is None
    assert cog._parse_auto_time(None) is None


def test_init_starts_auto_save_when_config_valid(monkeypatch):
    M = _import_module_with_patched_decorators(monkeypatch)

    monkeypatch.setattr(M, "MY_ID", 1)
    monkeypatch.setattr(M, "SAVE_GUILD_ID", 10)
    monkeypatch.setattr(M, "SAVE_CHANNEL_ID", 20)
    monkeypatch.setattr(M, "SAVE_ENABLED", True)
    monkeypatch.setattr(M, "AUTO_SAVE_ENABLED", True)
    monkeypatch.setattr(M, "AUTO_SAVE_TIME", "08:30")
    monkeypatch.setattr(M, "AUTO_SAVE_TZ", "UTC")

    bot = FakeBot(guild=None, save=FakeSaveService(), temp_voice=FakeTempVoiceService())
    cog = M.Saves(bot)

    # FakeLoop.start() doit avoir été appelé (FakeLoop est stocké sur la classe)
    assert cog.__class__.auto_save.started is True  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_send_db_backup_when_db_missing(monkeypatch, tmp_path):
    M = _import_module_with_patched_decorators(monkeypatch)

    monkeypatch.setattr(M, "SAVE_ENABLED", False)
    bot = FakeBot(guild=None, save=FakeSaveService(db_path=str(tmp_path / "eldoria.db")), temp_voice=FakeTempVoiceService())
    cog = M.Saves(bot)

    monkeypatch.setattr(M.os.path, "exists", lambda _p: False, raising=True)

    ch = FakeChannel()
    await cog._send_db_backup(channel=ch, reason="R")

    assert ch.sent[-1]["content"] == "Fichier DB introuvable !"


@pytest.mark.asyncio
async def test_send_db_backup_happy_path_and_remove_failure_ignored(monkeypatch, tmp_path):
    M = _import_module_with_patched_decorators(monkeypatch)

    monkeypatch.setattr(M, "SAVE_ENABLED", False)

    # travaille dans un dossier temporaire pour créer ./temp_eldoria_backup.db
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "eldoria.db"
    db_path.write_bytes(b"db")

    save = FakeSaveService(db_path=str(db_path))

    # backup_to_file crée le fichier temporaire attendu
    def backup_to_file(dst: str):
        Path(dst).write_bytes(b"backup")
        save.backup_calls.append(dst)

    save.backup_to_file = backup_to_file  # type: ignore[method-assign]

    bot = FakeBot(guild=None, save=save, temp_voice=FakeTempVoiceService())
    cog = M.Saves(bot)

    monkeypatch.setattr(M.os.path, "exists", lambda _p: True, raising=True)

    async def fake_to_thread(fn, *args):
        fn(*args)

    monkeypatch.setattr(M.asyncio, "to_thread", fake_to_thread, raising=True)

    # remove échoue, doit être ignoré
    monkeypatch.setattr(M.os, "remove", lambda _p: (_ for _ in ()).throw(OSError("no")), raising=True)

    ch = FakeChannel()
    await cog._send_db_backup(channel=ch, reason="R")

    assert ch.sent
    assert ch.sent[-1]["content"] == "R"
    assert ch.sent[-1]["file"] is not None


@pytest.mark.asyncio
async def test_auto_save_guards_disabled_noop(monkeypatch):
    M = _import_module_with_patched_decorators(monkeypatch)
    monkeypatch.setattr(M, "SAVE_ENABLED", False)
    monkeypatch.setattr(M, "AUTO_SAVE_ENABLED", True)

    bot = FakeBot(guild=None, save=FakeSaveService(), temp_voice=FakeTempVoiceService())
    cog = M.Saves(bot)

    await cog.auto_save()  # doit juste return


@pytest.mark.asyncio
async def test_auto_save_no_parsed_time_noop(monkeypatch):
    M = _import_module_with_patched_decorators(monkeypatch)

    monkeypatch.setattr(M, "MY_ID", 1)
    monkeypatch.setattr(M, "SAVE_GUILD_ID", 10)
    monkeypatch.setattr(M, "SAVE_CHANNEL_ID", 20)
    monkeypatch.setattr(M, "SAVE_ENABLED", True)
    monkeypatch.setattr(M, "AUTO_SAVE_ENABLED", True)
    monkeypatch.setattr(M, "AUTO_SAVE_TIME", None)

    bot = FakeBot(guild=None, save=FakeSaveService(), temp_voice=FakeTempVoiceService())
    cog = M.Saves(bot)

    # _auto_save_time n'existe pas (parse None)
    await cog.auto_save()


@pytest.mark.asyncio
async def test_auto_save_channel_none_noop(monkeypatch):
    M = _import_module_with_patched_decorators(monkeypatch)

    monkeypatch.setattr(M, "MY_ID", 1)
    monkeypatch.setattr(M, "SAVE_GUILD_ID", 10)
    monkeypatch.setattr(M, "SAVE_CHANNEL_ID", 20)
    monkeypatch.setattr(M, "SAVE_ENABLED", True)
    monkeypatch.setattr(M, "AUTO_SAVE_ENABLED", True)
    monkeypatch.setattr(M, "AUTO_SAVE_TIME", "08:30")
    monkeypatch.setattr(M, "AUTO_SAVE_TZ", "UTC")

    bot = FakeBot(guild=None, save=FakeSaveService(), temp_voice=FakeTempVoiceService())
    cog = M.Saves(bot)
    cog._auto_save_time = time(8, 30, tzinfo=UTC)

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 2, 13, 8, 30, 0, tzinfo=UTC)

    monkeypatch.setattr(M, "datetime", FakeDatetime)

    from eldoria.exceptions.general import ChannelRequired

    async def fake_get_channel(_bot, _cid):
        raise ChannelRequired()

    monkeypatch.setattr(M, "get_text_or_thread_channel", fake_get_channel, raising=True)

    with pytest.raises(ChannelRequired):
        await cog.auto_save()


@pytest.mark.asyncio
async def test_manual_save_channel_missing(monkeypatch):
    M = _import_module_with_patched_decorators(monkeypatch)

    monkeypatch.setattr(M, "MY_ID", 1)
    monkeypatch.setattr(M, "SAVE_GUILD_ID", 10)
    monkeypatch.setattr(M, "SAVE_CHANNEL_ID", 20)
    monkeypatch.setattr(M, "SAVE_ENABLED", True)

    bot = FakeBot(guild=None, save=FakeSaveService(), temp_voice=FakeTempVoiceService())
    cog = M.Saves(bot)

    from eldoria.exceptions.general import ChannelRequired

    async def fake_get_channel(_bot, _cid):
        raise ChannelRequired()

    monkeypatch.setattr(M, "get_text_or_thread_channel", fake_get_channel, raising=True)

    ctx = FakeCtx(uid=1)
    with pytest.raises(ChannelRequired):
        await cog.manual_save_command(ctx)


@pytest.mark.asyncio
async def test_manual_save_db_missing_sends_both_channel_and_followup(monkeypatch):
    M = _import_module_with_patched_decorators(monkeypatch)

    monkeypatch.setattr(M, "MY_ID", 1)
    monkeypatch.setattr(M, "SAVE_GUILD_ID", 10)
    monkeypatch.setattr(M, "SAVE_CHANNEL_ID", 20)
    monkeypatch.setattr(M, "SAVE_ENABLED", True)

    ch = FakeChannel()
    bot = FakeBot(guild=FakeGuild(channel=ch), save=FakeSaveService(), temp_voice=FakeTempVoiceService())
    cog = M.Saves(bot)

    async def fake_get_channel(_bot, _cid):
        return ch

    monkeypatch.setattr(M, "get_text_or_thread_channel", fake_get_channel, raising=True)
    monkeypatch.setattr(M.os.path, "exists", lambda _p: False, raising=True)

    ctx = FakeCtx(uid=1)
    await cog.manual_save_command(ctx)

    assert ch.sent[-1]["content"] == "Fichier DB introuvable !"
    assert ctx.followup.sent[-1]["content"] == "❌ DB introuvable."


def test_cog_unload_ignores_cancel_errors(monkeypatch):
    M = _import_module_with_patched_decorators(monkeypatch)

    monkeypatch.setattr(M, "SAVE_ENABLED", False)
    bot = FakeBot(guild=None, save=FakeSaveService(), temp_voice=FakeTempVoiceService())
    cog = M.Saves(bot)

    # force cancel to raise
    def cancel_raises():
        raise RuntimeError("no")

    cog.auto_save.cancel = cancel_raises  # type: ignore[attr-defined]
    cog.cog_unload()  # doit ignorer


@pytest.mark.asyncio
async def test_insert_db_fetch_message_error(monkeypatch):
    M = _import_module_with_patched_decorators(monkeypatch)

    monkeypatch.setattr(M, "MY_ID", 1)
    monkeypatch.setattr(M, "SAVE_GUILD_ID", 10)
    monkeypatch.setattr(M, "SAVE_CHANNEL_ID", 20)
    monkeypatch.setattr(M, "SAVE_ENABLED", True)

    ch = FakeChannel()
    ch.raise_on_fetch = RuntimeError("no")
    bot = FakeBot(guild=FakeGuild(channel=ch), save=FakeSaveService(), temp_voice=FakeTempVoiceService())
    cog = M.Saves(bot)

    async def fake_get_channel(_bot, _cid):
        return ch

    monkeypatch.setattr(M, "get_text_or_thread_channel", fake_get_channel, raising=True)

    ctx = FakeCtx(uid=1)
    with pytest.raises(RuntimeError):
        await cog.insert_db_command(ctx, message_id="123")


@pytest.mark.asyncio
async def test_insert_db_no_attachments(monkeypatch):
    M = _import_module_with_patched_decorators(monkeypatch)

    monkeypatch.setattr(M, "MY_ID", 1)
    monkeypatch.setattr(M, "SAVE_GUILD_ID", 10)
    monkeypatch.setattr(M, "SAVE_CHANNEL_ID", 20)
    monkeypatch.setattr(M, "SAVE_ENABLED", True)

    ch = FakeChannel()
    ch.fetch_map[123] = FakeMessage([])
    bot = FakeBot(guild=FakeGuild(channel=ch), save=FakeSaveService(), temp_voice=FakeTempVoiceService())
    cog = M.Saves(bot)

    async def fake_get_channel(_bot, _cid):
        return ch

    monkeypatch.setattr(M, "get_text_or_thread_channel", fake_get_channel, raising=True)

    ctx = FakeCtx(uid=1)
    await cog.insert_db_command(ctx, message_id="123")
    assert "Aucun fichier attaché" in ctx.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_insert_db_invalid_sqlite(monkeypatch):
    M = _import_module_with_patched_decorators(monkeypatch)

    monkeypatch.setattr(M, "MY_ID", 1)
    monkeypatch.setattr(M, "SAVE_GUILD_ID", 10)
    monkeypatch.setattr(M, "SAVE_CHANNEL_ID", 20)
    monkeypatch.setattr(M, "SAVE_ENABLED", True)

    ch = FakeChannel()
    att = FakeAttachment(filename="x.db")
    ch.fetch_map[123] = FakeMessage([att])
    bot = FakeBot(guild=FakeGuild(channel=ch), save=FakeSaveService(), temp_voice=FakeTempVoiceService())
    cog = M.Saves(bot)

    async def fake_get_channel(_bot, _cid):
        return ch

    monkeypatch.setattr(M, "get_text_or_thread_channel", fake_get_channel, raising=True)

    async def invalid(_attachment):
        return False

    monkeypatch.setattr(M, "is_valid_sqlite_db", invalid)

    ctx = FakeCtx(uid=1)
    await cog.insert_db_command(ctx, message_id="123")
    assert "n'est pas une base" in ctx.followup.sent[-1]["content"]


@pytest.mark.asyncio
async def test_insert_db_replace_failure_unlinks_tmp_and_reports(monkeypatch, tmp_path):
    M = _import_module_with_patched_decorators(monkeypatch)

    monkeypatch.setattr(M, "MY_ID", 1)
    monkeypatch.setattr(M, "SAVE_GUILD_ID", 10)
    monkeypatch.setattr(M, "SAVE_CHANNEL_ID", 20)
    monkeypatch.setattr(M, "SAVE_ENABLED", True)

    ch = FakeChannel()
    att = FakeAttachment(filename="eldoria.db")
    ch.fetch_map[123] = FakeMessage([att])

    save = FakeSaveService(db_path=str(tmp_path / "eldoria.db"))
    bot = FakeBot(guild=FakeGuild(channel=ch), save=save, temp_voice=FakeTempVoiceService())
    cog = M.Saves(bot)

    async def fake_get_channel(_bot, _cid):
        return ch

    monkeypatch.setattr(M, "get_text_or_thread_channel", fake_get_channel, raising=True)

    async def valid(_attachment):
        return True

    monkeypatch.setattr(M, "is_valid_sqlite_db", valid)

    # crée un fichier tmp pour que tmp_new.exists() soit True
    tmp_new_path = tmp_path / "temp_eldoria.db"
    tmp_new_path.write_bytes(b"x")

    async def save_to(path):
        # le code passe un Path, on écrase le contenu
        Path(path).write_bytes(b"x")
        att.saved_to.append(str(path))

    att.save = save_to  # type: ignore[method-assign]

    # replace_db_file échoue
    def replace_raises(_p):
        raise RuntimeError("boom")

    save.replace_db_file = replace_raises  # type: ignore[method-assign]

    async def fake_to_thread(fn, *args):
        fn(*args)

    monkeypatch.setattr(M.asyncio, "to_thread", fake_to_thread, raising=True)

    # force tmp_new.unlink to raise to cover inner except OSError (ligne 229-230)
    orig_unlink = Path.unlink

    def unlink_maybe(self, *a, **k):
        if str(self).endswith("temp_eldoria.db"):
            raise OSError("cannot")
        return orig_unlink(self, *a, **k)

    monkeypatch.setattr(Path, "unlink", unlink_maybe, raising=True)

    ctx = FakeCtx(uid=1)
    with pytest.raises(RuntimeError):
        await cog.insert_db_command(ctx, message_id="123")


def test_setup_adds_cog(monkeypatch):
    M = _import_module_with_patched_decorators(monkeypatch)

    monkeypatch.setattr(M, "SAVE_ENABLED", False)
    bot = FakeBot(guild=None, save=FakeSaveService(), temp_voice=FakeTempVoiceService())

    added = {}
    bot.add_cog = lambda cog: added.setdefault("cog", cog)  # type: ignore[attr-defined]

    M.setup(bot)
    assert isinstance(added.get("cog"), M.Saves)


# -----------------------------
# Tests: auto_save logic (happy path + guards)
# -----------------------------

@pytest.mark.asyncio
async def test_auto_save_calls_send_once_per_day(monkeypatch):
    M = _import_module_with_patched_decorators(monkeypatch)

    # config enabled
    monkeypatch.setattr(M, "MY_ID", 1)
    monkeypatch.setattr(M, "SAVE_GUILD_ID", 10)
    monkeypatch.setattr(M, "SAVE_CHANNEL_ID", 20)
    monkeypatch.setattr(M, "SAVE_ENABLED", True)
    monkeypatch.setattr(M, "AUTO_SAVE_TIME", "08:30")
    monkeypatch.setattr(M, "AUTO_SAVE_TZ", "UTC")
    monkeypatch.setattr(M, "AUTO_SAVE_ENABLED", True)

    ch = FakeChannel()
    guild = FakeGuild(channel=ch)
    bot = FakeBot(guild=guild, save=FakeSaveService(), temp_voice=FakeTempVoiceService())

    async def fake_get_channel(_bot, _cid):
        return ch
    monkeypatch.setattr(M, "get_text_or_thread_channel", fake_get_channel, raising=True)

    # empêcher le vrai start: on force __init__ mais on patch _send_db_backup
    calls = {"send": 0}
    async def fake_send_db_backup(self, *, channel, reason):
        calls["send"] += 1
        assert channel is ch
        assert "automatique" in reason.lower()

    monkeypatch.setattr(M.Saves, "_send_db_backup", fake_send_db_backup, raising=True)

    cog = M.Saves(bot)

    # set parsed time manually (sinon dépend de ZoneInfo/time)
    cog._auto_save_time = time(8, 30, tzinfo=UTC)

    # freeze "now" to matching minute
    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 2, 13, 8, 30, 5, tzinfo=UTC)
    monkeypatch.setattr(M, "datetime", FakeDatetime)

    await cog.auto_save()
    assert calls["send"] == 1
    assert getattr(cog, "_last_auto_save_date", None) == datetime(2026, 2, 13, tzinfo=UTC).date()

    # second call same date => no duplicate
    await cog.auto_save()
    assert calls["send"] == 1


@pytest.mark.asyncio
async def test_auto_save_returns_if_wrong_minute(monkeypatch):
    M = _import_module_with_patched_decorators(monkeypatch)

    monkeypatch.setattr(M, "MY_ID", 1)
    monkeypatch.setattr(M, "SAVE_GUILD_ID", 10)
    monkeypatch.setattr(M, "SAVE_CHANNEL_ID", 20)
    monkeypatch.setattr(M, "SAVE_ENABLED", True)
    monkeypatch.setattr(M, "AUTO_SAVE_TIME", "08:30")
    monkeypatch.setattr(M, "AUTO_SAVE_TZ", "UTC")
    monkeypatch.setattr(M, "AUTO_SAVE_ENABLED", True)

    bot = FakeBot(guild=FakeGuild(channel=FakeChannel()), save=FakeSaveService(), temp_voice=FakeTempVoiceService())

    async def fake_get_channel(_bot, _cid):
        return FakeChannel()
    monkeypatch.setattr(M, "get_text_or_thread_channel", fake_get_channel, raising=True)

    calls = {"send": 0}
    async def fake_send_db_backup(*, channel, reason):
        calls["send"] += 1
    monkeypatch.setattr(M.Saves, "_send_db_backup", fake_send_db_backup, raising=True)

    cog = M.Saves(bot)
    cog._auto_save_time = time(8, 30, tzinfo=UTC)

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 2, 13, 8, 29, 0, tzinfo=UTC)
    monkeypatch.setattr(M, "datetime", FakeDatetime)

    await cog.auto_save()
    assert calls["send"] == 0


# -----------------------------
# Tests: manual_save_command (guards)
# -----------------------------

@pytest.mark.asyncio
async def test_manual_save_not_configured(monkeypatch):
    M = _import_module_with_patched_decorators(monkeypatch)

    monkeypatch.setattr(M, "MY_ID", None)
    monkeypatch.setattr(M, "SAVE_GUILD_ID", 10)
    monkeypatch.setattr(M, "SAVE_CHANNEL_ID", 20)
    monkeypatch.setattr(M, "SAVE_ENABLED", False)


    bot = FakeBot(guild=None, save=FakeSaveService(), temp_voice=FakeTempVoiceService())
    cog = M.Saves(bot)

    ctx = FakeCtx(uid=1)
    await cog.manual_save_command(ctx)

    assert ctx.deferred == [{"ephemeral": True}]
    assert ctx.followup.sent[-1]["content"].startswith("Feature save non configurée")


@pytest.mark.asyncio
async def test_manual_save_wrong_user(monkeypatch):
    M = _import_module_with_patched_decorators(monkeypatch)

    monkeypatch.setattr(M, "MY_ID", 999)
    monkeypatch.setattr(M, "SAVE_GUILD_ID", 10)
    monkeypatch.setattr(M, "SAVE_CHANNEL_ID", 20)
    monkeypatch.setattr(M, "SAVE_ENABLED", True)

    bot = FakeBot(guild=None, save=FakeSaveService(), temp_voice=FakeTempVoiceService())
    cog = M.Saves(bot)

    ctx = FakeCtx(uid=1)
    await cog.manual_save_command(ctx)

    assert ctx.followup.sent[-1]["content"] == "Vous ne pouvez pas faire cela"


# -----------------------------
# Tests: insert_db_command (happy path)
# -----------------------------

@pytest.mark.asyncio
async def test_insert_db_success(monkeypatch):
    M = _import_module_with_patched_decorators(monkeypatch)

    monkeypatch.setattr(M, "MY_ID", 1)
    monkeypatch.setattr(M, "SAVE_GUILD_ID", 10)
    monkeypatch.setattr(M, "SAVE_CHANNEL_ID", 20)
    monkeypatch.setattr(M, "SAVE_ENABLED", True)

    ch = FakeChannel()
    att = FakeAttachment(filename="eldoria.db")
    ch.fetch_map[123] = FakeMessage([att])

    bot_guilds = [FakeBotGuild(1, existing_channel_ids={111})]  # 222 missing => should remove_active
    save = FakeSaveService(db_path="./data/eldoria.db")
    temp_voice = FakeTempVoiceService()

    bot = FakeBot(guild=FakeGuild(channel=ch), save=save, temp_voice=temp_voice)
    bot.guilds = bot_guilds

    cog = M.Saves(bot)

    async def fake_get_channel(_bot, _cid):
        return ch

    monkeypatch.setattr(M, "get_text_or_thread_channel", fake_get_channel, raising=True)

    # is_valid_sqlite_db -> True
    async def valid(_attachment):
        return True

    monkeypatch.setattr(M, "is_valid_sqlite_db", valid)

    # avoid filesystem
    monkeypatch.setattr(M.os.path, "dirname", lambda p: "./data")
    monkeypatch.setattr(M.os, "makedirs", lambda *a, **k: None)
    # os.path.join peut être appelé avec plus de 2 segments (y compris par
    # pytest lors du rendu des erreurs). On accepte donc *parts.
    monkeypatch.setattr(M.os.path, "join", lambda *parts: "/".join(parts))

    async def fake_to_thread(fn, *args):
        fn(*args)

    monkeypatch.setattr(M.asyncio, "to_thread", fake_to_thread)

    ctx = FakeCtx(uid=1)
    await cog.insert_db_command(ctx, message_id="123")

    # attachment saved (normalisation Windows/POSIX)
    assert [Path(p).as_posix() for p in att.saved_to] == ["data/temp_eldoria.db"]

    # replace called + init_db called (normalisation Windows/POSIX)
    assert [Path(str(p)).as_posix() for p in save.replace_calls] == ["data/temp_eldoria.db"]
    assert save.init_db_calls == 1

    # cleanup: channel 222 missing => remove_active called
    assert temp_voice.remove_calls == [(1, 1, 222)]

    assert ctx.followup.sent[-1]["content"].startswith("✅ Base de données remplacée")
