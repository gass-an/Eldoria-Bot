from datetime import datetime
from zoneinfo import ZoneInfo

from eldoria.config import AUTO_SAVE_TZ
from eldoria.utils.timestamp import now_ts

TIMEZONE = ZoneInfo(AUTO_SAVE_TZ)

def _day_key_utc(ts: int | None = None) -> str:
    dt = datetime.fromtimestamp(
        ts if ts is not None else now_ts(), 
        tz=TIMEZONE #prend la timezone défini dans le .env
        )  
    return dt.strftime("%Y%m%d")