from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.common import pagination as M
from tests._fakes._pages_fakes import FakeInteraction, FakeUser


def _mk_items(n: int) -> list[int]:
    return list(range(n))


def _mk_interaction() -> FakeInteraction:
    return FakeInteraction(user=FakeUser(42))


def _mk_async_generator(calls: list[dict], *, files=None):
    async def gen(page_items, page_index, total_pages, ident, bot):
        calls.append(
            {
                "page_items": list(page_items),
                "page_index": page_index,
                "total_pages": total_pages,
                "ident": ident,
                "bot": bot,
            }
        )
        # Embed fake via stub
        return discord.Embed(title=f"p{page_index}"), files
    return gen


# ---------------------------------------------------------------------------
# __init__ : boutons, paging, total_pages
# ---------------------------------------------------------------------------

def test_init_sets_buttons_and_paging_defaults():
    items = _mk_items(25)  # 25 items, page_size=10 => 3 pages
    calls: list[dict] = []
    gen = _mk_async_generator(calls)

    p = M.Paginator(items, embed_generator=gen, identifiant_for_embed=123, bot="bot")

    assert p.items is items
    assert p.page_size == 10
    assert p.current_page == 0
    assert p.total_pages == 3

    # Boutons
    assert p.previous_button.label == "Précédent"
    assert p.next_button.label == "Suivant"
    assert p.previous_button.disabled is True  # initialement désactivé
    assert p.next_button.disabled is False

    # Callbacks bien branchés
    assert p.previous_button.callback == p.previous_page
    assert p.next_button.callback == p.next_page

    # Les boutons ont été add_item dans la View
    assert p.previous_button in p.children
    assert p.next_button in p.children


def test_total_pages_empty_items_is_zero():
    items: list[int] = []
    calls: list[dict] = []
    gen = _mk_async_generator(calls)

    p = M.Paginator(items, embed_generator=gen)
    assert p.total_pages == 0


# ---------------------------------------------------------------------------
# create_embed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_embed_calls_generator_with_first_slice_and_returns_files():
    items = _mk_items(13)  # first slice size 10
    calls: list[dict] = []
    files = [discord.File("/tmp/a.png", filename="a.png")]
    gen = _mk_async_generator(calls, files=files)

    p = M.Paginator(items, embed_generator=gen, identifiant_for_embed="id", bot="botty")

    embed, out_files = await p.create_embed()

    assert isinstance(embed, discord.Embed)
    assert out_files == files

    assert calls == [
        {
            "page_items": items[:10],
            "page_index": 0,
            "total_pages": 2,
            "ident": "id",
            "bot": "botty",
        }
    ]


@pytest.mark.asyncio
async def test_create_embed_with_empty_items_calls_generator_with_empty_page():
    items: list[int] = []
    calls: list[dict] = []
    gen = _mk_async_generator(calls, files=None)

    p = M.Paginator(items, embed_generator=gen)

    embed, out_files = await p.create_embed()

    assert isinstance(embed, discord.Embed)
    assert out_files is None
    assert calls[0]["page_items"] == []
    assert calls[0]["page_index"] == 0
    assert calls[0]["total_pages"] == 0


@pytest.mark.asyncio
async def test_create_embed_raises_when_embed_generator_is_none():
    p = M.Paginator(_mk_items(5), embed_generator=None)
    with pytest.raises(TypeError):
        await p.create_embed()


# ---------------------------------------------------------------------------
# update_embed : slice + disabled toggles + edit_message called
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_embed_first_page_disables_prev_and_enables_next_when_multiple_pages():
    items = _mk_items(25)  # 3 pages
    calls: list[dict] = []
    gen = _mk_async_generator(calls)

    p = M.Paginator(items, embed_generator=gen)
    inter = _mk_interaction()

    p.current_page = 0
    await p.update_embed(inter)

    # slice page 0 => 0..9
    assert calls[-1]["page_items"] == items[0:10]
    assert calls[-1]["page_index"] == 0
    assert calls[-1]["total_pages"] == 3

    assert p.previous_button.disabled is True
    assert p.next_button.disabled is False

    # edit_message appelé
    assert inter.response.edits
    last_edit = inter.response.edits[-1]
    assert isinstance(last_edit["embed"], discord.Embed)
    assert last_edit["view"] is p


