from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


class Settings:
    app_name: str = "PathwayIQ API"
    api_version: str = "v1"
    data_file: Path
    gemini_api_key: str | None
    gemini_model: str
    gemini_enable_scheduling: bool

    def __init__(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.data_file = root / "app" / "data" / "seed_data.json"
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-3-flash")
        self.gemini_enable_scheduling = os.getenv("GEMINI_ENABLE_SCHEDULING", "true").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
