import sys
from types import ModuleType

import pytest


def _ensure_commands_and_tasks_stubs() -> None:
    """
    Ton tests/conftest.py installe déjà un stub "discord" minimal,
    mais il ne fournit pas forcément:
      - commands.Cog / listener / slash_command / option
      - commands.* exceptions utilisées par d'autres modules
      - discord.ext.tasks.loop
    Ici on complète ces stubs de façon safe (sans toucher au conftest).
    """
    import discord  # type: ignore

    # ---- commands
    commands_mod = sys.modules.get("discord.ext.commands")
    if commands_mod is None:
        commands_mod = ModuleType("discord.ext.commands")
        sys.modules["discord.ext.commands"] = commands_mod

    # Cog + décorateurs
    if not hasattr(commands_mod, "Cog"):
        class Cog:
            @classmethod
            def listener(cls, *_a, **_k):
                def deco(fn):
                    return fn
                return deco
        commands_mod.Cog = Cog

    if not hasattr(commands_mod, "slash_command"):
        def slash_command(*_a, **_k):
            def deco(fn):
                return fn
            return deco
        commands_mod.slash_command = slash_command

    # Exceptions Discord.py / py-cord usuelles
    # (elles sont testées dans Core; ici on les laisse si déjà présentes)
    for _name in (
        "MissingPermissions",
        "BotMissingPermissions",
        "MissingRole",
        "MissingAnyRole",
        "CheckFailure",
    ):
        if not hasattr(commands_mod, _name):
            setattr(commands_mod, _name, type(_name, (Exception,), {}))

    # ---- discord.option (py-cord)
    if not hasattr(discord, "option"):
        def option(*_a, **_k):
            def deco(fn):
                return fn
            return deco
        discord.option = option  # type: ignore[attr-defined]

    # ---- tasks.loop
    if "discord.ext.tasks" not in sys.modules:
        tasks_mod = ModuleType("discord.ext.tasks")
        sys.modules["discord.ext.tasks"] = tasks_mod
    else:
        tasks_mod = sys.modules["discord.ext.tasks"]

    if not hasattr(tasks_mod, "loop"):
        class _FakeLoop:
            def __init__(self, coro):
                self.coro = coro
                self._started = False

            def start(self):
                self._started = True

            def before_loop(self, coro):
                self._before_loop = coro
                return coro

            def __get__(self, instance, owner):
                # Si accès via la classe: Duels.maintenance_cleanup
                if instance is None:
                    return self

                # Retourne un objet appelable qui appelle la coro avec self bindé
                loop = self

                class _Bound:
                    coro = loop.coro

                    @property
                    def started(self):
                        return loop._started

                    async def __call__(self, *a, **k):
                        return await loop.coro(instance, *a, **k)

                    def start(self):
                        return loop.start()

                    def before_loop(self, coro):
                        return loop.before_loop(coro)

                return _Bound()

            async def __call__(self, *a, **k):
                # fallback si on l'appelle "non bindé"
                return await self.coro(*a, **k)

        def loop(*_a, **_k):
            def deco(fn):
                return _FakeLoop(fn)
            return deco

        tasks_mod.loop = loop  # type: ignore[attr-defined]


_ensure_commands_and_tasks_stubs()

# Import du module après les stubs
import eldoria.extensions.duels as duels_mod
from eldoria.extensions.duels import Duels, require_guild_ctx, setup


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
class _FakeFollowup:
    def __init__(self):
        self.sent = []

    async def send(self, content=None, *, ephemeral=False, embed=None, files=None, view=None):
        self.sent.append(
            {"content": content, "ephemeral": ephemeral, "embed": embed, "files": files, "view": view}
        )


class _FakeCtx:
    def __init__(self, *, guild, channel, user):
        self.guild = guild
        self.channel = channel
        self.user = user
        self.followup = _FakeFollowup()
        self.deferred = []
        self.responded = []

    async def defer(self, *, ephemeral=False):
        self.deferred.append({"ephemeral": ephemeral})

    async def respond(self, content, *, ephemeral=False):
        self.responded.append({"content": content, "ephemeral": ephemeral})


class _FakeGuild:
    def __init__(self, gid=123):
        self.id = gid


import discord  # type: ignore


class _FakeChannel(discord.abc.GuildChannel):  # type: ignore[attr-defined]
    def __init__(self, cid=999):
        self.id = cid


class _FakeMember:
    def __init__(self, mid=42, *, bot=False):
        self.id = mid
        self.bot = bot


class _FakeBot:
    def __init__(self, *, duel_service, xp_service):
        class _Services:
            def __init__(self, duel, xp):
                self.duel = duel
                self.xp = xp

        self.services = _Services(duel_service, xp_service)
        self._waited = 0
        self._guilds = {}

    def get_guild(self, guild_id: int):
        return self._guilds.get(guild_id)

    async def wait_until_ready(self):
        self._waited += 1


