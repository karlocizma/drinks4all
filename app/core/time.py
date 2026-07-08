from datetime import UTC, datetime


def utcnow() -> datetime:
    """Current UTC time as a naive datetime, matching this app's non-timezone-aware DateTime columns."""
    return datetime.now(UTC).replace(tzinfo=None)
