"""Module de logique métier pour la fonctionnalité d'XP par message."""

from datetime import datetime
from zoneinfo import ZoneInfo

from eldoria.config import AUTO_SAVE_TZ
from eldoria.utils.timestamp import now_ts

TIMEZONE = ZoneInfo(AUTO_SAVE_TZ)

def day_key_utc(ts: int | None = None) -> str:
    """Retourne une clé de jour au format YYYYMMDD en UTC, à partir d'un timestamp donné ou du timestamp actuel."""
    dt = datetime.fromtimestamp(
        ts if ts is not None else now_ts(), 
        tz=TIMEZONE #prend la timezone défini dans le .env
        )  
    return dt.strftime("%Y%m%d")