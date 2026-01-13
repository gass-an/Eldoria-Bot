import discord

def common_files(thumb_url: str | None, banner_url: str | None):
    """Return attachment files for help embeds.

    To keep navigation snappy, images are only attached on the first message.
    If CDN URLs are already known, return an empty list.
    """
    if thumb_url and banner_url:
        return []

    thumbnail_path = "./images/logo_Bot.png"
    banner_path = "./images/banner_Bot.png"
    thumbnail_file = discord.File(thumbnail_path, filename="logo_Bot.png")
    banner_file = discord.File(banner_path, filename="banner_Bot.png")
    return [thumbnail_file, banner_file]


def decorate(embed: discord.Embed, thumb_url: str | None, banner_url: str | None) -> discord.Embed:
    """Apply thumbnail/banner to the embed.

    - If URLs are known (after first send), reuse CDN URLs.
    - Else reference message attachments.
    """
    if thumb_url and banner_url:
        embed.set_thumbnail(url=thumb_url)
        embed.set_image(url=banner_url)
    else:
        embed.set_thumbnail(url="attachment://logo_Bot.png")
        embed.set_image(url="attachment://banner_Bot.png")
    return embed


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
        colour=discord.Color(0x00FFFF),
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
        colour=discord.Color(0x00FFFF),
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
