import discord

from .common.embedImages import common_files, decorate
from .common.embedColors import EMBED_COLOUR_PRIMARY

def build_home_embed(
    visible_by_cat: dict[str, list[str]],
    cat_descriptions: dict[str, str],
    thumb_url: str | None = None,
    banner_url: str | None = None,
):
    """Build the help home page embed."""
    embed = discord.Embed(
        title="Centre d'aide",
        description="Choisis une fonctionnalité ci-dessous pour voir les détails.\n",
        colour=EMBED_COLOUR_PRIMARY,
    )

    for cat, _cmds in visible_by_cat.items():
        desc = cat_descriptions.get(cat, "Fonctionnalité du bot.")
        embed.add_field(name=cat, value=f"> {desc}", inline=False)

    embed.set_footer(text="Utilise les boutons pour naviguer. (Peut prendre plusieurs secondes)")
    decorate(embed, thumb_url, banner_url)
    return embed


def build_category_embed(
    cat: str,
    cmds: list[str],
    help_infos: dict[str, str],
    cmd_map: dict[str, object],
    thumb_url: str | None = None,
    banner_url: str | None = None,
):
    """Build a category page embed."""
    embed = discord.Embed(
        title=f"Aide • {cat}",
        description="Commandes disponibles :",
        colour=EMBED_COLOUR_PRIMARY,
    )

    for cmd_name in cmds:
        cmd = cmd_map.get(cmd_name)
        desc = help_infos.get(cmd_name)
        if not desc and cmd is not None:
            desc = getattr(cmd, "description", None)
        if not desc:
            desc = "(Aucune description disponible.)"

        embed.add_field(name=f"▸ /{cmd_name}", value=f"> {desc}", inline=False)

    embed.set_footer(text="Utilise les boutons pour naviguer. (Peut prendre plusieurs secondes)")
    decorate(embed, thumb_url, banner_url)
    return embed
