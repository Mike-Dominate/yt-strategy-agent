"""Resolve a YouTube handle, URL, or channel ID to a canonical channel ID + handle."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from googleapiclient.discovery import build

from auth import get_credentials


def parse_input(raw: str) -> tuple[str, str | None]:
    """Return (kind, value). kind is 'id', 'handle', or 'username'."""
    raw = raw.strip()
    if raw.startswith("UC") and len(raw) == 24:
        return "id", raw
    m = re.search(r"youtube\.com/channel/(UC[\w-]{22})", raw)
    if m:
        return "id", m.group(1)
    m = re.search(r"youtube\.com/@([\w.\-]+)", raw)
    if m:
        return "handle", m.group(1)
    if raw.startswith("@"):
        return "handle", raw[1:]
    m = re.search(r"youtube\.com/(?:user|c)/([\w.\-]+)", raw)
    if m:
        return "username", m.group(1)
    return "handle", raw


def resolve(raw: str) -> dict:
    creds = get_credentials()
    yt = build("youtube", "v3", credentials=creds)
    kind, value = parse_input(raw)
    params = {"part": "snippet,contentDetails"}
    if kind == "id":
        params["id"] = value
    elif kind == "handle":
        params["forHandle"] = f"@{value}"
    else:
        params["forUsername"] = value
    resp = yt.channels().list(**params).execute()
    items = resp.get("items") or []
    if not items:
        raise SystemExit(f"Could not resolve: {raw}")
    item = items[0]
    return {
        "id": item["id"],
        "handle": item["snippet"].get("customUrl", "").lstrip("@") or value,
        "title": item["snippet"]["title"],
        "uploads_playlist": item["contentDetails"]["relatedPlaylists"]["uploads"],
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: resolve_channel.py <handle|url|id>")
    info = resolve(sys.argv[1])
    print(
        f"{info['id']}\t{info['handle']}\t{info['title']}\t{info['uploads_playlist']}"
    )
