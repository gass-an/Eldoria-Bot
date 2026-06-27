"""Service métier pour le système de ticketing.

Expose des méthodes pour gérer la configuration et fournir des helpers de création.
"""

from dataclasses import dataclass
from typing import Any

from eldoria.db.repo import ticketing_repo


@dataclass(slots=True)
class TicketingService:
    """Service simple pour gérer la configuration du ticketing."""

    def ensure_defaults(
        self,
        guild_id: int,
        *,
        enabled: bool = False,
        category_id: int = 0,
        open_channel_id: int = 0,
    ) -> None:
        return ticketing_repo.tk_ensure_defaults(
            guild_id, enabled=enabled, category_id=category_id, open_channel_id=open_channel_id
        )

    def get_config(self, guild_id: int) -> dict[str, Any]:
        return ticketing_repo.tk_get_config(guild_id)

    def set_config(
        self,
        guild_id: int,
        *,
        enabled: bool | None = None,
        category_id: int | None = None,
        open_channel_id: int | None = None,
    ) -> None:
        return ticketing_repo.tk_set_config(
            guild_id, enabled=enabled, category_id=category_id, open_channel_id=open_channel_id
        )

    def set_enabled(self, guild_id: int, enabled: bool) -> None:
        return ticketing_repo.tk_set_enabled(guild_id, enabled)

    def set_category_id(self, guild_id: int, category_id: int) -> None:
        return ticketing_repo.tk_set_category_id(guild_id, category_id)

    def set_open_channel_id(self, guild_id: int, open_channel_id: int) -> None:
        return ticketing_repo.tk_set_open_channel_id(guild_id, open_channel_id)

    def is_enabled(self, guild_id: int) -> bool:
        return ticketing_repo.tk_is_enabled(guild_id)

    def get_category_id(self, guild_id: int) -> int:
        return ticketing_repo.tk_get_category_id(guild_id)

    def get_open_channel_id(self, guild_id: int) -> int:
        return ticketing_repo.tk_get_open_channel_id(guild_id)

    def allocate_ticket_number(self, guild_id: int) -> int:
        return ticketing_repo.tk_allocate_ticket_number(guild_id)

    def record_ticket(
        self,
        guild_id: int,
        ticket_number: int,
        channel_id: int,
        owner_id: int,
        created_at: int,
    ) -> None:
        return ticketing_repo.tk_record_ticket(
            guild_id,
            ticket_number,
            channel_id,
            owner_id,
            created_at,
        )
