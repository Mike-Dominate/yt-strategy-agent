"""SMTP email sender for per-video briefs."""

from __future__ import annotations

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Iterable

from dotenv import dotenv_values

ROOT = Path(__file__).parent
_ENV = {
    **dotenv_values(ROOT / ".env"),
    **{k: v for k, v in os.environ.items() if k.startswith("SMTP_") or k == "EMAIL_TO"},
}


def _cfg() -> dict[str, str]:
    needed = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "EMAIL_TO"]
    cfg = {k: _ENV.get(k, "") for k in needed}
    missing = [k for k, v in cfg.items() if not v]
    if missing:
        raise RuntimeError(f"missing SMTP env vars: {missing}")
    cfg["SMTP_PASSWORD"] = cfg["SMTP_PASSWORD"].replace(" ", "")
    return cfg


def _format_rules(rules: list[dict], top: int = 5) -> str:
    if not rules:
        return "_(none)_"
    lines = []
    for r in rules[:top]:
        text = r.get("text") or r.get("rule") or r.get("note") or ""
        conf = r.get("effective_confidence", r.get("confidence", 0.0))
        lines.append(f"  • ({conf:.2f}) {text}")
    return "\n".join(lines)


def _diff_rule_sets(prior: list[dict], new: list[dict]) -> tuple[list[str], list[str]]:
    """Return (added_texts, removed_texts) by simple text equality."""
    prior_texts = {(r.get("text") or "").strip() for r in (prior or [])}
    new_texts = {(r.get("text") or "").strip() for r in (new or [])}
    added = sorted(new_texts - prior_texts)
    removed = sorted(prior_texts - new_texts)
    return [t for t in added if t], [t for t in removed if t]


def build_email_body(
    channel_title: str,
    channel_handle: str,
    video: dict,
    extraction: dict,
    prior_rules: dict | None,
    new_rules: dict,
    change_logged: bool,
    impact_paragraph: str,
    strategy_spec: str | None,
) -> str:
    vid = video["video_id"]
    url = f"https://www.youtube.com/watch?v={vid}"
    summary = (extraction.get("strategy_summary") or "").strip() or "_(none)_"
    sections: list[str] = []
    sections.append(
        f"NEW VIDEO — {channel_title}\n{video['title']}\n{url}\nPublished: {video.get('published_at','?')}\n"
    )
    if change_logged:
        sections.append("⚠️  STRATEGY SHIFT DETECTED — see changelog.md\n")
    sections.append(f"IMPACT ON TRADING STRATEGY\n{impact_paragraph}\n")
    sections.append(f"WHAT THIS VIDEO SAYS\n{summary}\n")
    sections.append(
        "KEY EXTRACTS FROM THIS VIDEO\n"
        f"Buy rules:\n{_format_rules(extraction.get('buy_rules', []), top=3)}\n\n"
        f"Sell rules:\n{_format_rules(extraction.get('sell_rules', []), top=3)}\n\n"
        f"Risk notes:\n{_format_rules(extraction.get('risk_notes', []), top=2)}\n\n"
        f"Timing notes:\n{_format_rules(extraction.get('timing_notes', []), top=2)}\n"
    )
    if prior_rules is not None:
        added_buy, removed_buy = _diff_rule_sets(
            prior_rules.get("buy_rules", []), new_rules.get("buy_rules", [])
        )
        added_sell, removed_sell = _diff_rule_sets(
            prior_rules.get("sell_rules", []), new_rules.get("sell_rules", [])
        )
        diff_lines: list[str] = []
        if added_buy:
            diff_lines.append("  + buy rule: " + "\n  + buy rule: ".join(added_buy))
        if removed_buy:
            diff_lines.append("  − buy rule: " + "\n  − buy rule: ".join(removed_buy))
        if added_sell:
            diff_lines.append("  + sell rule: " + "\n  + sell rule: ".join(added_sell))
        if removed_sell:
            diff_lines.append(
                "  − sell rule: " + "\n  − sell rule: ".join(removed_sell)
            )
        sections.append(
            "WHAT CHANGED IN THE ROLLING RULES\n"
            + (
                "\n".join(diff_lines)
                if diff_lines
                else "  (no rule-level changes; weighting may have shifted confidence)"
            )
            + "\n"
        )
    sections.append(
        "CURRENT ROLLING STRATEGY\n"
        f"Summary: {(new_rules.get('strategy_summary') or '').strip() or '(building)'}\n\n"
        f"Top buy rules:\n{_format_rules(new_rules.get('buy_rules', []), top=5)}\n\n"
        f"Top risk notes:\n{_format_rules(new_rules.get('risk_notes', []), top=3)}\n"
    )
    if strategy_spec:
        sections.append(
            "LIVE PAPER-TRADING SPEC (current)\n" + strategy_spec.strip() + "\n"
        )
    sections.append(
        "FILES ON THE VPS\n"
        f"  channels/{channel_handle}/strategy.md      — full living strategy\n"
        f"  channels/{channel_handle}/strategy_spec.md — paper-trading spec (if applicable)\n"
        f"  channels/{channel_handle}/changelog.md     — strategy shifts log\n"
        f"  channels/{channel_handle}/videos/{vid}.md  — this video's full extract\n"
    )
    return "\n".join(sections)


def send_email(subject: str, body: str) -> None:
    cfg = _cfg()
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["SMTP_USER"]
    msg["To"] = cfg["EMAIL_TO"]
    msg.attach(MIMEText(body, "plain"))
    context = ssl.create_default_context()
    with smtplib.SMTP(cfg["SMTP_HOST"], int(cfg["SMTP_PORT"])) as server:
        server.starttls(context=context)
        server.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
        server.send_message(msg)
