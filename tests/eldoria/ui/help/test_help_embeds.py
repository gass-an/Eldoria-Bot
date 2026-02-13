from __future__ import annotations

import discord  # type: ignore
import pytest

from eldoria.ui.help import embeds as M


class FakeCmd:
    def __init__(self, description: str | None):
        self.description = description


def test_build_home_embed_builds_fields_footer_and_calls_decorate(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 123)

    called: dict = {"args": None}

    def fake_decorate(embed, thumb_url, banner_url):
        called["args"] = (embed, thumb_url, banner_url)
        return embed

    monkeypatch.setattr(M, "decorate", fake_decorate)

    visible_by_cat = {
        "XP": ["xp_rank", "xp_top"],
        "Duels": ["duel"],
    }
    cat_descriptions = {
        "XP": "Système d'expérience",
        # "Duels" manquant => fallback
    }

    embed = M.build_home_embed(
        visible_by_cat=visible_by_cat,
        cat_descriptions=cat_descriptions,
        thumb_url="T",
        banner_url="B",
    )

    assert isinstance(embed, discord.Embed)
    assert embed.title == "Centre d'aide"
    assert "Choisis une fonctionnalité" in embed.description
    assert embed.colour == 123

    assert len(embed.fields) == 2
    assert embed.fields[0] == {"name": "XP", "value": "> Système d'expérience", "inline": False}
    assert embed.fields[1] == {"name": "Duels", "value": "> Fonctionnalité du bot.", "inline": False}

    assert embed.footer == {"text": "Utilise les boutons pour naviguer. (Peut prendre plusieurs secondes)"}

    # decorate called with exact thumb/banner
    assert called["args"][0] is embed
    assert called["args"][1] == "T"
    assert called["args"][2] == "B"


@pytest.mark.parametrize(
    "desc_in_help, cmd_obj_desc, expected",
    [
        ("Texte help_infos", "Desc cmd", "Texte help_infos"),  # help_infos prioritaire
        (None, "Desc cmd", "Desc cmd"),                        # fallback sur cmd.description
        (None, None, "(Aucune description disponible.)"),      # fallback final
    ],
)
def test_build_category_embed_description_fallbacks(monkeypatch, desc_in_help, cmd_obj_desc, expected):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 999)

    called: dict = {"args": None}

    def fake_decorate(embed, thumb_url, banner_url):
        called["args"] = (embed, thumb_url, banner_url)
        return embed

    monkeypatch.setattr(M, "decorate", fake_decorate)

    cmds = ["ping"]
    help_infos = {}
    if desc_in_help is not None:
        help_infos["ping"] = desc_in_help

    cmd_map = {"ping": FakeCmd(cmd_obj_desc)}

    embed = M.build_category_embed(
        cat="Utils",
        cmds=cmds,
        help_infos=help_infos,
        cmd_map=cmd_map,
        thumb_url="TH",
        banner_url="BA",
    )

    assert isinstance(embed, discord.Embed)
    assert embed.title == "Aide • Utils"
    assert embed.description == "Commandes disponibles :"
    assert embed.colour == 999

    assert len(embed.fields) == 1
    assert embed.fields[0]["name"] == "▸ /ping"
    assert embed.fields[0]["value"] == f"> {expected}"
    assert embed.fields[0]["inline"] is False

    assert embed.footer == {"text": "Utilise les boutons pour naviguer. (Peut prendre plusieurs secondes)"}

    assert called["args"][0] is embed
    assert called["args"][1] == "TH"
    assert called["args"][2] == "BA"


def test_build_category_embed_multiple_cmds_keeps_order(monkeypatch):
    monkeypatch.setattr(M, "EMBED_COLOUR_PRIMARY", 1)
    monkeypatch.setattr(M, "decorate", lambda embed, t, b: embed)

    cmds = ["a", "b", "c"]
    help_infos = {"b": "B desc"}
    cmd_map = {"a": FakeCmd("A desc"), "b": FakeCmd("ignored"), "c": FakeCmd(None)}

    embed = M.build_category_embed(
        cat="Cat",
        cmds=cmds,
        help_infos=help_infos,
        cmd_map=cmd_map,
    )

    assert [f["name"] for f in embed.fields] == ["▸ /a", "▸ /b", "▸ /c"]
    assert embed.fields[0]["value"] == "> A desc"
    assert embed.fields[1]["value"] == "> B desc"  # help_infos prioritaire
    assert embed.fields[2]["value"] == "> (Aucune description disponible.)"
