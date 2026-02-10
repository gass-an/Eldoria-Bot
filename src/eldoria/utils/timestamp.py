from datetime import UTC, datetime


def now_ts() -> int:
    return int(datetime.now(UTC).timestamp())

def add_duration(timestamp:int, *, seconds:int = 0, minutes:int = 0, hours:int = 0, days:int = 0) -> int:

    if seconds < 0 or minutes < 0 or hours < 0 or days < 0:
        raise ValueError("Durée négative interdite")

    return timestamp + seconds + (minutes * 60) + (hours * 3600) + (days * 86400)