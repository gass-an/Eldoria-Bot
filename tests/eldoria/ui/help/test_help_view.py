from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.help import view as M
from tests._fakes._pages_fakes import (
    FakeCtx,
    FakeInteraction,
    FakeMessage,
    FakeUser,
)


# ------------------------------------------------------------
# CompatInteraction : support edit_original_response(embed/files/view)
# + enregistre aussi response.edit_message
# ------------------------------------------------------------
class CompatInteraction(FakeInteraction):
    def __init__(self, *, user: FakeUser, message=None):
        super().__init__(user=user, message=message)
        self.response_edit_calls: list[dict] = []

        # Patch: FakeResponse.edit_message stocke déjà .edits
        # mais on garde aussi ici si tu veux inspecter.
        orig_edit = self.response.edit_message

        async def wrapped_edit_message(*, embed=None, view=None):
            self.response_edit_calls.append({"embed": embed, "view": view})
            await orig_edit(embed=embed, view=view)

        self.response.edit_message = wrapped_edit_message  # type: ignore[assignment]

    async def edit_original_response(
        self,
        *,
        content=None,
        embeds=None,
        attachments=None,
        view=None,
        embed=None,
        files=None,
    ):
        # Reproduit le comportement du fake original: lève AVANT de logguer
        if getattr(self, "raise_on_edit_original", None) is not None:
            raise self.raise_on_edit_original  # type: ignore[misc]

        self.original_edits.append(
            {
                "content": content,
                "embeds": embeds,
                "attachments": attachments,
                "view": view,
                "embed": embed,
                "files": files,
            }
        )



class FakePerms:
    def __init__(self, value: int):
        self.value = value


class FakeCmd:
    def __init__(self, name: str, *, dp=None, can_run=True):
        self.name = name
        self.default_member_permissions = dp
        self._can_run = can_run

    async def can_run(self, ctx):
        if isinstance(self._can_run, BaseException):
            raise self._can_run
        return bool(self._can_run)


class FakeBot:
    def __init__(self, cmds):
        self.application_commands = cmds



def _make_view(monkeypatch, *, author_id=1, visible_by_cat=None):
    visible_by_cat = visible_by_cat or {"XP": ["xp_rank"], "Duels": ["duel"]}
    bot = object()
    cmd_map = {}
    help_infos = {}
    cat_desc = {"XP": "Système XP", "Duels": "Duels !"}
    view = M.HelpMenuView(
        author_id=author_id,
        bot=bot,
        cmd_map=cmd_map,
        help_infos=help_infos,
        visible_by_cat=visible_by_cat,
        cat_descriptions=cat_desc,
    )
    return view


def test_help_menu_view_init_creates_buttons_and_sets_home_active(monkeypatch):
    view = _make_view(monkeypatch)

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


@pytest.mark.asyncio
async def test_home_button_callback_with_no_view_noops(monkeypatch):
    btn = M.HomeButton()
    btn.view = None  # type: ignore[attr-defined]
    # Par défaut, btn.view est None (pas ajouté dans une View)
    inter = CompatInteraction(user=FakeUser(1), message=FakeMessage())
    await btn.callback(inter)  # ne doit pas lever


@pytest.mark.asyncio
async def test_category_button_callback_with_no_view_noops(monkeypatch):
    btn = M.CategoryButton("XP")
    btn.view = None  # type: ignore[attr-defined]
    inter = CompatInteraction(user=FakeUser(1), message=FakeMessage())
    await btn.callback(inter)  # ne doit pas lever


def test_common_files_and_decorate_helpers(monkeypatch):
    view = _make_view(monkeypatch)
    view._thumb_url = "T"
    view._banner_url = "B"

    monkeypatch.setattr(M, "common_files", lambda *_a: ["F"], raising=True)
    monkeypatch.setattr(M, "decorate", lambda e, *_a: f"DECOR({e})", raising=True)

    assert view._common_files() == ["F"]
    assert view._decorate("E") == "DECOR(E)"


def test_build_home_and_category_call_builders(monkeypatch):
    view = _make_view(monkeypatch)
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


