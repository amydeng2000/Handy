"""Read one curated conversation thread from local JSON."""

import json
from pathlib import Path

from pydantic import ValidationError

from .models import Moment


def load_moments(path: Path) -> list[Moment]:
    """Validate every record and sort by date, preserving order within a date."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("moments file must be a nonempty JSON array")

    try:
        moments = [Moment.model_validate(item) for item in raw]
    except ValidationError as error:
        raise ValueError(f"invalid moment: {error}") from error

    ids = [moment.id for moment in moments]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate moment id")
    if any(not moment.id.strip() or not moment.text.strip() for moment in moments):
        raise ValueError("moment id and text must contain non-whitespace characters")

    return sorted(moments, key=lambda moment: moment.date)
