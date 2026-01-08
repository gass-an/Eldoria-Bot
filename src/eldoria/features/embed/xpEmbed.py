import discord
from discord.ext import commands

from ...db import gestionDB

async def generate_xp_status_embed(cfg: dict, guild_id: int, bot: commands.Bot):
    guild = bot.get_guild(guild_id)
    enabled = bool(cfg.get("enabled", False))
    
    embed = discord.Embed(
        title="Statut du système XP",
        description="Configuration actuelle du système d'expérience sur ce serveur.",
        colour=discord.Color.blurple()
    )

    if enabled :
        embed.add_field(
            name="État",
            value="✅ Activé",
            inline=False
        )
        embed.add_field(
            name="XP / message",
            value=str(cfg.get("points_per_message", 8)),
            inline=True
        )
        embed.add_field(
            name="Cooldown",
            value=f"{cfg.get('cooldown_seconds', 90)} secondes",
            inline=True
        )
        embed.add_field(
            name="Bonus Server Tag",
            value=f"+{cfg.get('bonus_percent', 20)}%",
            inline=True
        )
        embed.add_field(
            name="Malus Karuta (k<=10)",
            value=f"{cfg.get('karuta_k_small_percent', 30)}%",
            inline=True
        )
    
    else :
        embed.add_field(
            name="État",
            value="⛔ Désactivé",
            inline=True
        )
        embed.add_field(
        name="Information",
        value="Demandez à un administrateur d'utiliser `/xp_enable` pour activer le système.",
        inline=False
        )

    embed.set_footer(text=f"Serveur : {guild.name if guild else guild_id}")

    # Images (même pattern que les autres embeds)
    thumbnail_path = "./images/logo_Bot.png"
    thumbnail_file = discord.File(thumbnail_path, filename="logo_Bot.png")
    embed.set_thumbnail(url="attachment://logo_Bot.png")

    image_path = "./images/banner_Bot.png"
    image_file = discord.File(image_path, filename="banner_Bot.png")
    embed.set_image(url="attachment://banner_Bot.png")

    files = [thumbnail_file, image_file]
    return embed, files


async def generate_xp_disable_embed(guild_id: int, bot: commands.Bot):
    guild = bot.get_guild(guild_id)
    embed = discord.Embed(
        title="Statut du système XP",
        description="Configuration actuelle du système d'expérience sur ce serveur.",
        colour=discord.Color.blurple()
    )

    embed.add_field(
            name="État",
            value="⛔ Désactivé",
            inline=True
    )
    embed.add_field(
        name="Information",
        value="Demandez à un administrateur d'utiliser `/xp_enable` pour activer le système.",
        inline=False
    )

    embed.set_footer(text=f"Serveur : {guild.name if guild else guild_id}")

    # Images (même pattern que les autres embeds)
    thumbnail_path = "./images/logo_Bot.png"
    thumbnail_file = discord.File(thumbnail_path, filename="logo_Bot.png")
    embed.set_thumbnail(url="attachment://logo_Bot.png")

    image_path = "./images/banner_Bot.png"
    image_file = discord.File(image_path, filename="banner_Bot.png")
    embed.set_image(url="attachment://banner_Bot.png")

    files = [thumbnail_file, image_file]
    return embed, files


async def generate_list_xp_embed(items, current_page: int, total_pages: int, guild_id: int, bot: commands.Bot):
    """Génère l'embed du classement XP.

    `items` peut être au format :
      - list[(user_id, xp, level)]
      - list[(user_id, xp, level, lvl_label)]  # si le label est pré-calculé côté commande
    """

    embed = discord.Embed(
        title="Classement XP",
        description="Liste des membres et de leurs XP.",
        colour=discord.Color(0x00FFFF),
    )

    guild = bot.get_guild(guild_id)

    # Récupère le mapping {level: role_id} depuis la DB (indépendant du nom)
    role_ids = gestionDB.xp_get_role_ids(guild_id) if guild_id else {}

    def level_label(level: int) -> str:
        if guild:
            rid = role_ids.get(int(level))
            role = guild.get_role(rid) if rid else None
            if role:
                return role.mention
        return f"lvl{level}"

    if not items:
        embed.add_field(name="Aucun membre", value="Personne n'a encore gagné d'XP.", inline=False)
    else:
        lines = []
        rank_start = current_page * 10 + 1
        for idx, item in enumerate(items, start=rank_start):
            # Compat: on accepte les tuples de taille 3 (ancien) ou 4 (avec label)
            if len(item) == 4:
                user_id, xp, level, lvl_txt = item
            else:
                user_id, xp, level = item
                lvl_txt = level_label(level)

            member = guild.get_member(user_id) if guild else None
            name = member.display_name if member else f"ID {user_id}"
            lines.append(f"**{idx}.** {name} — {lvl_txt} — **{xp} XP**")

        embed.add_field(name="Membres", value="\n".join(lines), inline=False)

    embed.set_footer(text=f"Page {current_page + 1}/{total_pages}")

    thumbnail_path = "./images/logo_Bot.png"
    thumbnail_file = discord.File(thumbnail_path, filename="logo_Bot.png")
    embed.set_thumbnail(url="attachment://logo_Bot.png")

    image_path = "./images/banner_Bot.png"
    image_file = discord.File(image_path, filename="banner_Bot.png")
    embed.set_image(url="attachment://banner_Bot.png")

    files = [thumbnail_file, image_file]
    return embed, files

