from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _read_env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()


PROJECT_ROOT = Path(__file__).resolve().parent.parent
NEW_RELIC_GRAPHQL_ENDPOINT = "https://api.newrelic.com/graphql"
MARKETS_ROOT = PROJECT_ROOT / "markets"


def get_runtime_settings() -> dict:
    api_key = _read_env("NEW_RELIC_API_KEY")
    if not api_key:
        raise ValueError("Missing required environment variable: NEW_RELIC_API_KEY")
    return {
        "graphql_endpoint": NEW_RELIC_GRAPHQL_ENDPOINT,
        "api_key": api_key,
        "tetris_api_key": _read_env("TETRIS_API_KEY"),
        "markets_root": str(MARKETS_ROOT),
        "output_dir": _read_env("OUTPUT_DIR", str(PROJECT_ROOT / "output")),
    }