class _FakeDuelService:
    def __init__(self):
        self.cleanup_calls = []
        self.cancel_calls = 0
        self.new_duel_calls = []

        # programmable returns
        self._cancel_return = []
        self._new_duel_side_effect = None

    def cleanup_old_duels(self, ts):
        self.cleanup_calls.append(ts)

    def cancel_expired_duels(self):
        self.cancel_calls += 1
        return list(self._cancel_return)

    def new_duel(self, *, guild_id, channel_id, player_a_id, player_b_id):
        self.new_duel_calls.append((guild_id, channel_id, player_a_id, player_b_id))
        if self._new_duel_side_effect is not None:
            raise self._new_duel_side_effect
        # snapshot minimal
        return {"duel": {"expires_at": 111, "id": 777}}


class _FakeXpService:
    def __init__(self):
        self._enabled = True
        self.sync_calls = []

    def is_enabled(self, guild_id: int) -> bool:
        return self._enabled

    async def sync_xp_roles_for_users(self, guild, user_ids):
        self.sync_calls.append((guild, list(user_ids)))


# ---------------------------------------------------------------------------
# Tests require_guild_ctx
# ---------------------------------------------------------------------------
def test_require_guild_ctx_ok():
    guild = _FakeGuild()
    channel = _FakeChannel()
    ctx = _FakeCtx(guild=guild, channel=channel, user=_FakeMember(1))
    g, c = require_guild_ctx(ctx)
    assert g is guild
    assert c is channel


def test_require_guild_ctx_raises_outside_guild():
    ctx = _FakeCtx(guild=None, channel=None, user=_FakeMember(1))
    with pytest.raises(RuntimeError):
        require_guild_ctx(ctx)


# ---------------------------------------------------------------------------
# Tests __init__ loops started
# ---------------------------------------------------------------------------
def test_duels_init_starts_loops(monkeypatch):
    duel = _FakeDuelService()
    xp = _FakeXpService()
    bot = _FakeBot(duel_service=duel, xp_service=xp)

    d = Duels(bot)

    assert d.clear_expired_duels_loop.started is True
    assert d.maintenance_cleanup.started is True
    assert d.duel is duel
    assert d.xp is xp


# ---------------------------------------------------------------------------
# Tests loops
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_maintenance_cleanup_calls_service(monkeypatch):
    duel = _FakeDuelService()
    xp = _FakeXpService()
    bot = _FakeBot(duel_service=duel, xp_service=xp)

    d = Duels(bot)

    monkeypatch.setattr(duels_mod, "now_ts", lambda: 9999)
    await d.maintenance_cleanup()


    assert duel.cleanup_calls == [9999]


@pytest.mark.asyncio
async def test_before_loops_wait_ready(monkeypatch):
    duel = _FakeDuelService()
    xp = _FakeXpService()
    bot = _FakeBot(duel_service=duel, xp_service=xp)
    d = Duels(bot)

    await d.before_maintenance_cleanup()
    await d.before_clear_expired_duels_loop()

    assert bot._waited == 2


@pytest.mark.asyncio
async def test_clear_expired_duels_applies_ui_and_syncs_roles(monkeypatch):
    duel = _FakeDuelService()
    xp = _FakeXpService()
    bot = _FakeBot(duel_service=duel, xp_service=xp)

    guild = _FakeGuild(123)
    bot._guilds[123] = guild

    duel._cancel_return = [
        {"guild_id": 123, "xp_changed": True, "sync_roles_user_ids": [1, 2], "message_id": 10, "channel_id": 20, "player_a_id": 1, "player_b_id": 2},
        {"guild_id": 123, "xp_changed": False, "message_id": 11, "channel_id": 21, "player_a_id": 1, "player_b_id": 2},
    ]

    d = Duels(bot)

    applied = []
    async def fake_apply(self, info):
        applied.append(info)

    monkeypatch.setattr(Duels, "_apply_expired_ui", fake_apply, raising=True)

    await d.clear_expired_duels_loop()  # type: ignore[operator]

    assert duel.cancel_calls == 1
    assert len(applied) == 2
    assert xp.sync_calls == [(guild, [1, 2])]


