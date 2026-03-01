from __future__ import annotations

from types import SimpleNamespace

import discord  # type: ignore
import pytest

from eldoria.ui.help import view as M
from tests._fakes import (
    FakeCtx,
    FakeInteraction,
    FakeMessage,
    FakeUser,
)


def make_perms(value: int):
    return SimpleNamespace(value=value)


def make_cmd(name: str, *, dp=None, can_run=True):
    async def _can_run(ctx):
        if isinstance(can_run, BaseException):
            raise can_run
        return bool(can_run)

    return SimpleNamespace(name=name, default_member_permissions=dp, can_run=_can_run)


def make_interaction(*, user: FakeUser, message=None, custom_id: str | None = None):
    data = {} if custom_id is None else {"custom_id": custom_id}
    return FakeInteraction(user=user, message=message, data=data)


def _make_view(*, author_id=1, visible_by_cat=None):
    visible_by_cat = visible_by_cat or {"XP": ["xp_rank"], "Duels": ["duel"]}
    cmd_map: dict[str, object] = {}
    help_infos: dict[str, str] = {}
    cat_desc = {"XP": "Système XP", "Duels": "Duels !"}
    view = M.HelpMenuView(
        author_id=author_id,
        cmd_map=cmd_map,
        help_infos=help_infos,
        visible_by_cat=visible_by_cat,
        cat_descriptions=cat_desc,
    )
    return view


def test_help_menu_view_init_creates_buttons_and_sets_home_active():
    view = _make_view()

    # 1 bouton Accueil + 1 bouton par catégorie
    assert view.home_button.label == "Accueil"
    assert set(view._cat_buttons.keys()) == {"XP", "Duels"}
    assert len(view.children) == 1 + 2

    # Home active => primary + disabled
    assert view.current is None
    assert view.home_button.disabled is True
    assert view.home_button.style == discord.ButtonStyle.primary

    # Cat buttons inactive => secondary + enabled
    for btn in view._cat_buttons.values():
        assert btn.disabled is False
        assert btn.style == discord.ButtonStyle.secondary


def test_common_files_helper(monkeypatch):
    view = _make_view()
    view._thumb_url = "T"
    view._banner_url = "B"

    monkeypatch.setattr(M, "common_files", lambda *_a: ["F"], raising=True)
    assert view._common_files() == ["F"]


def test_build_home_and_category_call_builders(monkeypatch):
    view = _make_view()
    view._thumb_url = "T"
    view._banner_url = "B"

    monkeypatch.setattr(M, "common_files", lambda *_a: ["FILES"], raising=True)

    monkeypatch.setattr(
        M,
        "build_home_embed",
        lambda **kw: ("HOME", kw["thumb_url"], kw["banner_url"]),
        raising=True,
    )
    monkeypatch.setattr(
        M,
        "build_category_embed",
        lambda **kw: ("CAT", kw["cat"], kw["cmds"], kw["thumb_url"], kw["banner_url"]),
        raising=True,
    )

    home_embed, home_files = view.build_home()
    assert home_embed[0] == "HOME"
    assert home_files == ["FILES"]

    cat_embed, cat_files = view.build_category("XP")
    assert cat_embed[0] == "CAT"
    assert cat_files == ["FILES"]


def test_refresh_nav_buttons_when_in_category_marks_category_active():
    view = _make_view()

    view.current = "Duels"
    view._refresh_nav_buttons()

    # Home redevient cliquable
    assert view.home_button.disabled is False
    assert view.home_button.style == discord.ButtonStyle.secondary

    # Duels active
    assert view._cat_buttons["Duels"].disabled is True
    assert view._cat_buttons["Duels"].style == discord.ButtonStyle.primary

    # XP inactive
    assert view._cat_buttons["XP"].disabled is False
    assert view._cat_buttons["XP"].style == discord.ButtonStyle.secondary


