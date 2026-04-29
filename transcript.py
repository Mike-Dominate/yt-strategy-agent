"""Transcript fetching via Apify (karamelo/youtube-transcripts actor)."""

from __future__ import annotations

import html
import os
from pathlib import Path

from apify_client import ApifyClient
from dotenv import dotenv_values

ROOT = Path(__file__).parent
_ENV = dotenv_values(ROOT / ".env")
_APIFY_TOKEN = _ENV.get("APIFY_TOKEN") or os.environ.get("APIFY_TOKEN")
_ACTOR = "karamelo/youtube-transcripts"


def fetch_transcripts(video_ids: list[str]) -> dict[str, str | None]:
    """Return {video_id: transcript_text or None} for each video."""
    if not video_ids:
        return {}
    if not _APIFY_TOKEN:
        raise RuntimeError("APIFY_TOKEN not found in .env")
    client = ApifyClient(_APIFY_TOKEN)
    urls = [f"https://www.youtube.com/watch?v={vid}" for vid in video_ids]
    run = client.actor(_ACTOR).call(
        run_input={
            "urls": urls,
            "outputFormat": "singleStringText",
            "maxRetries": 8,
            "channelIDBoolean": True,
            "datePublishedBoolean": True,
        }
    )
    out: dict[str, str | None] = {vid: None for vid in video_ids}
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        vid = item.get("videoId")
        captions = item.get("captions") or ""
        if vid and captions:
            out[vid] = html.unescape(captions).strip()
    return out
