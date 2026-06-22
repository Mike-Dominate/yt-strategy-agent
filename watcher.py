"""Long-running watcher: poll YouTube on a configurable interval."""

from __future__ import annotations

import time
import traceback
from datetime import datetime, timezone

from ingest import run_once
from logging_utils import configure_logging, get_logger
from settings import WATCH_INTERVAL_SECONDS

logger = get_logger("watcher")


def main() -> None:
    configure_logging()
    logger.info("starting watcher at %s", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    while True:
        cycle_start = datetime.now(timezone.utc)
        try:
            new = run_once()
            logger.info("%s ok - %s new video(s)", cycle_start.isoformat(timespec="seconds"), new)
        except Exception:
            logger.exception("%s ERROR", cycle_start.isoformat(timespec="seconds"))
            traceback.print_exc()
        time.sleep(WATCH_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
