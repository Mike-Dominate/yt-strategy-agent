"""Claude extraction with prompt caching."""

from __future__ import annotations

import json
import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import dotenv_values

ROOT = Path(__file__).parent
_ENV = dotenv_values(ROOT / ".env")
_API_KEY = _ENV.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
_BASE_URL = _ENV.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com"

MODEL = "claude-opus-4-7"
MAX_TOKENS = 4096

SYSTEM_PROMPT = """You are a trading-strategy analyst. You read transcripts of trading and investing YouTube videos and extract a structured representation of the host's strategy: what they buy, what they sell, how they manage risk, how they time entries and exits, and any specific trades they describe executing.

You return ONLY valid JSON matching this exact schema:

{
  "strategy_summary": "string — 2-4 sentences describing the host's overall approach in this video",
  "buy_rules":    [{"rule": "string", "confidence": 0.0-1.0, "source_quote": "string"}],
  "sell_rules":   [{"rule": "string", "confidence": 0.0-1.0, "source_quote": "string"}],
  "risk_notes":   [{"note": "string", "confidence": 0.0-1.0, "source_quote": "string"}],
  "timing_notes": [{"note": "string", "confidence": 0.0-1.0, "source_quote": "string"}],
  "executed_trades": [
    {"asset": "string", "direction": "long|short", "entry": "string", "exit": "string", "outcome": "string"}
  ],
  "strategy_shift": {"changed": false, "what_changed": "string", "vs_prior": "string"}
}

Rules:
- Each rule/note must be a concrete, actionable statement, not a vague observation.
- `confidence` reflects how clearly and emphatically the host states the rule (0.9+ for explicit "always do X", 0.5 for offhand suggestions, <0.3 for speculation).
- `source_quote` must be a verbatim snippet from the transcript (≤200 chars).
- If the host mentions changing their mind from a previous position, set strategy_shift.changed = true.
- If a section has no relevant content, return an empty array.
- Return JSON only, no markdown fences, no commentary."""


def _client() -> Anthropic:
    if not _API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not found in .env")
    return Anthropic(api_key=_API_KEY, base_url=_BASE_URL)


def extract_from_transcript(transcript: str, video_title: str) -> dict:
    """Send transcript to Claude with system prompt cached. Returns parsed JSON."""
    user = (
        f"Video title: {video_title}\n\n"
        f"Transcript:\n{transcript}\n\n"
        "Extract the structured strategy JSON now."
    )
    resp = _client().messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(
        block.text for block in resp.content if hasattr(block, "text")
    ).strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip().rstrip("`").strip()
    return json.loads(text)
