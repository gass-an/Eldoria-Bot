import pytest

# Import du module après les stubs
import eldoria.extensions.duels as duels_mod
from eldoria.extensions.duels import Duels, require_guild_ctx, setup
from tests._fakes import (
    FakeBot,
    FakeChannel,
    FakeCtx,
    FakeDuelService,
    FakeFetchMessageChannel,
    FakeGuild,
    FakeMember,
    FakeMessage,
    FakeXpService,
)


# ---------------------------------------------------------------------------
# Tests require_guild_ctx
# ---------------------------------------------------------------------------
def test_require_guild_ctx_ok():
    guild = FakeGuild()
    channel = FakeChannel()
    ctx = FakeCtx(guild=guild, channel=channel, user=FakeMember(1))
    g, c = require_guild_ctx(ctx)
    assert g is guild
    assert c is channel


def test_require_guild_ctx_raises_outside_guild():
    from eldoria.exceptions.general import GuildRequired

    ctx = FakeCtx(guild=None, channel=None, user=FakeMember(1))
    with pytest.raises(GuildRequired):
        require_guild_ctx(ctx)



# ---------------------------------------------------------------------------
# Tests __init__ loops started
# ---------------------------------------------------------------------------
def test_duels_init_starts_loops(monkeypatch):
    duel = FakeDuelService()
    xp = FakeXpService()
    bot = FakeBot(duel_service=duel, xp_service=xp)

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
    duel = FakeDuelService()
    xp = FakeXpService()
    bot = FakeBot(duel_service=duel, xp_service=xp)

    d = Duels(bot)

    monkeypatch.setattr(duels_mod, "now_ts", lambda: 9999)
    await d.maintenance_cleanup()


    assert duel.cleanup_calls == [9999]


@pytest.mark.asyncio
async def test_before_loops_wait_ready(monkeypatch):
    duel = FakeDuelService()
    xp = FakeXpService()
    bot = FakeBot(duel_service=duel, xp_service=xp)
    d = Duels(bot)

    await d.before_maintenance_cleanup()
    await d.before_clear_expired_duels_loop()

    assert bot._waited == 2


@pytest.mark.asyncio
async def test_clear_expired_duels_applies_ui_and_syncs_roles(monkeypatch):
    duel = FakeDuelService()
    xp = FakeXpService()
    bot = FakeBot(duel_service=duel, xp_service=xp)

    guild = FakeGuild(123)
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
    duel = FakeDuelService()
    xp = FakeXpService()
    bot = FakeBot(duel_service=duel, xp_service=xp)

    guild = FakeGuild(123)
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
    duel = FakeDuelService()
    xp = FakeXpService()
    bot = FakeBot(duel_service=duel, xp_service=xp)

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
    duel = FakeDuelService()
    xp = FakeXpService()
    bot = FakeBot(duel_service=duel, xp_service=xp)
    guild = FakeGuild(123)
    bot._guilds[123] = guild

    msg = FakeMessage()
    fake_channel = FakeFetchMessageChannel(20, message=msg)

    async def fake_get_member(g, mid):
        assert g is guild
        return FakeMember(mid)

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
    assert msg.edits == [{"content": "", "embed": "EMBED", "view": None, "files": None}]


@pytest.mark.asyncio
async def test_apply_expired_ui_returns_if_missing_ids(monkeypatch):
    duel = FakeDuelService()
    xp = FakeXpService()
    bot = FakeBot(duel_service=duel, xp_service=xp)
    d = Duels(bot)

    await d._apply_expired_ui({"guild_id": 1})  # no channel/message
    # no exception => ok


@pytest.mark.asyncio
async def test_apply_expired_ui_returns_if_guild_missing(monkeypatch):
    duel = FakeDuelService()
    xp = FakeXpService()
    bot = FakeBot(duel_service=duel, xp_service=xp)
    d = Duels(bot)

    await d._apply_expired_ui({"guild_id": 999, "channel_id": 1, "message_id": 2, "player_a_id": 1, "player_b_id": 2})


# ---------------------------------------------------------------------------
# Tests duel_command
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_duel_command_rejects_bot_member(monkeypatch):
    duel = FakeDuelService()
    xp = FakeXpService()
    bot = FakeBot(duel_service=duel, xp_service=xp)
    d = Duels(bot)

    ctx = FakeCtx(guild=FakeGuild(), channel=FakeChannel(), user=FakeMember(1))
    member = FakeMember(2, bot=True)

    from eldoria.exceptions.general import BotTargetNotAllowed

    with pytest.raises(BotTargetNotAllowed):
        await d.duel_command(ctx, member)

    assert ctx.deferred is True
    assert ctx.defer_ephemeral is True
    assert duel.new_duel_calls == []