@pytest.mark.asyncio
async def test_update_embed_middle_page_enables_both_buttons():
    items = _mk_items(25)  # 3 pages
    calls: list[dict] = []
    gen = _mk_async_generator(calls)

    p = M.Paginator(items, embed_generator=gen)
    inter = _mk_interaction()

    p.current_page = 1
    await p.update_embed(inter)

    assert calls[-1]["page_items"] == items[10:20]
    assert p.previous_button.disabled is False
    assert p.next_button.disabled is False


@pytest.mark.asyncio
async def test_update_embed_last_page_disables_next():
    items = _mk_items(25)  # 3 pages => last page index 2
    calls: list[dict] = []
    gen = _mk_async_generator(calls)

    p = M.Paginator(items, embed_generator=gen)
    inter = _mk_interaction()

    p.current_page = 2
    await p.update_embed(inter)

    assert calls[-1]["page_items"] == items[20:30]  # fin tronquée
    assert p.previous_button.disabled is False
    assert p.next_button.disabled is True


@pytest.mark.asyncio
async def test_update_embed_one_page_disables_both_after_update():
    items = _mk_items(7)  # total_pages=1
    calls: list[dict] = []
    gen = _mk_async_generator(calls)

    p = M.Paginator(items, embed_generator=gen)
    inter = _mk_interaction()

    await p.update_embed(inter)

    assert calls[-1]["page_items"] == items[0:10]
    assert p.previous_button.disabled is True
    assert p.next_button.disabled is True  # current_page(0) >= total_pages-1(0)


@pytest.mark.asyncio
async def test_update_embed_empty_items_disables_next_and_prev_and_calls_generator():
    items: list[int] = []
    calls: list[dict] = []
    gen = _mk_async_generator(calls)

    p = M.Paginator(items, embed_generator=gen)
    inter = _mk_interaction()

    await p.update_embed(inter)

    assert calls[-1]["page_items"] == []
    assert calls[-1]["page_index"] == 0
    assert calls[-1]["total_pages"] == 0

    assert p.previous_button.disabled is True
    assert p.next_button.disabled is True  # 0 >= -1 => True
    assert inter.response.edits


@pytest.mark.asyncio
async def test_update_embed_raises_when_embed_generator_is_none():
    p = M.Paginator(_mk_items(5), embed_generator=None)
    inter = _mk_interaction()
    with pytest.raises(TypeError):
        await p.update_embed(inter)


# ---------------------------------------------------------------------------
# previous_page / next_page : limites + update appelé
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_previous_page_decrements_when_possible_and_updates():
    items = _mk_items(25)  # 3 pages
    calls: list[dict] = []
    gen = _mk_async_generator(calls)

    p = M.Paginator(items, embed_generator=gen)
    inter = _mk_interaction()

    p.current_page = 2
    await p.previous_page(inter)

    assert p.current_page == 1
    assert calls[-1]["page_index"] == 1
    assert inter.response.edits


@pytest.mark.asyncio
async def test_previous_page_at_zero_does_not_go_negative_but_updates():
    items = _mk_items(25)
    calls: list[dict] = []
    gen = _mk_async_generator(calls)

    p = M.Paginator(items, embed_generator=gen)
    inter = _mk_interaction()

    p.current_page = 0
    await p.previous_page(inter)

    assert p.current_page == 0
    assert calls[-1]["page_index"] == 0
    assert inter.response.edits


@pytest.mark.asyncio
async def test_next_page_increments_when_possible_and_updates():
    items = _mk_items(25)  # 3 pages
    calls: list[dict] = []
    gen = _mk_async_generator(calls)

    p = M.Paginator(items, embed_generator=gen)
    inter = _mk_interaction()

    p.current_page = 0
    await p.next_page(inter)

    assert p.current_page == 1
    assert calls[-1]["page_index"] == 1
    assert inter.response.edits


@pytest.mark.asyncio
async def test_next_page_at_last_does_not_exceed_but_updates():
    items = _mk_items(25)  # 3 pages => last index 2
    calls: list[dict] = []
    gen = _mk_async_generator(calls)

    p = M.Paginator(items, embed_generator=gen)
    inter = _mk_interaction()

    p.current_page = 2
    await p.next_page(inter)

    assert p.current_page == 2
    assert calls[-1]["page_index"] == 2
    assert inter.response.edits
