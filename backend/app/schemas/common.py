from datetime import datetime, timezone
from typing import Annotated

from pydantic import BeforeValidator


def _assume_utc(v: object) -> object:
    """SQLite drops tzinfo on round-trip even though Dataset/Finding models
    always write timezone-aware UTC values (see models/dataset.py `_now`).
    Without this, naive datetimes serialize without a UTC offset and
    JS `new Date(iso)` misreads them as already being in the browser's
    local time instead of converting from UTC.
    """
    if isinstance(v, datetime) and v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    return v


UTCDatetime = Annotated[datetime, BeforeValidator(_assume_utc)]