@pytest.mark.asyncio
async def test_duel_command_rejects_self(monkeypatch):
    duel = FakeDuelService()
    xp = FakeXpService()
    bot = FakeBot(duel_service=duel, xp_service=xp)
    d = Duels(bot)

    ctx = FakeCtx(guild=FakeGuild(), channel=FakeChannel(), user=FakeMember(1))
    member = FakeMember(1)

    from eldoria.exceptions.duel import SamePlayerDuel

    with pytest.raises(SamePlayerDuel):
        await d.duel_command(ctx, member)

    assert duel.new_duel_calls == []


@pytest.mark.asyncio
async def test_duel_command_outside_guild_raises(monkeypatch):
    from eldoria.exceptions.general import GuildRequired

    duel = FakeDuelService()
    xp = FakeXpService()
    bot = FakeBot(duel_service=duel, xp_service=xp)
    d = Duels(bot)

    ctx = FakeCtx(guild=None, channel=None, user=FakeMember(1))
    member = FakeMember(2)

    with pytest.raises(GuildRequired):
        await d.duel_command(ctx, member)

    assert duel.new_duel_calls == []


@pytest.mark.asyncio
async def test_duel_command_xp_disabled_sends_embed(monkeypatch):
    duel = FakeDuelService()
    xp = FakeXpService()
    xp._enabled = False

    bot = FakeBot(duel_service=duel, xp_service=xp)
    d = Duels(bot)

    ctx = FakeCtx(guild=FakeGuild(123), channel=FakeChannel(99), user=FakeMember(1))
    member = FakeMember(2)

    from eldoria.exceptions.general import XpDisabled

    with pytest.raises(XpDisabled):
        await d.duel_command(ctx, member)

    assert duel.new_duel_calls == []


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_duel_command_duel_error(monkeypatch):
    from eldoria.exceptions.duel import DuelError

    duel = FakeDuelService()
    duel._new_duel_side_effect = DuelError("nope")
    xp = FakeXpService()
    bot = FakeBot(duel_service=duel, xp_service=xp)
    d = Duels(bot)

    ctx = FakeCtx(guild=FakeGuild(123), channel=FakeChannel(99), user=FakeMember(1))
    member = FakeMember(2)

    with pytest.raises(DuelError):
        await d.duel_command(ctx, member)

    assert duel.new_duel_calls == [(123, 99, 1, 2)]



@pytest.mark.asyncio
async def test_duel_command_success_sends_home_view(monkeypatch):
    duel = FakeDuelService()
    xp = FakeXpService()
    bot = FakeBot(duel_service=duel, xp_service=xp)
    d = Duels(bot)

    async def fake_build_home(expires_at):
        assert expires_at == 111
        return ("EMBED", ["FILES"])

    monkeypatch.setattr(duels_mod, "build_home_duels_embed", fake_build_home)
    monkeypatch.setattr(
        duels_mod,
        "HomeView",
        lambda *, bot, duel_id: type("HomeViewStub", (), {"bot": bot, "duel_id": duel_id})(),
    )

    ctx = FakeCtx(guild=FakeGuild(123), channel=FakeChannel(99), user=FakeMember(1))
    member = FakeMember(2)

    await d.duel_command(ctx, member)

    last = ctx.followup.sent[-1]
    assert last["embed"] == "EMBED"
    assert last["files"] == ["FILES"]
    assert getattr(last["view"], "duel_id") == 777
    assert getattr(last["view"], "bot") is bot
    assert last["ephemeral"] is True
    assert duel.new_duel_calls == [(123, 99, 1, 2)]


# ---------------------------------------------------------------------------
# Tests setup()
# ---------------------------------------------------------------------------
def test_setup_adds_cog(monkeypatch):
    duel = FakeDuelService()
    xp = FakeXpService()
    bot = FakeBot(duel_service=duel, xp_service=xp)

    added = {}

    def add_cog(cog):
        added["cog"] = cog

    bot.add_cog = add_cog  # type: ignore[attr-defined]

    setup(bot)

    assert isinstance(added["cog"], Duels)
    assert added["cog"].bot is bot
