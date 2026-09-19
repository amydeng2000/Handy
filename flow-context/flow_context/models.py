"""Validated records and compact synthesis output."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Moment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    date: date
    source_type: Literal["voice", "ai_chat", "meeting", "document"]
    author_role: Literal["user", "ai", "other"]
    stance: Literal["observation", "proposal", "rejection", "decision", "open_question"]
    origin: Literal["real", "synthetic"]
    text: str = Field(min_length=1)


class ContextPacket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_direction: str = Field(min_length=1)
    why_it_changed: str = Field(min_length=1)
    open_questions: str = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)
