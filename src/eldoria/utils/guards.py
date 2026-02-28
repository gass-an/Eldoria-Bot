"""Module de guards pour les commandes, permettant de vérifier certaines conditions avant d'exécuter la logique principale d'une commande."""

from collections.abc import Mapping

import discord

from eldoria.exceptions.duel import SamePlayerDuel
from eldoria.exceptions.general import (
    BotTargetNotAllowed,
    ChannelRequired,
    FeatureNotConfigured,
    GuildRequired,
    NotAllowed,
)
from eldoria.exceptions.role import (
    EmojiAlreadyBound,
    InvalidGuild,
    MessageAlreadyBound,
    RoleAboveBot,
    RoleAlreadyBound,
    SecretRoleNotFound,
)


def require_guild_ctx(ctx: discord.ApplicationContext) -> tuple[discord.Guild, discord.abc.GuildChannel]:
    """Garantit que la commande est exécutée dans une guild et un channel valide."""
    if ctx.guild is None:
        raise GuildRequired()

    if ctx.channel is None or not isinstance(ctx.channel, discord.abc.GuildChannel):
        raise ChannelRequired()

    return ctx.guild, ctx.channel

def require_not_bot(member: discord.Member) -> discord.Member:
    """Garantit que le membre n'est pas un bot, sinon lève une exception."""
    if member.bot:
        raise BotTargetNotAllowed(member.id)
    return member


def require_not_self(ctx: discord.ApplicationContext, member: discord.Member) -> discord.Member:
    """Garantit que le membre ciblé n'est pas l'utilisateur exécutant la commande, sinon lève une exception."""
    if member.id == ctx.user.id:
        raise SamePlayerDuel(ctx.user.id, ctx.user.id)
    return member

def require_feature_enabled(enabled: bool, feature_name: str) -> None:
    """Garantit qu'une fonctionnalité est activée pour le serveur, sinon lève une exception."""
    if not enabled:
        raise FeatureNotConfigured(feature_name)


def require_specific_user_id(ctx: discord.ApplicationContext, allowed_user_id: int) -> None:
    """Garantit que l'utilisateur exécutant la commande a l'ID spécifié, sinon lève une exception."""
    if ctx.user.id != allowed_user_id:
        raise NotAllowed()
    
def require_specific_guild(actual_guild_id: int, expected_guild_id: int) -> None:
    """Garantit que le serveur a l'ID spécifié, sinon lève une exception."""
    if actual_guild_id != expected_guild_id:
        raise InvalidGuild(expected_guild_id, actual_guild_id)
    
def require_role_assignable_by_bot(bot_member: discord.Member, role: discord.Role) -> None:
    """Garantit que le rôle est assignable par le bot (c'est-à-dire qu'il est en dessous du rôle du bot dans la hiérarchie), sinon lève une exception."""
    if role.position >= bot_member.top_role.position:
        raise RoleAboveBot(role.id)
    

def require_no_rr_conflict(
    *,
    message_id: int,
    emoji: str,
    role_id: int,
    existing: Mapping[str, int],  # {emoji: role_id}
) -> None:
    """Garantit qu'il n'y a pas de conflit de rôle de réaction pour un message donné, sinon lève une exception."""
    for existing_emoji, existing_role_id in existing.items():
        # Même rôle, autre emoji
        if existing_role_id == role_id and existing_emoji != emoji:
            raise RoleAlreadyBound(
                message_id=message_id,
                role_id=role_id,
                existing_emoji=existing_emoji,
            )
        # Même emoji, autre rôle
        if existing_role_id != role_id and existing_emoji == emoji:
            raise EmojiAlreadyBound(
                message_id=message_id,
                emoji=emoji,
                existing_role_id=existing_role_id,
            )
        
def require_secretrole_not_conflicting(*, message: str, existing_role_id: int | None, role_id: int) -> None:
    """Garantit qu'il n'y a pas de conflit de rôle secret pour un message+channel donné, sinon lève une exception."""
    if existing_role_id is not None and existing_role_id != role_id:
        raise MessageAlreadyBound(message=message, existing_role_id=existing_role_id)


def require_secretrole_exists(*, message: str, existing_role_id: int | None) -> int:
    """Garantit qu'une règle de rôle secret existe pour un message+channel donné, sinon lève une exception."""
    if existing_role_id is None:
        raise SecretRoleNotFound(message=message)
    return existing_role_id