@pytest.mark.asyncio
async def test_interaction_check_blocks_other_user_and_uses_response_send(monkeypatch):
    # interaction_check est fourni par BasePanelView (message différent)
    view = _make_view(author_id=1)

    inter = make_interaction(user=FakeUser(2))  # pas l'auteur
    ok = await view.interaction_check(inter)

    assert ok is False
    assert inter.response.sent
    assert inter.response.sent[-1]["content"] == "❌ Seul l'auteur de la commande peut utiliser ce panneau."
    assert inter.response.sent[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_on_timeout_disables_all_buttons():
    view = _make_view()
    assert any(isinstance(i, discord.ui.Button) and not i.disabled for i in view.children)

    await view.on_timeout()

    for item in view.children:
        if isinstance(item, (discord.ui.Button, discord.ui.Select)):
            assert item.disabled is True


@pytest.mark.asyncio
async def test_safe_edit_when_response_not_done_uses_response_edit_message():
    view = _make_view()
    inter = make_interaction(user=FakeUser(1), message=FakeMessage())  # is_done False par défaut

    await view._safe_edit(inter, embed="EMBED", files=["FILES"])

    assert inter.response.edits == [{"embed": "EMBED", "view": view}]
    assert inter.response.deferred is False
    assert inter.original_edits == []


@pytest.mark.asyncio
async def test_safe_edit_when_response_done_and_uploaded_once_edits_original_without_files():
    view = _make_view()
    view._uploaded_once = True

    inter = make_interaction(user=FakeUser(1), message=FakeMessage())
    inter.response._done = True  # type: ignore[attr-defined]

    await view._safe_edit(inter, embed="E", files=["F"])
    assert inter.original_edits == [
        {"content": None, "embeds": None, "attachments": None, "view": view, "embed": "E", "files": None}
    ]


@pytest.mark.asyncio
async def test_safe_edit_when_response_done_first_time_sends_files_and_sets_flag():
    view = _make_view()
    view._uploaded_once = False

    inter = make_interaction(user=FakeUser(1), message=FakeMessage())
    inter.response._done = True  # type: ignore[attr-defined]

    await view._safe_edit(inter, embed="E", files=["F"])
    assert inter.original_edits[-1]["files"] == ["F"]
    assert view._uploaded_once is True


@pytest.mark.asyncio
async def test_safe_edit_handles_notfound_and_http_exception():
    view = _make_view()

    # NotFound
    inter1 = make_interaction(user=FakeUser(1), message=FakeMessage())
    inter1.raise_on_edit_original = discord.NotFound  # type: ignore[attr-defined]
    await view._safe_edit(inter1, embed="E", files=["F"])
    assert inter1.original_edits == []

    # HTTPException
    inter2 = make_interaction(user=FakeUser(1), message=FakeMessage())
    inter2.raise_on_edit_original = discord.HTTPException  # type: ignore[attr-defined]
    await view._safe_edit(inter2, embed="E", files=["F"])
    assert inter2.original_edits == []


@pytest.mark.asyncio
async def test_click_category_button_routes_sets_current_refreshes_and_calls_safe_edit(monkeypatch):
    view = _make_view()

    # mock build_category + _safe_edit
    view.build_category = lambda cat: ("EMBED_CAT", ["FILES_CAT"])  # type: ignore[assignment]

    safe_calls: list[dict] = []

    async def fake_safe(interaction, *, embed, files=None):
        safe_calls.append({"embed": embed, "files": files, "current": view.current})

    view._safe_edit = fake_safe  # type: ignore[assignment]

    # Simule un clic sur le bouton XP (RoutedButton -> view.route_button)
    btn = view._cat_buttons["XP"]
    inter = make_interaction(user=FakeUser(1), message=FakeMessage(), custom_id="help:cat:XP")

    await btn.callback(inter)  # RoutedButton.callback

    assert view.current == "XP"
    assert safe_calls == [{"embed": "EMBED_CAT", "files": ["FILES_CAT"], "current": "XP"}]
    assert view._cat_buttons["XP"].disabled is True
    assert view.home_button.disabled is False


@pytest.mark.asyncio
async def test_click_home_button_routes_go_home(monkeypatch):
    view = _make_view()
    view.current = "XP"
    view._refresh_nav_buttons()

    view.build_home = lambda: ("EMBED_HOME", ["FILES_HOME"])  # type: ignore[assignment]

    safe_calls: list[dict] = []

    async def fake_safe(interaction, *, embed, files=None):
        safe_calls.append({"embed": embed, "files": files, "current": view.current})

    view._safe_edit = fake_safe  # type: ignore[assignment]

    inter = make_interaction(user=FakeUser(1), message=FakeMessage(), custom_id="help:home")

    await view.home_button.callback(inter)  # RoutedButton.callback -> route_button -> _go_home

    assert view.current is None
    assert safe_calls == [{"embed": "EMBED_HOME", "files": ["FILES_HOME"], "current": None}]
    assert view.home_button.disabled is True


@pytest.mark.asyncio
async def test_send_help_menu_no_visible_commands_sends_message(monkeypatch):
    # Config JSON
    def fake_load_help_config():
        help_infos = {"admin": "desc"}
        categories = {"Admin": ["admin"]}
        cat_desc = {"Admin": "Admin tools"}
        return help_infos, categories, cat_desc

    monkeypatch.setattr(M, "load_help_config", fake_load_help_config)

    # cmd existe mais perms insuffisantes
    cmd = make_cmd("admin", dp=make_perms(0b10), can_run=True)
    bot = SimpleNamespace(application_commands=[cmd])

    user = FakeUser(1, guild_permissions=make_perms(0b01))
    ctx = FakeCtx(user=user)

    await M.send_help_menu(ctx, bot)

    assert ctx.followup.sent
    last = ctx.followup.sent[-1]
    assert "Aucune commande disponible avec vos permissions." in (last.get("content") or (last.get("args") or [""])[0])


@pytest.mark.asyncio
async def test_send_help_menu_handles_ctx_without_defer_and_bot_without_application_commands(monkeypatch):
    monkeypatch.setattr(M, "load_help_config", lambda: ({}, {"Cat": ["a"]}, {}))

    # Bot without application_commands attribute triggers getattr None branch
    user = FakeUser(1, guild_permissions=make_perms(0xFFFF))
    ctx = SimpleNamespace(user=user, followup=FakeCtx(user=user).followup)

    await M.send_help_menu(ctx, object())
    assert ctx.followup.sent


@pytest.mark.asyncio
async def test_send_help_menu_builds_visible_by_cat_excludes_internal_and_adds_autres(monkeypatch):
    # Config : une catégorie déclarée + une commande non déclarée
    def fake_load_help_config():
        help_infos = {"a": "A", "manual_save": "X", "insert_db": "Y", "logs": "Z"}  # excluded doit être retiré
        categories = {"Utils": ["a", "manual_save"]}
        cat_desc = {"Utils": "Utils desc", "Autres": "Other"}
        return help_infos, categories, cat_desc

    monkeypatch.setattr(M, "load_help_config", fake_load_help_config)

    # Commands: a visible, b non déclaré visible, help ignoré pour Autres, manual_save/insert_db excluded
    cmd_a = make_cmd("a", dp=None, can_run=True)
    cmd_b = make_cmd("b", dp=None, can_run=True)
    cmd_help = make_cmd("help", dp=None, can_run=True)
    cmd_manual = make_cmd("manual_save", dp=None, can_run=True)
    cmd_insert = make_cmd("insert_db", dp=None, can_run=True)
    cmd_logs = make_cmd("logs", dp=None, can_run=True)

    bot = SimpleNamespace(application_commands=[cmd_a, cmd_b, cmd_help, cmd_manual, cmd_insert, cmd_logs])

    user = FakeUser(42, guild_permissions=make_perms(0xFFFF))
    ctx = FakeCtx(user=user)

    created = {"view": None, "visible_by_cat": None}

    def view_factory(*, author_id, cmd_map, help_infos, visible_by_cat, cat_descriptions):
        created["visible_by_cat"] = visible_by_cat

        view_obj = SimpleNamespace()

        def build_home():
            return ("EMBED_HOME", ["FILES_HOME"])

        view_obj.build_home = build_home
        created["view"] = view_obj
        return view_obj

    monkeypatch.setattr(M, "HelpMenuView", view_factory)

    await M.send_help_menu(ctx, bot)

    assert created["visible_by_cat"] == {"Utils": ["a"], "Autres": ["b"]}

    assert ctx.followup.sent
    last = ctx.followup.sent[-1]
    assert last["embed"] == "EMBED_HOME"
    assert last["files"] == ["FILES_HOME"]
    assert last["view"] is created["view"]
    assert last["ephemeral"] is True


@pytest.mark.asyncio
async def test_send_help_menu_visibility_checks_can_run_false_or_exception(monkeypatch):
    def fake_load_help_config():
        return ({}, {"Cat": ["ok", "no", "boom"]}, {})

    monkeypatch.setattr(M, "load_help_config", fake_load_help_config)

    cmd_ok = make_cmd("ok", can_run=True)
    cmd_no = make_cmd("no", can_run=False)
    cmd_boom = make_cmd("boom", can_run=RuntimeError("fail"))

    bot = SimpleNamespace(application_commands=[cmd_ok, cmd_no, cmd_boom])

    user = FakeUser(1, guild_permissions=make_perms(0xFFFF))
    ctx = FakeCtx(user=user)

    created = {"visible_by_cat": None}

    def view_factory(*, author_id, cmd_map, help_infos, visible_by_cat, cat_descriptions):
        created["visible_by_cat"] = visible_by_cat
        return SimpleNamespace(build_home=lambda: ("E", ["F"]))

    monkeypatch.setattr(M, "HelpMenuView", view_factory)

    await M.send_help_menu(ctx, bot)

    assert created["visible_by_cat"] == {"Cat": ["ok"]}