"""Transcript fetching with provider fallback support."""

from __future__ import annotations

import html
import os

from apify_client import ApifyClient
from dotenv import dotenv_values
from youtube_transcript_api import YouTubeTranscriptApi

from logging_utils import get_logger
from settings import ROOT, TRANSCRIPT_PROVIDER

_ENV = dotenv_values(ROOT / ".env")
_APIFY_TOKEN = _ENV.get("APIFY_TOKEN") or os.environ.get("APIFY_TOKEN")
_ACTOR = "karamelo/youtube-transcripts"
logger = get_logger("transcript")


def _fetch_apify(video_ids: list[str]) -> dict[str, str | None]:
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


def _fetch_youtube_transcript_api(video_ids: list[str]) -> dict[str, str | None]:
    out: dict[str, str | None] = {vid: None for vid in video_ids}
    api = YouTubeTranscriptApi()
    for vid in video_ids:
        try:
            transcript = api.fetch(vid)
            out[vid] = " ".join(chunk.text for chunk in transcript).strip()
        except Exception as exc:
            logger.warning("youtube transcript api failed for %s: %s", vid, exc)
    return out


def fetch_transcripts(video_ids: list[str]) -> dict[str, str | None]:
    """Return {video_id: transcript_text or None} for each video."""
    if not video_ids:
        return {}
    providers = {
        "apify": [_fetch_apify],
        "youtube": [_fetch_youtube_transcript_api],
        "auto": [_fetch_apify, _fetch_youtube_transcript_api],
    }
    sequence = providers.get(TRANSCRIPT_PROVIDER, providers["auto"])
    out: dict[str, str | None] = {vid: None for vid in video_ids}
    remaining = list(video_ids)
    for fetcher in sequence:
        if not remaining:
            break
        try:
            batch = fetcher(remaining)
        except Exception as exc:
            logger.warning("transcript provider %s failed: %s", fetcher.__name__, exc)
            continue
        for vid, transcript in batch.items():
            if transcript:
                out[vid] = transcript
        remaining = [vid for vid in remaining if not out.get(vid)]
    return out
