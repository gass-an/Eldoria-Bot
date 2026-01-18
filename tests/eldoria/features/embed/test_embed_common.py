from tests._embed_fakes import FakeEmbed  # noqa: F401 (active stubs discord)

import discord  # type: ignore


def test_embed_colour_primary_constant():
    from eldoria.features.embed.common.embedColors import EMBED_COLOUR_PRIMARY

    assert int(EMBED_COLOUR_PRIMARY) == 0x3FA7C4


def test_common_files_returns_empty_when_urls_present():
    from eldoria.features.embed.common.embedImages import common_files

    assert common_files("https://cdn/thumb.png", "https://cdn/banner.png") == []


def test_common_files_returns_two_files_when_urls_missing():
    from eldoria.features.embed.common.embedImages import common_files

    files = common_files(None, None)
    assert len(files) == 2
    assert files[0].filename == "logo_bot.png"
    assert files[1].filename == "banner_bot.png"


def test_decorate_uses_cdn_urls_when_present():
    from eldoria.features.embed.common.embedImages import decorate

    e = discord.Embed(title="t")
    decorate(e, "https://cdn/thumb.png", "https://cdn/banner.png")

    assert e.thumbnail == {"url": "https://cdn/thumb.png"}
    assert e.image == {"url": "https://cdn/banner.png"}


def test_decorate_uses_attachment_urls_when_missing():
    from eldoria.features.embed.common.embedImages import decorate

    e = discord.Embed(title="t")
    decorate(e, None, None)

    assert e.thumbnail == {"url": "attachment://logo_bot.png"}
    assert e.image == {"url": "attachment://banner_bot.png"}
