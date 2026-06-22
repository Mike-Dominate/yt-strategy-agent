"""Central runtime settings for YT Strategy Agent."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).parent
ENV = {
    **dotenv_values(ROOT / ".env"),
    **os.environ,
}


def _get(name: str, default: str | None = None) -> str | None:
    value = ENV.get(name)
    return value if value not in (None, "") else default


def _get_bool(name: str, default: bool = False) -> bool:
    raw = _get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    raw = _get(name)
    if raw is None:
        return default
    return int(raw)


STATE_DIR = Path(_get("YT_STATE_DIR", str(ROOT)))
CHANNELS_FILE = Path(_get("YT_CHANNELS_FILE", str(ROOT / "channels.yaml")))
CLIENT_SECRET = Path(_get("YT_CLIENT_SECRET", str(ROOT / "client_secret.json")))
TOKEN_PATH = Path(_get("YT_TOKEN_PATH", str(STATE_DIR / "token.pickle")))
DB_PATH = Path(_get("YT_DB_PATH", str(STATE_DIR / "state.db")))
CHANNELS_DIR = Path(_get("YT_OUTPUT_DIR", str(STATE_DIR / "channels")))
LOG_DIR = Path(_get("YT_LOG_DIR", str(STATE_DIR / "logs")))
WATCH_INTERVAL_SECONDS = _get_int("YT_WATCH_INTERVAL_SECONDS", 600)
YOUTUBE_WINDOW = _get_int("YT_WINDOW", 5)
EMAIL_ENABLED = _get_bool("YT_EMAIL_ENABLED", True)
TRANSCRIPT_PROVIDER = (_get("YT_TRANSCRIPT_PROVIDER", "auto") or "auto").strip().lower()
EMBEDDING_MODEL = _get("YT_EMBEDDING_MODEL", "all-MiniLM-L6-v2") or "all-MiniLM-L6-v2"
LLM_PROVIDER = (_get("YT_LLM_PROVIDER", "anthropic") or "anthropic").strip().lower()
LLM_MODEL = _get("YT_LLM_MODEL", "claude-opus-4-7") or "claude-opus-4-7"
ANTHROPIC_BASE_URL = _get("ANTHROPIC_BASE_URL", "https://api.anthropic.com") or "https://api.anthropic.com"
TAILSCALE_HOSTNAME = _get("TAILSCALE_HOSTNAME")
TAILSCALE_TAILNET = _get("TAILSCALE_TAILNET")

for path in [STATE_DIR, CHANNELS_DIR, LOG_DIR]:
    path.mkdir(parents=True, exist_ok=True)