def test_refresh_nav_buttons_when_in_category_marks_category_active(monkeypatch):
    view = _make_view(monkeypatch)

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
    view = _make_view(monkeypatch, author_id=1)

    inter = CompatInteraction(user=FakeUser(2))  # pas l'auteur
    ok = await view.interaction_check(inter)

    assert ok is False
    assert inter.response.sent
    assert inter.response.sent[-1]["content"] == "❌ Ce menu ne t'appartient pas."
    assert inter.response.sent[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_interaction_check_blocks_other_user_and_falls_back_to_followup(monkeypatch):
    view = _make_view(monkeypatch, author_id=1)

    inter = CompatInteraction(user=FakeUser(2))
    # Simule "déjà répondu" => response.send_message lève InteractionResponded
    inter.response.raise_on_send = discord.InteractionResponded  # type: ignore[attr-defined]

    ok = await view.interaction_check(inter)

    assert ok is False
    assert inter.followup.sent
    assert inter.followup.sent[-1]["content"] == "❌ Ce menu ne t'appartient pas."
    assert inter.followup.sent[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_on_timeout_disables_all_buttons(monkeypatch):
    view = _make_view(monkeypatch)
    # sanity: avant
    assert any(isinstance(i, discord.ui.Button) and not i.disabled for i in view.children)

    await view.on_timeout()

    for item in view.children:
        if isinstance(item, discord.ui.Button):
            assert item.disabled is True


@pytest.mark.asyncio
async def test_safe_edit_fast_path_when_urls_known_uses_response_edit_message(monkeypatch):
    view = _make_view(monkeypatch)
    view._thumb_url = "T"
    view._banner_url = "B"

    # message avec attachments non nécessaire ici
    inter = CompatInteraction(user=FakeUser(1), message=FakeMessage())

    await view._safe_edit(inter, embed="EMBED", files=["FILES"])

    # fast_no_files => response.edit_message appelé et return
    assert inter.response_edit_calls == [{"embed": "EMBED", "view": view}]
    assert inter.response.deferred is False
    assert inter.original_edits == []


@pytest.mark.asyncio
async def test_safe_edit_when_response_not_done_uses_response_edit_message(monkeypatch):
    view = _make_view(monkeypatch)

    inter = CompatInteraction(user=FakeUser(1), message=FakeMessage())  # is_done False par défaut

    await view._safe_edit(inter, embed="EMBED", files=["FILES"])

    assert inter.response_edit_calls == [{"embed": "EMBED", "view": view}]
    assert inter.response.deferred is False
    assert inter.original_edits == []


@pytest.mark.asyncio
async def test_safe_edit_when_response_done_and_uploaded_once_edits_original_without_files(monkeypatch):
    view = _make_view(monkeypatch)
    view._uploaded_once = True

    inter = CompatInteraction(user=FakeUser(1), message=FakeMessage())
    inter.response._done = True  # type: ignore[attr-defined]

    await view._safe_edit(inter, embed="E", files=["F"])
    assert inter.original_edits == [{"content": None, "embeds": None, "attachments": None, "view": view, "embed": "E", "files": None}]


@pytest.mark.asyncio
async def test_safe_edit_when_response_done_first_time_sends_files_and_sets_flag(monkeypatch):
    view = _make_view(monkeypatch)
    view._uploaded_once = False

    inter = CompatInteraction(user=FakeUser(1), message=FakeMessage())
    inter.response._done = True  # type: ignore[attr-defined]

    await view._safe_edit(inter, embed="E", files=["F"])
    assert inter.original_edits[-1]["files"] == ["F"]
    assert view._uploaded_once is True


@pytest.mark.asyncio
async def test_safe_edit_handles_notfound_and_http_exception(monkeypatch):
    view = _make_view(monkeypatch)

    # NotFound
    inter1 = CompatInteraction(user=FakeUser(1), message=FakeMessage())
    inter1.raise_on_edit_original = discord.NotFound  # type: ignore[attr-defined]
    await view._safe_edit(inter1, embed="E", files=["F"])
    assert inter1.original_edits == []

    # HTTPException
    inter2 = CompatInteraction(user=FakeUser(1), message=FakeMessage())
    inter2.raise_on_edit_original = discord.HTTPException  # type: ignore[attr-defined]
    await view._safe_edit(inter2, embed="E", files=["F"])
    assert inter2.original_edits == []


@pytest.mark.asyncio
async def test_make_cat_cb_sets_current_refreshes_and_calls_safe_edit(monkeypatch):
    view = _make_view(monkeypatch)

    # mock build_category + _safe_edit
    view.build_category = lambda cat: ("EMBED_CAT", ["FILES_CAT"])  # type: ignore[assignment]

    safe_calls: list[dict] = []

    async def fake_safe(interaction, *, embed, files=None):
        safe_calls.append({"embed": embed, "files": files, "current": view.current})

    view._safe_edit = fake_safe  # type: ignore[assignment]

    inter = CompatInteraction(user=FakeUser(1), message=FakeMessage())

    # Nouveau code: les boutons de catégorie sont des instances de CategoryButton.
    btn = view._cat_buttons["XP"]
    await btn.callback(inter)  # type: ignore[attr-defined]

    assert view.current == "XP"
    assert safe_calls == [{"embed": "EMBED_CAT", "files": ["FILES_CAT"], "current": "XP"}]
    assert view._cat_buttons["XP"].disabled is True
    assert view.home_button.disabled is False


@pytest.mark.asyncio
async def test_go_home_sets_current_none_refreshes_and_calls_safe_edit(monkeypatch):
    view = _make_view(monkeypatch)
    view.current = "XP"
    view._refresh_nav_buttons()

    view.build_home = lambda: ("EMBED_HOME", ["FILES_HOME"])  # type: ignore[assignment]

    safe_calls: list[dict] = []

    async def fake_safe(interaction, *, embed, files=None):
        safe_calls.append({"embed": embed, "files": files, "current": view.current})

    view._safe_edit = fake_safe  # type: ignore[assignment]

    inter = CompatInteraction(user=FakeUser(1), message=FakeMessage())

    await view._go_home(inter)

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
    cmd = FakeCmd("admin", dp=FakePerms(0b10), can_run=True)
    bot = FakeBot([cmd])

    user = FakeUser(1, guild_permissions=FakePerms(0b01))
    ctx = FakeCtx(user=user)

    await M.send_help_menu(ctx, bot)

    # followup send "Aucune commande..."
    assert ctx.followup.sent
    last = ctx.followup.sent[-1]

    assert "Aucune commande disponible avec vos permissions." in (
    last.get("content") or (last.get("args") or [""])[0]
)


@pytest.mark.asyncio
async def test_send_help_menu_handles_ctx_without_defer_and_bot_without_application_commands(monkeypatch):
    # load_help_config minimal
    monkeypatch.setattr(M, "load_help_config", lambda: ({}, {"Cat": ["a"]}, {}))

    # Bot without application_commands attribute triggers cmds None branch
    class Bot:
        pass

    user = FakeUser(1, guild_permissions=FakePerms(0xFFFF))

    class CtxNoDefer:
        def __init__(self, user):
            self.user = user
            self.followup = FakeCtx(user=user).followup

    ctx = CtxNoDefer(user)

    await M.send_help_menu(ctx, Bot())
    # no visible commands -> followup message
    assert ctx.followup.sent


@pytest.mark.asyncio
async def test_send_help_menu_builds_visible_by_cat_excludes_internal_and_adds_autres(monkeypatch):
    # Config : une catégorie déclarée + une commande non déclarée
    def fake_load_help_config():
        help_infos = {"a": "A", "manual_save": "X", "insert_db": "Y"}  # excluded doit être retiré
        categories = {"Utils": ["a", "manual_save"]}
        cat_desc = {"Utils": "Utils desc", "Autres": "Other"}
        return help_infos, categories, cat_desc

    monkeypatch.setattr(M, "load_help_config", fake_load_help_config)

    # Commands: a visible, b non déclaré visible, help ignoré, manual_save excluded
    cmd_a = FakeCmd("a", dp=None, can_run=True)
    cmd_b = FakeCmd("b", dp=None, can_run=True)
    cmd_help = FakeCmd("help", dp=None, can_run=True)
    cmd_manual = FakeCmd("manual_save", dp=None, can_run=True)
    cmd_insert = FakeCmd("insert_db", dp=None, can_run=True)

    bot = FakeBot([cmd_a, cmd_b, cmd_help, cmd_manual, cmd_insert])

    user = FakeUser(42, guild_permissions=FakePerms(0xFFFF))
    ctx = FakeCtx(user=user)

    # On veut éviter de tester les builders internes: on patch view + build_home
    created = {"view": None, "visible_by_cat": None}

    class FakeView:
        def __init__(self, *, author_id, bot, cmd_map, help_infos, visible_by_cat, cat_descriptions):
            created["view"] = self
            created["visible_by_cat"] = visible_by_cat

        def build_home(self):
            return ("EMBED_HOME", ["FILES_HOME"])

    monkeypatch.setattr(M, "HelpMenuView", FakeView)

    await M.send_help_menu(ctx, bot)

    # visible_by_cat attendu :
    # - Utils contient "a" (manual_save filtré)
    # - Autres contient "b" (non déclaré)
    assert created["visible_by_cat"] == {"Utils": ["a"], "Autres": ["b"]}

    # followup send embed/files/view
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

    cmd_ok = FakeCmd("ok", can_run=True)
    cmd_no = FakeCmd("no", can_run=False)
    cmd_boom = FakeCmd("boom", can_run=RuntimeError("fail"))

    bot = FakeBot([cmd_ok, cmd_no, cmd_boom])

    user = FakeUser(1, guild_permissions=FakePerms(0xFFFF))
    ctx = FakeCtx(user=user)

    created = {"visible_by_cat": None}

    class FakeView:
        def __init__(self, *, author_id, bot, cmd_map, help_infos, visible_by_cat, cat_descriptions):
            created["visible_by_cat"] = visible_by_cat

        def build_home(self):
            return ("E", ["F"])

    monkeypatch.setattr(M, "HelpMenuView", FakeView)

    await M.send_help_menu(ctx, bot)

    assert created["visible_by_cat"] == {"Cat": ["ok"]}