from dataclasses import dataclass
from typing import Any

from eldoria.features.duel._internal import flow, gameplay, helpers, maintenance

@dataclass(slots=True)
class DuelService:
    def new_duel(self, guild_id: int, channel_id: int, player_a_id: int, player_b_id: int) -> dict[str, Any]:
        return flow.new_duel(guild_id, channel_id, player_a_id, player_b_id)

    def configure_game_type(self, duel_id: int, game_type: str) -> dict[str, Any]:
        return flow.configure_game_type(duel_id, game_type)

    def configure_stake_xp(self, duel_id: int, stake_xp: int) -> dict[str, Any]:
        return flow.configure_stake_xp(duel_id, stake_xp)

    def send_invite(self, duel_id: int, message_id: int) -> dict[str, Any]:
        return flow.send_invite(duel_id, message_id)

    def accept_duel(self, duel_id: int, user_id: int) -> dict[str, Any]:
        return flow.accept_duel(duel_id, user_id)

    def refuse_duel(self, duel_id: int, user_id: int) -> dict[str, Any]:
        return flow.refuse_duel(duel_id, user_id)

    def play_game_action(self, duel_id: int, user_id: int, action: dict[str, Any]) -> dict[str, Any]:
        return gameplay.play_game_action(duel_id, user_id, action)

    def cancel_expired_duels(self) -> list[dict[str, Any]]:
        return maintenance.cancel_expired_duels()

    def cleanup_old_duels(self, now_ts: int) -> None:
        return maintenance.cleanup_old_duels(now_ts)
    
    def get_allowed_stakes(self, duel_id: int) -> list[int]:
        return helpers.get_allowed_stakes(duel_id)
