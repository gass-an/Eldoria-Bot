from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.common.embeds import images

# Important: injecte FakeEmbed/FakeFile dans le stub discord (installé par conftest)
from tests._fakes import _embed_fakes  # noqa: F401

# ---------------------------------------------------------------------------
# common_files
# ---------------------------------------------------------------------------

def test_common_files_returns_empty_when_both_urls_known():
    assert images.common_files("https://cdn/thumb.png", "https://cdn/banner.png") == []


@pytest.mark.parametrize(
    "thumb_url,banner_url",
    [
        (None, None),
        ("https://cdn/thumb.png", None),
        (None, "https://cdn/banner.png"),
        ("", "https://cdn/banner.png"),   # "" est falsy => considéré "inconnu"
        ("https://cdn/thumb.png", ""),    # "" est falsy => considéré "inconnu"
        ("", ""),                         # les deux falsy => "inconnus"
    ],
)
def test_common_files_returns_two_files_when_any_url_missing_or_falsy(thumb_url, banner_url):
    files = images.common_files(thumb_url, banner_url)
    assert len(files) == 2
    assert all(isinstance(f, discord.File) for f in files)


def test_common_files_uses_custom_paths_and_filenames():
    files = images.common_files(
        None,
        None,
        thumbnail_path="/tmp/t.png",
        banner_path="/tmp/b.png",
        thumbnail_filename="t_custom.png",
        banner_filename="b_custom.png",
    )
    assert len(files) == 2

    thumb, banner = files
    assert thumb.fp == "/tmp/t.png"
    assert thumb.filename == "t_custom.png"
    assert banner.fp == "/tmp/b.png"
    assert banner.filename == "b_custom.png"


# ---------------------------------------------------------------------------
# decorate
# ---------------------------------------------------------------------------

def test_decorate_reuses_cdn_urls_when_both_known():
    embed = discord.Embed(title="x")
    out = images.decorate(embed, "https://cdn/thumb.png", "https://cdn/banner.png")

    assert out is embed
    assert embed.thumbnail == {"url": "https://cdn/thumb.png"}
    assert embed.image == {"url": "https://cdn/banner.png"}


@pytest.mark.parametrize(
    "thumb_url,banner_url",
    [
        (None, None),
        ("https://cdn/thumb.png", None),
        (None, "https://cdn/banner.png"),
        ("", "https://cdn/banner.png"),
        ("https://cdn/thumb.png", ""),
        ("", ""),
    ],
)
def test_decorate_uses_attachments_when_any_url_missing_or_falsy(thumb_url, banner_url):
    embed = discord.Embed(title="x")
    out = images.decorate(embed, thumb_url, banner_url)

    assert out is embed
    assert embed.thumbnail == {"url": f"attachment://{images.DEFAULT_THUMBNAIL_FILENAME}"}
    assert embed.image == {"url": f"attachment://{images.DEFAULT_BANNER_FILENAME}"}


def test_decorate_uses_custom_attachment_filenames():
    embed = discord.Embed(title="x")
    out = images.decorate(
        embed,
        None,
        None,
        thumbnail_filename="thumb.png",
        banner_filename="banner.png",
    )

    assert out is embed
    assert embed.thumbnail == {"url": "attachment://thumb.png"}
    assert embed.image == {"url": "attachment://banner.png"}


# ---------------------------------------------------------------------------
# common_thumb
# ---------------------------------------------------------------------------

def test_common_thumb_returns_empty_when_thumb_url_known():
    assert images.common_thumb("https://cdn/thumb.png") == []


@pytest.mark.parametrize("thumb_url", [None, "", 0])  # 0 est falsy, testé volontairement
def test_common_thumb_returns_one_file_when_thumb_url_missing_or_falsy(thumb_url):
    files = images.common_thumb(thumb_url)
    assert len(files) == 1
    assert isinstance(files[0], discord.File)


def test_common_thumb_uses_custom_path_and_filename():
    files = images.common_thumb(None, thumbnail_path="/tmp/t.png", thumbnail_filename="t_custom.png")
    assert len(files) == 1
    f = files[0]
    assert f.fp == "/tmp/t.png"
    assert f.filename == "t_custom.png"


# ---------------------------------------------------------------------------
# decorate_thumb_only
# ---------------------------------------------------------------------------

def test_decorate_thumb_only_reuses_cdn_url_when_known():
    embed = discord.Embed(title="x")
    out = images.decorate_thumb_only(embed, "https://cdn/thumb.png")

    assert out is embed
    assert embed.thumbnail == {"url": "https://cdn/thumb.png"}


@pytest.mark.parametrize("thumb_url", [None, "", 0])
def test_decorate_thumb_only_uses_attachment_when_missing_or_falsy(thumb_url):
    embed = discord.Embed(title="x")
    out = images.decorate_thumb_only(embed, thumb_url)

    assert out is embed
    assert embed.thumbnail == {"url": f"attachment://{images.DEFAULT_THUMBNAIL_FILENAME}"}


def test_decorate_thumb_only_uses_custom_attachment_filename():
    embed = discord.Embed(title="x")
    out = images.decorate_thumb_only(embed, None, thumbnail_filename="thumb.png")

    assert out is embed
    assert embed.thumbnail == {"url": "attachment://thumb.png"}
