"""SQLite state + markdown IO."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Iterable

from settings import CHANNELS_DIR, DB_PATH


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            channel_id TEXT NOT NULL,
            handle TEXT NOT NULL,
            title TEXT NOT NULL,
            published_at TEXT NOT NULL,
            processed_at TEXT NOT NULL,
            extraction_json TEXT NOT NULL
        )
        """)
    return conn


def seen(video_id: str) -> bool:
    with _db() as conn:
        row = conn.execute(
            "SELECT 1 FROM videos WHERE video_id = ?", (video_id,)
        ).fetchone()
    return row is not None


def mark_seen(
    channel_id: str,
    handle: str,
    video_id: str,
    title: str,
    published_at: str,
    extraction: dict,
) -> None:
    with _db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO videos VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                video_id,
                channel_id,
                handle,
                title,
                published_at,
                datetime.now(timezone.utc).isoformat(),
                json.dumps(extraction),
            ),
        )


def latest_extractions(channel_id: str, limit: int = 5) -> list[dict]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT video_id, title, published_at, extraction_json FROM videos "
            "WHERE channel_id = ? ORDER BY published_at DESC LIMIT ?",
            (channel_id, limit),
        ).fetchall()
    out = []
    for video_id, title, published_at, extraction_json in rows:
        out.append(
            {
                "video_id": video_id,
                "title": title,
                "published_at": published_at,
                "extraction": json.loads(extraction_json),
            }
        )
    return out


def channel_dir(handle: str) -> Path:
    d = CHANNELS_DIR / handle
    (d / "videos").mkdir(parents=True, exist_ok=True)
    return d


def write_video_md(
    handle: str, video_id: str, title: str, published_at: str, extraction: dict
) -> None:
    path = channel_dir(handle) / "videos" / f"{video_id}.md"
    lines = [
        f"# {title}",
        "",
        f"- Video: https://www.youtube.com/watch?v={video_id}",
        f"- Published: {published_at}",
        "",
        "## Strategy summary",
        extraction.get("strategy_summary", "").strip() or "_(none)_",
        "",
    ]
    for section, key in [
        ("Buy rules", "buy_rules"),
        ("Sell rules", "sell_rules"),
        ("Risk notes", "risk_notes"),
        ("Timing notes", "timing_notes"),
    ]:
        items = extraction.get(key) or []
        lines.append(f"## {section}")
        if not items:
            lines.append("_(none)_")
        for item in items:
            text = item.get("rule") or item.get("note") or ""
            conf = item.get("confidence", 0.0)
            quote = (item.get("source_quote") or "").strip()
            lines.append(f"- ({conf:.2f}) {text}")
            if quote:
                lines.append(f"  > {quote}")
        lines.append("")
    trades = extraction.get("executed_trades") or []
    lines.append("## Executed trades")
    if not trades:
        lines.append("_(none)_")
    for t in trades:
        lines.append(
            f"- {t.get('asset','?')} {t.get('direction','?')} entry {t.get('entry','?')} "
            f"exit {t.get('exit','?')} → {t.get('outcome','?')}"
        )
    path.write_text("\n".join(lines) + "\n")


def write_strategy_md(
    handle: str, title: str, rules: dict, sources: Iterable[dict]
) -> None:
    path = channel_dir(handle) / "strategy.md"
    lines = [
        f"# {title} — Living Strategy",
        "",
        f"_Last updated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}_",
        "",
        "## Strategy summary",
        rules.get("strategy_summary", "").strip() or "_(building — needs more videos)_",
        "",
    ]
    for section, key in [
        ("Buy rules", "buy_rules"),
        ("Sell rules", "sell_rules"),
        ("Risk notes", "risk_notes"),
        ("Timing notes", "timing_notes"),
    ]:
        items = rules.get(key) or []
        lines.append(f"## {section}")
        if not items:
            lines.append("_(none yet)_")
        for item in items:
            lines.append(f"- ({item['effective_confidence']:.2f}) {item['text']}")
        lines.append("")
    lines.append("## Sources (rolling 5-video window)")
    for s in sources:
        lines.append(
            f"- [{s['title']}](https://www.youtube.com/watch?v={s['video_id']}) — {s['published_at']}"
        )
    path.write_text("\n".join(lines) + "\n")


def write_rules_json(handle: str, rules: dict) -> None:
    (channel_dir(handle) / "rules.json").write_text(json.dumps(rules, indent=2))


def read_rules_json(handle: str) -> dict | None:
    p = channel_dir(handle) / "rules.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def append_changelog(handle: str, entry: str) -> None:
    p = channel_dir(handle) / "changelog.md"
    header = "" if p.exists() else "# Strategy changelog\n\n"
    with p.open("a") as fh:
        fh.write(header + entry + "\n")
