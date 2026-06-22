"""Main ingest pipeline. Run with --once for a single pass."""

from __future__ import annotations

import argparse
import sys

import yaml
from googleapiclient.discovery import build

from auth import get_credentials
from change_detect import detect_and_log
from extract import extract_from_transcript, summarize_impact
from notify import build_email_body, send_email
from transcript import fetch_transcripts
from logging_utils import get_logger
from settings import CHANNELS_FILE, YOUTUBE_WINDOW
from store import (
    channel_dir,
    latest_extractions,
    mark_seen,
    read_rules_json,
    seen,
    write_rules_json,
    write_strategy_md,
    write_video_md,
)
from weighting import rebuild

logger = get_logger("ingest")


def _load_channels() -> list[dict]:
    data = yaml.safe_load(CHANNELS_FILE.read_text())
    return data.get("channels", [])


def _latest_videos(yt, uploads_playlist: str, limit: int = YOUTUBE_WINDOW) -> list[dict]:
    resp = (
        yt.playlistItems()
        .list(
            part="snippet,contentDetails",
            playlistId=uploads_playlist,
            maxResults=limit,
        )
        .execute()
    )
    return [
        {
            "video_id": item["contentDetails"]["videoId"],
            "title": item["snippet"]["title"],
            "published_at": item["contentDetails"].get("videoPublishedAt")
            or item["snippet"]["publishedAt"],
        }
        for item in resp.get("items", [])
    ]


def process_channel(yt, channel: dict) -> int:
    handle = channel["handle"]
    title = channel["title"]
    logger.info("processing %s (@%s)", title, handle)
    videos = _latest_videos(yt, channel["uploads_playlist"], YOUTUBE_WINDOW)
    if not videos:
        logger.info("no uploads found for %s", handle)
        return 0
    unseen = [v for v in videos if not seen(v["video_id"])]
    transcripts: dict[str, str | None] = {}
    if unseen:
        logger.info("fetching %s transcript(s) for %s", len(unseen), handle)
        try:
            transcripts = fetch_transcripts([v["video_id"] for v in unseen])
        except Exception as exc:
            logger.warning("transcript fetch failed for %s: %s", handle, exc)
    new_count = 0
    for video in videos:
        vid = video["video_id"]
        if seen(vid):
            logger.info("seen %s %s", vid, video['title'][:60])
            continue
        logger.info("fetch %s %s", vid, video['title'][:60])
        transcript = transcripts.get(vid)
        if not transcript:
            logger.info("no transcript available for %s, skipping", vid)
            continue
        try:
            extraction = extract_from_transcript(transcript[:60000], video["title"])
        except Exception as exc:
            logger.warning("extraction failed for %s: %s", vid, exc)
            continue
        prior_rules = read_rules_json(handle)
        write_video_md(handle, vid, video["title"], video["published_at"], extraction)
        change_logged = detect_and_log(handle, vid, video["title"], extraction)
        mark_seen(
            channel["id"],
            handle,
            vid,
            video["title"],
            video["published_at"],
            extraction,
        )
        extractions = latest_extractions(channel["id"], YOUTUBE_WINDOW)
        new_rules = rebuild([e["extraction"] for e in extractions])
        write_rules_json(handle, new_rules)
        write_strategy_md(
            handle,
            title,
            new_rules,
            sources=[
                {
                    "video_id": e["video_id"],
                    "title": e["title"],
                    "published_at": e["published_at"],
                }
                for e in extractions
            ],
        )
        spec_path = channel_dir(handle) / "strategy_spec.md"
        spec_text = spec_path.read_text() if spec_path.exists() else None
        try:
            impact = summarize_impact(extraction, video["title"], spec_text)
        except Exception as exc:
            impact = f"(impact summary failed: {exc})"
        try:
            body = build_email_body(
                channel_title=title,
                channel_handle=handle,
                video=video,
                extraction=extraction,
                prior_rules=prior_rules,
                new_rules=new_rules,
                change_logged=change_logged,
                impact_paragraph=impact,
                strategy_spec=spec_text,
            )
            shift_tag = " ⚠ SHIFT" if change_logged else ""
            subject = f"[YT Strategy] {title}: {video['title'][:80]}{shift_tag}"
            send_email(subject, body)
            logger.info("notification/email processed for %s", vid)
        except Exception as exc:
            logger.warning("email/notification failed for %s: %s", vid, exc)
        new_count += 1
    if new_count == 0:
        extractions = latest_extractions(channel["id"], YOUTUBE_WINDOW)
        if extractions and not (channel_dir(handle) / "strategy.md").exists():
            rules = rebuild([e["extraction"] for e in extractions])
            write_rules_json(handle, rules)
            write_strategy_md(
                handle,
                title,
                rules,
                sources=[
                    {
                        "video_id": e["video_id"],
                        "title": e["title"],
                        "published_at": e["published_at"],
                    }
                    for e in extractions
                ],
            )
    logger.info("%s new video(s) processed this pass for %s", new_count, handle)
    return new_count


def run_once() -> int:
    creds = get_credentials()
    yt = build("youtube", "v3", credentials=creds)
    total = 0
    for channel in _load_channels():
        total += process_channel(yt, channel)
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once", action="store_true", help="run a single pass and exit"
    )
    args = parser.parse_args()
    new = run_once()
    logger.info("done. %s new video(s) processed.", new)
