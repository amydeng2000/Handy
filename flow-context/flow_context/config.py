"""Configuration loaded from the local, ignored .env file."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class LlmConfig:
    base_url: str
    model: str
    api_key: str


@dataclass(frozen=True)
class FlowConfig:
    moments_path: Path
    thread_title: str
    llm: LlmConfig


def load_config(env_path: Path | None = None) -> FlowConfig:
    load_dotenv(dotenv_path=env_path or PROJECT_DIR / ".env", override=False)
    moments_path = Path(os.getenv("FLOW_CONTEXT_MOMENTS_PATH", "data/example_moments.json"))
    if not moments_path.is_absolute():
        moments_path = PROJECT_DIR / moments_path

    return FlowConfig(
        moments_path=moments_path,
        thread_title=os.getenv("FLOW_CONTEXT_THREAD_TITLE", "Future of Flow").strip(),
        llm=LlmConfig(
            base_url=os.getenv("FLOW_CONTEXT_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            model=os.getenv("FLOW_CONTEXT_LLM_MODEL", "gpt-4.1-mini"),
            api_key=os.getenv("FLOW_CONTEXT_LLM_API_KEY", ""),
        ),
    )
