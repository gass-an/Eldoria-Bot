import pytest

from tests._pages_fakes import (
    FakeAttachment,
    FakeInteraction,
    FakeMessage,
    FakeUser,
)  # noqa: F401 installs discord.ui stubs


@pytest.mark.asyncio
async def test_help_menu_refresh_nav_buttons_styles_and_disabled(monkeypatch):
    # Stub helpEmbed used by HelpMenuView
    import eldoria.pages.helpMenu as mod

    class _HE:
        @staticmethod
        def common_files(a, b):
            return []

        @staticmethod
        def decorate(e, a, b):
            return None

        @staticmethod
        def build_home_embed(*, visible_by_cat, cat_descriptions, thumb_url, banner_url):
            return "HOME_EMBED"

        @staticmethod
        def build_category_embed(*, cat, cmds, help_infos, cmd_map, thumb_url, banner_url):
            return f"CAT_{cat}"

    monkeypatch.setattr(mod, "helpEmbed", _HE)

    view = mod.HelpMenuView(
        author_id=1,
        bot=None,
        cmd_map={},
        help_infos={},
        visible_by_cat={"A": ["x"], "B": ["y"]},
        cat_descriptions={"A": "desc"},
    )

    # initial: home active/disabled, cats default and enabled
    assert view.current is None
    assert view.home_button.disabled is True
    assert view._cat_buttons["A"].disabled is False
    assert view._cat_buttons["B"].disabled is False

    # switch to category
    view.current = "A"
    view._refresh_nav_buttons()
    assert view.home_button.disabled is False
    assert view._cat_buttons["A"].disabled is True
    assert view._cat_buttons["B"].disabled is False


@pytest.mark.asyncio
async def test_help_menu_capture_attachment_urls_from_message(monkeypatch):
    import eldoria.pages.helpMenu as mod

    # stub helpEmbed (not used directly here)
    class _HE:
        @staticmethod
        def common_files(a, b):
            return []

        @staticmethod
        def decorate(e, a, b):
            return None

        @staticmethod
        def build_home_embed(**kwargs):
            return "HOME"

        @staticmethod
        def build_category_embed(**kwargs):
            return "CAT"

    monkeypatch.setattr(mod, "helpEmbed", _HE)

    view = mod.HelpMenuView(
        author_id=1,
        bot=None,
        cmd_map={},
        help_infos={},
        visible_by_cat={"A": ["x"]},
        cat_descriptions={},
    )

    msg = FakeMessage(
        attachments=[
            FakeAttachment(filename="logo_Bot.png", url="https://cdn/logo.png"),
            FakeAttachment(filename="banner_Bot.png", url="https://cdn/banner.png"),
        ]
    )
    inter = FakeInteraction(user=FakeUser(1), message=msg)

    view._capture_attachment_urls_from_message(inter)
    assert view._thumb_url == "https://cdn/logo.png"
    assert view._banner_url == "https://cdn/banner.png"


@pytest.mark.asyncio
async def test_help_menu_interaction_check_blocks_other_user(monkeypatch):
    import eldoria.pages.helpMenu as mod
    import discord  # type: ignore

    # stub helpEmbed
    class _HE:
        @staticmethod
        def common_files(a, b):
            return []
        @staticmethod
        def decorate(e, a, b):
            return None
        @staticmethod
        def build_home_embed(**kwargs):
            return "HOME"
        @staticmethod
        def build_category_embed(**kwargs):
            return "CAT"

    monkeypatch.setattr(mod, "helpEmbed", _HE)

    view = mod.HelpMenuView(
        author_id=999,
        bot=None,
        cmd_map={},
        help_infos={},
        visible_by_cat={"A": ["x"]},
        cat_descriptions={},
    )

    inter = FakeInteraction(user=FakeUser(1), message=None)
    ok = await view.interaction_check(inter)
    assert ok is False
    assert inter.response.sent[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_help_menu_interaction_check_fallback_followup_when_already_responded(monkeypatch):
    import eldoria.pages.helpMenu as mod
    import discord  # type: ignore

    class _HE:
        @staticmethod
        def common_files(a, b):
            return []
        @staticmethod
        def decorate(e, a, b):
            return None
        @staticmethod
        def build_home_embed(**kwargs):
            return "HOME"
        @staticmethod
        def build_category_embed(**kwargs):
            return "CAT"

    monkeypatch.setattr(mod, "helpEmbed", _HE)

    view = mod.HelpMenuView(
        author_id=999,
        bot=None,
        cmd_map={},
        help_infos={},
        visible_by_cat={"A": ["x"]},
        cat_descriptions={},
    )

    inter = FakeInteraction(user=FakeUser(1), message=None)
    inter.response.raise_on_send = discord.InteractionResponded  # simulate "already responded"

    ok = await view.interaction_check(inter)
    assert ok is False
    assert inter.followup.sent
    assert inter.followup.sent[-1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_help_menu_safe_edit_fast_path_when_urls_present(monkeypatch):
    import eldoria.pages.helpMenu as mod

    class _HE:
        @staticmethod
        def common_files(a, b):
            return []
        @staticmethod
        def decorate(e, a, b):
            return None
        @staticmethod
        def build_home_embed(**kwargs):
            return "HOME"
        @staticmethod
        def build_category_embed(**kwargs):
            return "CAT"

    monkeypatch.setattr(mod, "helpEmbed", _HE)

    view = mod.HelpMenuView(
        author_id=1,
        bot=None,
        cmd_map={},
        help_infos={},
        visible_by_cat={"A": ["x"]},
        cat_descriptions={},
    )

    # Already have URLs -> fast_no_files -> response.edit_message
    view._thumb_url = "https://cdn/logo"
    view._banner_url = "https://cdn/banner"

    inter = FakeInteraction(user=FakeUser(1), message=None)
    await view._safe_edit(inter, embed="E", files=["F"])

    assert inter.response.edits
    assert not inter.original_edits  # returned early


@pytest.mark.asyncio
async def test_help_menu_safe_edit_defer_then_edit_with_files(monkeypatch):
    import eldoria.pages.helpMenu as mod

    class _HE:
        @staticmethod
        def common_files(a, b):
            return ["FILES"]
        @staticmethod
        def decorate(e, a, b):
            return None
        @staticmethod
        def build_home_embed(**kwargs):
            return "HOME"
        @staticmethod
        def build_category_embed(**kwargs):
            return "CAT"

    monkeypatch.setattr(mod, "helpEmbed", _HE)

    view = mod.HelpMenuView(
        author_id=1,
        bot=None,
        cmd_map={},
        help_infos={},
        visible_by_cat={"A": ["x"]},
        cat_descriptions={},
    )

    # No URLs -> should defer then edit_original_response with files
    inter = FakeInteraction(user=FakeUser(1), message=None)
    await view._safe_edit(inter, embed="E", files=["F1", "F2"])

    assert inter.response.deferred is True
    assert inter.original_edits
    assert inter.original_edits[-1]["files"] == ["F1", "F2"]
