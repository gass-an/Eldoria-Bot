from datetime import datetime, timezone

def now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())

def add_duration(timestamp:int, *, seconds:int = 0, minutes:int = 0, hours:int = 0) -> int:

    if seconds < 0 or minutes < 0 or hours < 0:
        raise ValueError("Durée négative interdite")

    return timestamp + seconds + (minutes * 60) + (hours * 3600)