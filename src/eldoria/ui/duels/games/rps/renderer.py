from __future__ import annotations
from typing import Optional
import discord

import eldoria.features.duel.constants as constants
from eldoria.features.duel.games.rps.rps_constants import (
    RPS_DICT_RESULT,
    RPS_DICT_STATE,
    RPS_PAYLOAD_A_MOVE,
    RPS_PAYLOAD_B_MOVE,
    RPS_STATE_FINISHED,
    RPS_STATE_WAITING,
    RPS_MOVE_PAPER,
    RPS_MOVE_ROCK,
    RPS_MOVE_SCISSORS,
)
from eldoria.ui.duels.common import build_game_base_embed
from eldoria.ui.duels.result.finished import build_game_result_base_embed
from eldoria.utils.discord_utils import get_member_by_id_or_raise

from .view import RpsView


MOVE_EMOJI = {
    RPS_MOVE_ROCK: "🪨 Pierre",
    RPS_MOVE_PAPER: "📄 Papier",
    RPS_MOVE_SCISSORS: "✂️ Ciseaux",
}

def _move_label(move: str | None) -> str:
    if not move:
        return "?"
    return f"{MOVE_EMOJI.get(move, '❔')}"

def _result_label(result: str, player_a: discord.Member, player_b: discord.Member) -> str:
    match result:
        case constants.DUEL_RESULT_DRAW:
            return "🤝 Égalité"
        case constants.DUEL_RESULT_WIN_A:
            return f"🏆 Victoire de **{player_a.display_name}**"
        case constants.DUEL_RESULT_WIN_B:
            return f"🏆 Victoire de **{player_b.display_name}**"
        case _:
            return f"Résultat: {result}"


async def render_rps(
    snapshot: dict,
    guild: discord.Guild,
    bot: object,
) -> tuple[discord.Embed, list[discord.File], Optional[discord.ui.View]]:
    duel = snapshot["duel"]
    player_a_id = duel["player_a"]
    player_b_id = duel["player_b"]

    player_a = await get_member_by_id_or_raise(guild, player_a_id)
    player_b = await get_member_by_id_or_raise(guild, player_b_id)

    stake_xp = duel["stake_xp"]
    expires_at = duel["expires_at"]
    game_type = duel["game_type"]

    

    game = snapshot.get("game") or {}
    state = game.get(RPS_DICT_STATE)

    if state == RPS_STATE_WAITING or state is None:

        # base embed de la partie
        embed, files = await build_game_base_embed(
            player_a=player_a,
            player_b=player_b,
            stake_xp=stake_xp,
            expires_at=expires_at,
            game_type=game_type,
        )

        a_played = "✅" if game.get("a_played") else "⌛"
        b_played = "✅" if game.get("b_played") else "⌛"
        embed.add_field(
            name="État",
            value=(
                f"{player_a.display_name} a joué: {a_played}\n"
                f"{player_b.display_name} a joué: {b_played}\n\u200b\n"
            ),
            inline=False,
        )
        embed.set_footer(text="Choisis ton coup avec les boutons ci-dessous (caché jusqu'à la fin).")
        return embed, files, RpsView(bot=bot, duel_id=duel["id"])

    
    if state == RPS_STATE_FINISHED:

        embed, files = await build_game_result_base_embed(
            player_a=player_a,
            player_b=player_b,
            stake_xp=stake_xp,
            game_type=game_type,
        )
        
        result = str(game.get(RPS_DICT_RESULT, "UNKNOWN"))
        embed.add_field(name="Résultat", value=_result_label(result, player_a, player_b) + "\n\u200b\n", inline=False)

        a_move = game.get(RPS_PAYLOAD_A_MOVE)
        b_move = game.get(RPS_PAYLOAD_B_MOVE)
        embed.add_field(
            name="Coups joués",
            value=(
                f"{player_a.display_name} : {_move_label(a_move)}\n"
                f"{player_b.display_name} : {_move_label(b_move)}\n\u200b\n"
            ),
            inline=True,
        )

        embed.add_field(name="", value="", inline=True)
        
        xp = snapshot.get("xp")
        if isinstance(xp, dict):
            embed.add_field(
                name="XP après duel",
                value=(
                    f"{player_a.display_name}: **{xp.get(player_a_id, '?')}**\n"
                    f"{player_b.display_name}: **{xp.get(player_b_id, '?')}**\n\u200b\n"
                ),
                inline=True,
            )

        embed.set_footer(text="Duel terminé.")
        return embed, files, None

    
    

    # fallback si état inconnu
    embed.add_field(name="État", value=f"État inconnu: `{state}`", inline=False)
    return embed, files, RpsView(bot=bot, duel_id=duel["id"])
