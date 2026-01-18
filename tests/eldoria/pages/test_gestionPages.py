import pytest

from tests._pages_fakes import FakeInteraction, FakeUser  # noqa: F401


@pytest.mark.asyncio
async def test_paginator_init_buttons_and_total_pages():
    from eldoria.pages.gestionPages import Paginator

    items = list(range(21))  # page_size=10 -> ceil = 3

    async def embed_gen(page_items, current_page, total_pages, identifiant, bot):
        return ("EMBED", ["FILES"])

    view = Paginator(items, embed_generator=embed_gen, identifiant_for_embed=123, bot="BOT")

    assert view.page_size == 10
    assert view.current_page == 0
    assert view.total_pages == 3

    assert view.previous_button.label == "Précédent"
    assert view.previous_button.disabled is True
    assert view.next_button.label == "Suivant"
    assert view.next_button.disabled is False


@pytest.mark.asyncio
async def test_paginator_create_embed_calls_generator_with_first_page():
    from eldoria.pages.gestionPages import Paginator

    items = list(range(25))
    calls = []

    async def embed_gen(page_items, current_page, total_pages, identifiant, bot):
        calls.append((page_items, current_page, total_pages, identifiant, bot))
        return ("EMBED0", ["F0"])

    view = Paginator(items, embed_generator=embed_gen, identifiant_for_embed=77, bot="B")
    embed, files = await view.create_embed()

    assert embed == "EMBED0"
    assert files == ["F0"]
    assert calls == [(items[:10], 0, 3, 77, "B")]


@pytest.mark.asyncio
async def test_paginator_update_embed_slices_items_and_disables_buttons():
    from eldoria.pages.gestionPages import Paginator

    items = list(range(25))
    calls = []

    async def embed_gen(page_items, current_page, total_pages, identifiant, bot):
        calls.append((list(page_items), current_page, total_pages))
        return (f"EMBED{current_page}", [])

    view = Paginator(items, embed_generator=embed_gen, identifiant_for_embed=1, bot=None)
    view.current_page = 1  # second page

    inter = FakeInteraction(user=FakeUser(1), message=None)
    await view.update_embed(inter)

    # second page slice
    assert calls == [(items[10:20], 1, 3)]

    # buttons state in middle
    assert view.previous_button.disabled is False
    assert view.next_button.disabled is False

    # edited via interaction.response.edit_message
    assert inter.response.edits
    assert inter.response.edits[-1]["embed"] == "EMBED1"
    assert inter.response.edits[-1]["view"] is view


@pytest.mark.asyncio
async def test_paginator_next_and_previous_page_changes_current_page():
    from eldoria.pages.gestionPages import Paginator

    items = list(range(25))

    async def embed_gen(page_items, current_page, total_pages, identifiant, bot):
        return ("E", [])

    view = Paginator(items, embed_generator=embed_gen)

    inter = FakeInteraction(user=FakeUser(1), message=None)

    # next -> page 1
    await view.next_page(inter)
    assert view.current_page == 1

    # previous -> page 0
    await view.previous_page(inter)
    assert view.current_page == 0

    # previous at 0 stays 0
    await view.previous_page(inter)
    assert view.current_page == 0
