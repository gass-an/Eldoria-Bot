import pytest

from tests._pages_fakes import FakeCtx, FakePerms, FakeUser  # noqa: F401 installs discord.ui stubs


class _PermObj:
    def __init__(self, value: int):
        self.value = value


class FakeCmd:
    def __init__(self, name: str, *, can_run=True, default_perms: int | None = None):
        self.name = name
        self._can_run = can_run
        self.default_member_permissions = _PermObj(default_perms) if default_perms is not None else None

    async def can_run(self, ctx):
        return self._can_run


class FakeBot:
    def __init__(self, cmds):
        self.application_commands = cmds


@pytest.mark.asyncio
async def test_send_help_menu_no_visible_commands(monkeypatch):
    import eldoria.pages.help_menu as mod

    # help config: one category with one command, but user can't run it
    monkeypatch.setattr(
        mod.help_json,
        "load_help_config",
        lambda: (
            {"ban": "Ban"},
            {"Moderation": ["ban"]},
            {"Moderation": "desc"},
        ),
    )

    bot = FakeBot([FakeCmd("ban", can_run=False)])
    ctx = FakeCtx(user=FakeUser(1, guild_permissions=FakePerms(0)))

    await mod.send_help_menu(ctx, bot)

    # should defer ephemeral
    assert ctx.deferred and ctx.deferred[0]["ephemeral"] is True

    # should send "Aucune commande..."
    assert ctx.followup.sent
    assert "Aucune commande disponible" in ctx.followup.sent[-1]["content"]
    assert ctx.followup.sent[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_send_help_menu_builds_view_and_sends_embed(monkeypatch):
    import eldoria.pages.help_menu as mod

    # help config declares only "ping" in category Utils
    monkeypatch.setattr(
        mod.help_json,
        "load_help_config",
        lambda: (
            {"ping": "Ping"},
            {"Utils": ["ping"]},
            {"Utils": "desc"},
        ),
    )

    # bot also has an undeclared command => should go to "Autres"
    cmds = [
        FakeCmd("ping", can_run=True),
        FakeCmd("foo", can_run=True),
        FakeCmd("help", can_run=True),  # ignored from Autres addition
        FakeCmd("manual_save", can_run=True),  # excluded
    ]
    bot = FakeBot(cmds)

    # Replace HelpMenuView with a light fake (we don't test embed rendering here)
    created = {}

    class FakeView:
        def __init__(self, *, author_id, bot, cmd_map, help_infos, visible_by_cat, cat_descriptions):
            created["author_id"] = author_id
            created["visible_by_cat"] = visible_by_cat
            self.visible_by_cat = visible_by_cat

        def build_home(self):
            return ("HOME_EMBED", ["HOME_FILES"])

    monkeypatch.setattr(mod, "HelpMenuView", FakeView)

    # user has perms that allow everything (dp check passes)
    ctx = FakeCtx(user=FakeUser(42, guild_permissions=FakePerms(0xFFFFFFFF)))

    await mod.send_help_menu(ctx, bot)

    assert created["author_id"] == 42
    # Should include declared category + auto "Autres" for foo
    assert "Utils" in created["visible_by_cat"]
    assert created["visible_by_cat"]["Utils"] == ["ping"]
    assert "Autres" in created["visible_by_cat"]
    assert "foo" in created["visible_by_cat"]["Autres"]
    # Excluded cmd removed
    assert "manual_save" not in created["visible_by_cat"].get("Autres", [])

    # sends embed/files/view
    assert ctx.followup.sent
    payload = ctx.followup.sent[-1]
    assert payload["embed"] == "HOME_EMBED"
    assert payload["files"] == ["HOME_FILES"]
    assert payload["view"] is not None
    assert payload["ephemeral"] is True


@pytest.mark.asyncio
async def test_send_help_menu_filters_by_default_member_permissions(monkeypatch):
    import eldoria.pages.help_menu as mod

    monkeypatch.setattr(
        mod.help_json,
        "load_help_config",
        lambda: (
            {"secure": "Secure"},
            {"Admin": ["secure"]},
            {"Admin": "desc"},
        ),
    )

    # command requires perms bit 0b10
    bot = FakeBot([FakeCmd("secure", can_run=True, default_perms=0b10)])

    # user has only 0b01 => should not see it
    ctx = FakeCtx(user=FakeUser(1, guild_permissions=FakePerms(0b01)))

    await mod.send_help_menu(ctx, bot)

    assert ctx.followup.sent
    assert "Aucune commande disponible" in ctx.followup.sent[-1]["content"]
