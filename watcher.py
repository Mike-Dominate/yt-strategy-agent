"""Long-running watcher: poll YouTube every 10 minutes."""

from __future__ import annotations

import time
import traceback
from datetime import datetime, timezone

from ingest import run_once

INTERVAL_SECONDS = 600


def main() -> None:
    print(
        f"[watcher] starting at {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        flush=True,
    )
    while True:
        cycle_start = datetime.now(timezone.utc)
        try:
            new = run_once()
            print(
                f"[watcher] {cycle_start.isoformat(timespec='seconds')} ok — {new} new video(s)",
                flush=True,
            )
        except Exception:
            print(
                f"[watcher] {cycle_start.isoformat(timespec='seconds')} ERROR:",
                flush=True,
            )
            traceback.print_exc()
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
