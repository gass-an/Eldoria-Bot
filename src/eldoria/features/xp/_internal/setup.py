import discord
from eldoria.db.repo.xp_repo import xp_ensure_defaults, xp_get_role_ids, xp_upsert_role_id
from eldoria.defaults import XP_LEVELS_DEFAULTS


async def ensure_guild_xp_setup(guild: discord.Guild) -> None:
    """Crée la config + niveaux par défaut + rôles level5..level1 (si absents),
    sans jamais toucher aux positions (création uniquement).
    """
    xp_ensure_defaults(guild.id, XP_LEVELS_DEFAULTS)

    role_ids = xp_get_role_ids(guild.id)
    roles_by_id = {r.id: r for r in guild.roles}

    # On crée du plus haut niveau au plus bas : level5 → level1
    for lvl in range(5, 0, -1):
        role: discord.Role | None = None

        # 1) Priorité : role_id déjà connu en DB
        rid = role_ids.get(lvl)
        if rid:
            role = roles_by_id.get(rid)

        # 2) Fallback anti-doublons si DB reset : retrouver par nom
        if role is None:
            role = discord.utils.get(guild.roles, name=f"level{lvl}")

        # 3) Créer si vraiment absent (sans déplacer)
        if role is None:
            try:
                role = await guild.create_role(
                    name=f"level{lvl}",
                    reason="Initialisation des rôles XP",
                )
            except discord.Forbidden:
                # pas la permission de créer des rôles → on arrête sans casser
                return

        # 4) Stocker/mettre à jour en DB
        xp_upsert_role_id(guild.id, lvl, role.id)