@pytest.mark.asyncio
async def test_clear_expired_duels_ignores_apply_ui_errors(monkeypatch):
    duel = _FakeDuelService()
    xp = _FakeXpService()
    bot = _FakeBot(duel_service=duel, xp_service=xp)

    guild = _FakeGuild(123)
    bot._guilds[123] = guild

    duel._cancel_return = [
        {"guild_id": 123, "xp_changed": True, "sync_roles_user_ids": [1], "message_id": 10, "channel_id": 20, "player_a_id": 1, "player_b_id": 2},
    ]

    d = Duels(bot)

    async def boom(_info):
        raise Exception("nope")

    monkeypatch.setattr(Duels, "_apply_expired_ui", boom, raising=True)

    await d.clear_expired_duels_loop()  # type: ignore[operator]

    # apply a planté => loop continue, mais pas de sync car on skip après exception
    assert xp.sync_calls == []


@pytest.mark.asyncio
async def test_clear_expired_duels_skips_if_guild_missing(monkeypatch):
    duel = _FakeDuelService()
    xp = _FakeXpService()
    bot = _FakeBot(duel_service=duel, xp_service=xp)

    duel._cancel_return = [
        {"guild_id": 999, "xp_changed": True, "sync_roles_user_ids": [1], "message_id": 10, "channel_id": 20, "player_a_id": 1, "player_b_id": 2},
    ]

    d = Duels(bot)

    async def ok(_info):
        return None

    monkeypatch.setattr(Duels, "_apply_expired_ui", ok, raising=True)

    await d.clear_expired_duels_loop()  # type: ignore[operator]

    assert xp.sync_calls == []


# ---------------------------------------------------------------------------
# Tests _apply_expired_ui
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_apply_expired_ui_happy_path(monkeypatch):
    duel = _FakeDuelService()
    xp = _FakeXpService()
    bot = _FakeBot(duel_service=duel, xp_service=xp)
    guild = _FakeGuild(123)
    bot._guilds[123] = guild

    class _FakeMsg:
        def __init__(self):
            self.edits = []
        async def edit(self, *, content="", embed=None, view=None):
            self.edits.append({"content": content, "embed": embed, "view": view})

    class _FakeChan:
        def __init__(self):
            self.fetched = []
            self.msg = _FakeMsg()
        async def fetch_message(self, mid):
            self.fetched.append(mid)
            return self.msg

    fake_channel = _FakeChan()

    async def fake_get_member(g, mid):
        assert g is guild
        return _FakeMember(mid)

    async def fake_get_chan(*, bot, channel_id):
        assert bot is bot  # noqa: B015
        assert channel_id == 20
        return fake_channel

    async def fake_build_embed(**kwargs):
        return ("EMBED", ["FILES"])

    monkeypatch.setattr(duels_mod, "get_member_by_id_or_raise", fake_get_member)
    monkeypatch.setattr(duels_mod, "get_text_or_thread_channel", fake_get_chan)
    monkeypatch.setattr(duels_mod, "build_expired_duels_embed", fake_build_embed)

    d = Duels(bot)
    info = {
        "guild_id": 123,
        "channel_id": 20,
        "message_id": 10,
        "player_a_id": 1,
        "player_b_id": 2,
        "previous_status": "PENDING",
        "stake_xp": 5,
        "game_type": "coinflip",
    }

    await d._apply_expired_ui(info)

    assert fake_channel.fetched == [10]
    assert fake_channel.msg.edits == [{"content": "", "embed": "EMBED", "view": None}]


@pytest.mark.asyncio
async def test_apply_expired_ui_returns_if_missing_ids(monkeypatch):
    duel = _FakeDuelService()
    xp = _FakeXpService()
    bot = _FakeBot(duel_service=duel, xp_service=xp)
    d = Duels(bot)

    await d._apply_expired_ui({"guild_id": 1})  # no channel/message
    # no exception => ok


@pytest.mark.asyncio
async def test_apply_expired_ui_returns_if_guild_missing(monkeypatch):
    duel = _FakeDuelService()
    xp = _FakeXpService()
    bot = _FakeBot(duel_service=duel, xp_service=xp)
    d = Duels(bot)

    await d._apply_expired_ui({"guild_id": 999, "channel_id": 1, "message_id": 2, "player_a_id": 1, "player_b_id": 2})


# ---------------------------------------------------------------------------
# Tests duel_command
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_duel_command_rejects_bot_member(monkeypatch):
    duel = _FakeDuelService()
    xp = _FakeXpService()
    bot = _FakeBot(duel_service=duel, xp_service=xp)
    d = Duels(bot)

    ctx = _FakeCtx(guild=_FakeGuild(), channel=_FakeChannel(), user=_FakeMember(1))
    member = _FakeMember(2, bot=True)

    await d.duel_command(ctx, member)

    assert ctx.deferred == [{"ephemeral": True}]
    assert ctx.followup.sent[-1]["content"] == "🤖 Tu ne peux pas défier un bot."
    assert duel.new_duel_calls == []