async def generate_xp_profile_embed(
    *,
    guild_id: int,
    user: discord.User | discord.Member,
    xp: int,
    level: int,
    level_label: str,
    next_level_label: str | None,
    next_xp_required: int | None,
    bot: commands.Bot,
    ):
    
    guild = bot.get_guild(guild_id)

    embed = discord.Embed(
        title="📊 Ton profil XP",
        colour=discord.Color.blurple()
    )

    embed.set_author(
        name=str(user),
        icon_url=user.display_avatar.url if user.display_avatar else None
    )

    embed.add_field(
        name="Niveau actuel",
        value=f"**{level_label}** (niveau {level})",
        inline=True
    )

    embed.add_field(
        name="XP total",
        value=f"**{xp} XP**",
        inline=True
    )

    if next_xp_required is None:
        embed.add_field(
            name="Progression",
            value="🏆 **Niveau maximum atteint !**",
            inline=False
        )
    else:
        remaining = max(next_xp_required - xp, 0)
        embed.add_field(
            name="Prochain niveau",
            value=(
                f"**{next_level_label}**\n"
                f"Seuil : **{next_xp_required} XP**\n"
                f"XP restante : **{remaining} XP**"
            ),
            inline=False
        )

    embed.set_footer(text=f"Serveur : {guild.name if guild else guild_id}")

    # Images (même pattern que les autres embeds)
    thumbnail_path = "./images/logo_Bot.png"
    thumbnail_file = discord.File(thumbnail_path, filename="logo_Bot.png")
    embed.set_thumbnail(url="attachment://logo_Bot.png")

    image_path = "./images/banner_Bot.png"
    image_file = discord.File(image_path, filename="banner_Bot.png")
    embed.set_image(url="attachment://banner_Bot.png")

    files = [thumbnail_file, image_file]
    return embed, files


async def generate_xp_roles_embed(levels_with_roles, guild_id: int, bot: commands.Bot):
    """Crée un embed listant les rôles liés aux niveaux et l'XP nécessaire.

    Paramètre attendu:
      levels_with_roles: list[(level:int, xp_required:int, role_id:int|None)]
    """
    embed = discord.Embed(
        title="Rôles & Niveaux XP",
        description="XP requis pour atteindre chaque rôle de niveau.",
        colour=discord.Color(0x00FFFF),
    )

    guild = bot.get_guild(guild_id) if guild_id else None

    lines = []
    for level, xp_required, role_id in levels_with_roles or []:
        role = guild.get_role(role_id) if (guild and role_id) else None
        role_txt = role.mention if role else f"lvl{level}"
        lines.append(f"**Niveau {level}** — {role_txt} — **{xp_required} XP**")

    if not lines:
        embed.add_field(name="Aucune configuration", value="Aucun niveau n'est configuré pour ce serveur.", inline=False)
    else:
        embed.add_field(name="Niveaux", value="\n".join(lines), inline=False)

    thumbnail_path = "./images/logo_Bot.png"
    thumbnail_file = discord.File(thumbnail_path, filename="logo_Bot.png")
    embed.set_thumbnail(url="attachment://logo_Bot.png")

    image_path = "./images/banner_Bot.png"
    image_file = discord.File(image_path, filename="banner_Bot.png")
    embed.set_image(url="attachment://banner_Bot.png")

    files = [thumbnail_file, image_file]
    return embed, files
