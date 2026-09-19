"""Validated records and compact synthesis output."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Moment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    conversation_id: str | None = Field(default=None, min_length=1)
    source_label: str | None = Field(default=None, min_length=1)
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

    @field_validator("source_ids", mode="before")
    @classmethod
    def normalize_comma_separated_ids(cls, value: object) -> object:
        if isinstance(value, str):
            return [source_id.strip() for source_id in value.split(",") if source_id.strip()]
        return value

    @field_validator("current_direction", "why_it_changed", "open_questions", mode="before")
    @classmethod
    def normalize_bullet_list(cls, value: object) -> object:
        if isinstance(value, list) and all(isinstance(part, str) for part in value):
            return "; ".join(part.strip() for part in value if part.strip())
        return value

    @field_validator("current_direction", "why_it_changed", "open_questions")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("packet fields cannot be blank")
        return value.strip()
