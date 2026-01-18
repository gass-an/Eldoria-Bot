from tests._embed_fakes import FakeEmbed  # noqa: F401 (active stubs discord)

from eldoria.features.embed.helpEmbed import build_home_embed, build_category_embed


def test_build_home_embed_fields_and_footer():
    visible_by_cat = {"Utilitaires": ["ping"], "Moderation": ["ban", "kick"]}
    cat_descriptions = {"Utilitaires": "Commandes utiles"}

    embed = build_home_embed(visible_by_cat, cat_descriptions, None, None)

    assert embed.title == "Centre d'aide"
    assert "Choisis une fonctionnalité" in (embed.description or "")

    assert [f["name"] for f in embed.fields] == ["Utilitaires", "Moderation"]
    assert embed.fields[0]["value"] == "> Commandes utiles"
    assert embed.fields[1]["value"] == "> Fonctionnalité du bot."

    assert embed.footer == {
        "text": "Utilise les boutons pour naviguer. (Peut prendre plusieurs secondes)"
    }
    assert embed.thumbnail == {"url": "attachment://logo_Bot.png"}
    assert embed.image == {"url": "attachment://banner_Bot.png"}


def test_build_category_embed_description_resolution_order():
    class CmdObj:
        description = "Desc depuis cmd_map"

    embed = build_category_embed(
        "Utilitaires",
        cmds=["ping", "pong", "nope"],
        help_infos={"ping": "Desc ping"},
        cmd_map={"pong": CmdObj()},
        thumb_url="https://cdn/thumb.png",
        banner_url="https://cdn/banner.png",
    )

    assert embed.title == "Aide • Utilitaires"
    assert embed.fields[0]["name"] == "▸ /ping"
    assert embed.fields[0]["value"] == "> Desc ping"

    assert embed.fields[1]["name"] == "▸ /pong"
    assert embed.fields[1]["value"] == "> Desc depuis cmd_map"

    assert embed.fields[2]["name"] == "▸ /nope"
    assert embed.fields[2]["value"] == "> (Aucune description disponible.)"

    assert embed.thumbnail == {"url": "https://cdn/thumb.png"}
    assert embed.image == {"url": "https://cdn/banner.png"}