@pytest.mark.asyncio
async def test_duel_command_rejects_self(monkeypatch):
    duel = _FakeDuelService()
    xp = _FakeXpService()
    bot = _FakeBot(duel_service=duel, xp_service=xp)
    d = Duels(bot)

    ctx = _FakeCtx(guild=_FakeGuild(), channel=_FakeChannel(), user=_FakeMember(1))
    member = _FakeMember(1)

    await d.duel_command(ctx, member)

    assert ctx.followup.sent[-1]["content"] == "😅 Tu ne peux pas te défier toi-même."
    assert duel.new_duel_calls == []


@pytest.mark.asyncio
async def test_duel_command_outside_guild_respond(monkeypatch):
    duel = _FakeDuelService()
    xp = _FakeXpService()
    bot = _FakeBot(duel_service=duel, xp_service=xp)
    d = Duels(bot)

    ctx = _FakeCtx(guild=None, channel=None, user=_FakeMember(1))
    member = _FakeMember(2)

    await d.duel_command(ctx, member)

    assert ctx.responded == [{"content": "❌ Utilisable uniquement sur un serveur.", "ephemeral": True}]
    assert duel.new_duel_calls == []


@pytest.mark.asyncio
async def test_duel_command_xp_disabled_sends_embed(monkeypatch):
    duel = _FakeDuelService()
    xp = _FakeXpService()
    xp._enabled = False

    bot = _FakeBot(duel_service=duel, xp_service=xp)
    d = Duels(bot)

    async def fake_xp_disable_embed(guild_id, _bot):
        assert guild_id == 123
        return ("EMBED", ["FILES"])

    monkeypatch.setattr(duels_mod, "build_xp_disable_embed", fake_xp_disable_embed)

    ctx = _FakeCtx(guild=_FakeGuild(123), channel=_FakeChannel(99), user=_FakeMember(1))
    member = _FakeMember(2)

    await d.duel_command(ctx, member)

    last = ctx.followup.sent[-1]
    assert last["embed"] == "EMBED"
    assert last["files"] == ["FILES"]
    assert last["ephemeral"] is True
    assert duel.new_duel_calls == []


@pytest.mark.asyncio
async def test_duel_command_duel_error(monkeypatch):
    # DuelError est importé dans le module; on le récupère depuis là
    DuelError = duels_mod.DuelError

    duel = _FakeDuelService()
    duel._new_duel_side_effect = DuelError("nope")
    xp = _FakeXpService()
    bot = _FakeBot(duel_service=duel, xp_service=xp)
    d = Duels(bot)

    monkeypatch.setattr(duels_mod, "duel_error_message", lambda e: f"ERR:{e}")

    ctx = _FakeCtx(guild=_FakeGuild(123), channel=_FakeChannel(99), user=_FakeMember(1))
    member = _FakeMember(2)

    await d.duel_command(ctx, member)

    assert ctx.followup.sent[-1]["content"] == "ERR:nope"
    assert duel.new_duel_calls == [(123, 99, 1, 2)]


@pytest.mark.asyncio
async def test_duel_command_success_sends_home_view(monkeypatch):
    duel = _FakeDuelService()
    xp = _FakeXpService()
    bot = _FakeBot(duel_service=duel, xp_service=xp)
    d = Duels(bot)

    async def fake_build_home(expires_at):
        assert expires_at == 111
        return ("EMBED", ["FILES"])

    class _HomeView:
        def __init__(self, *, bot, duel_id):
            self.bot = bot
            self.duel_id = duel_id

    monkeypatch.setattr(duels_mod, "build_home_duels_embed", fake_build_home)
    monkeypatch.setattr(duels_mod, "HomeView", _HomeView)

    ctx = _FakeCtx(guild=_FakeGuild(123), channel=_FakeChannel(99), user=_FakeMember(1))
    member = _FakeMember(2)

    await d.duel_command(ctx, member)

    last = ctx.followup.sent[-1]
    assert last["embed"] == "EMBED"
    assert last["files"] == ["FILES"]
    assert isinstance(last["view"], _HomeView)
    assert last["view"].duel_id == 777
    assert last["ephemeral"] is True
    assert duel.new_duel_calls == [(123, 99, 1, 2)]


# ---------------------------------------------------------------------------
# Tests setup()
# ---------------------------------------------------------------------------
def test_setup_adds_cog(monkeypatch):
    duel = _FakeDuelService()
    xp = _FakeXpService()
    bot = _FakeBot(duel_service=duel, xp_service=xp)

    added = {}

    def add_cog(cog):
        added["cog"] = cog

    bot.add_cog = add_cog  # type: ignore[attr-defined]

    setup(bot)

    assert isinstance(added["cog"], Duels)
    assert added["cog"].bot is bot
