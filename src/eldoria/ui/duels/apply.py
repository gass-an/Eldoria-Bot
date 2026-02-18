"""Module pour appliquer un snapshot de duel sur le message courant."""

from __future__ import annotations

import discord

from eldoria.app.bot import EldoriaBot
from eldoria.utils.mentions import level_mention


async def apply_duel_snapshot(
    *,
    interaction: discord.Interaction,
    snapshot: dict,
    bot: EldoriaBot,
) -> None:
    """Applique un snapshot sur le message courant.
    
    - render via render_duel_message (inclut déjà le sync roles XP chez toi)
    - edit du message
    - annonce level up/down si présent dans snapshot.effects.level_changes
    """
    guild = interaction.guild
    if guild is None:
        return

    # Import local pour éviter cycles
    from eldoria.ui.duels.render import render_duel_message

    embed, files, view = await render_duel_message(snapshot=snapshot, guild=guild, bot=bot)

    msg = interaction.message
    if msg is None:
        await interaction.followup.send(content="Impossible de modifier le message (message introuvable).", ephemeral=True)
        return

    await msg.edit(
        content=msg.content or "",
        embed=embed,
        view=view,
    )

    # Annonce level up/down (si demandé par le service via effects)
    effects = snapshot.get("effects") or {}
    changes = effects.get("level_changes") or []
    if not changes:
        return

    channel = interaction.channel
    if channel is None or not isinstance(channel, discord.abc.Messageable):
        return

    lines: list[str] = []
    for ch in changes:
        uid = ch.get("user_id")
        old_lvl = ch.get("old_level")
        new_lvl = ch.get("new_level")
        if uid is None or old_lvl is None or new_lvl is None:
            continue

        member = guild.get_member(uid)
        if member is None:
            continue
        
        role_ids = effects.get("xp_role_ids") or {}

        lvl_txt = level_mention(guild, new_lvl, role_ids)
        if new_lvl > old_lvl:
            lines.append(f"🎉 GG {member.mention} : tu atteins le rang  {lvl_txt} grâce au duel !")
        else:
            lines.append(f"📉 Hélas, {member.mention} redescend au rang **{lvl_txt}** à cause du duel.")

    if lines:
        await channel.send("\n".join(lines))
