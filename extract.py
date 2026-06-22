"""Claude extraction with prompt caching."""

from __future__ import annotations

import json
import os

from anthropic import Anthropic
from anthropic import APIError

from settings import ANTHROPIC_BASE_URL, ENV, LLM_MODEL, LLM_PROVIDER

_API_KEY = ENV.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")

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
    if LLM_PROVIDER != "anthropic":
        raise RuntimeError(f"unsupported LLM provider: {LLM_PROVIDER}")
    return Anthropic(api_key=_API_KEY, base_url=ANTHROPIC_BASE_URL)


def extract_from_transcript(transcript: str, video_title: str) -> dict:
    """Send transcript to Claude with system prompt cached. Returns parsed JSON."""
    user = (
        f"Video title: {video_title}\n\n"
        f"Transcript:\n{transcript}\n\n"
        "Extract the structured strategy JSON now."
    )
    resp = _client().messages.create(
        model=LLM_MODEL,
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


_IMPACT_SYSTEM = """You are a trading-strategy reviewer. The user runs a paper-trading system that reads a "strategy spec" markdown file and executes signals.

Given (a) the spec, (b) a fresh extraction from a new video by the same host, write a 3-5 sentence brief covering:
1. Whether this video changes the spec's bias (long / flat / short).
2. Whether any explicit invalidation level mentioned in the spec is now closer or further from triggering.
3. Whether tranche size, entry zones, or take-profit levels need adjusting based on what the host said.
4. One concrete action (or "no action — bias intact") for the next 24 hours.

Be plain-spoken, no hedging adverbs. Do not invent numbers the host didn't say."""


def summarize_impact(
    extraction: dict, video_title: str, strategy_spec: str | None
) -> str:
    spec_block = (
        f"Current spec:\n{strategy_spec.strip()}\n\n"
        if strategy_spec
        else "(No paper-trading spec exists yet for this channel — return: 'No tradable spec for this channel; this video updates the macro view only.')\n\n"
    )
    user = (
        spec_block
        + f"New video: {video_title}\n\n"
        + f"Extracted JSON:\n{json.dumps(extraction, indent=2)}\n\n"
        + "Write the brief now."
    )
    try:
        resp = _client().messages.create(
            model=LLM_MODEL,
            max_tokens=600,
            system=[
                {
                    "type": "text",
                    "text": _IMPACT_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user}],
        )
        return "".join(
            block.text for block in resp.content if hasattr(block, "text")
        ).strip()
    except APIError as exc:
        return f"(impact summary failed: {exc})"
