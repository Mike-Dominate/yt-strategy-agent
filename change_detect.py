"""Detect strategy shifts between consecutive video extractions."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from store import append_changelog, read_rules_json
from weighting import _embed

SUMMARY_DRIFT_THRESHOLD = 0.35
CONTRADICTION_CONFIDENCE = 0.6


def _semantic_distance(a: str, b: str) -> float:
    if not a.strip() or not b.strip():
        return 0.0
    embs = _embed([a, b])
    sim = float(np.dot(embs[0], embs[1]))
    return 1.0 - sim


def detect_and_log(
    handle: str, video_id: str, video_title: str, new_extraction: dict
) -> bool:
    prior = read_rules_json(handle)
    triggers: list[str] = []
    if prior:
        prior_summary = prior.get("strategy_summary", "")
        new_summary = new_extraction.get("strategy_summary", "")
        if _semantic_distance(prior_summary, new_summary) > SUMMARY_DRIFT_THRESHOLD:
            triggers.append("Strategy summary drifted significantly from prior state.")
        prior_rules = [
            r["text"]
            for r in prior.get("buy_rules", []) + prior.get("sell_rules", [])
            if r["effective_confidence"] >= CONTRADICTION_CONFIDENCE
        ]
        new_rules = [
            r.get("rule", "")
            for r in new_extraction.get("buy_rules", [])
            + new_extraction.get("sell_rules", [])
        ]
        if prior_rules and new_rules:
            embs_prior = _embed(prior_rules)
            embs_new = _embed(new_rules)
            for i, e_new in enumerate(embs_new):
                for j, e_prior in enumerate(embs_prior):
                    sim = float(np.dot(e_new, e_prior))
                    if 0.55 < sim < 0.78:
                        triggers.append(
                            f'Possible contradiction: new "{new_rules[i]}" vs prior "{prior_rules[j]}"'
                        )
                        break
    shift = new_extraction.get("strategy_shift") or {}
    if shift.get("changed"):
        triggers.append(
            f"Host explicitly noted a shift: {shift.get('what_changed','')} (vs {shift.get('vs_prior','')})"
        )
    if not triggers:
        return False
    today = datetime.now(timezone.utc).date().isoformat()
    quote = ""
    for src in (new_extraction.get("buy_rules") or []) + (
        new_extraction.get("sell_rules") or []
    ):
        if src.get("source_quote"):
            quote = src["source_quote"]
            break
    entry_lines = [
        f"## {today} — {video_title} ({video_id})",
    ]
    for t in triggers:
        entry_lines.append(f"- {t}")
    if quote:
        entry_lines.append(f'- Triggering quote: "{quote}"')
    append_changelog(handle, "\n".join(entry_lines))
    return True
