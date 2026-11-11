"""Load versioned prompt templates shipped with the voice service."""
from functools import lru_cache
from pathlib import Path

from langchain_core.prompts import PromptTemplate

PROMPT_DIRECTORY = Path(__file__).resolve().parents[4] / "prompts"


@lru_cache
def load_prompt(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError("Invalid prompt name")
    return (PROMPT_DIRECTORY / f"{name}.txt").read_text(encoding="utf-8")


def render_prompt(name: str, **variables: str) -> str:
    return PromptTemplate.from_template(load_prompt(name)).format(**variables)
