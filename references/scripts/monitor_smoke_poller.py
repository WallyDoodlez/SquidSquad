#!/usr/bin/env python3
"""Smoke-test poller for the Claude Code Monitor tool.

Emits N JSON event lines on stdout, one per `interval` seconds, then exits.
Mirrors what the future #7630 event_poll.py would do: produce one stdout line
per event so the Monitor tool can wake the watching agent line-by-line.

Usage:
    python monitor_smoke_poller.py [count] [interval_sec]
"""
import json
import sys
import time
import uuid
from datetime import datetime, timezone


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    interval = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0

    for i in range(1, count + 1):
        event = {
            "id": uuid.uuid4().hex[:8],
            "seq": i,
            "type": "smoke-test-event",
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "payload": f"event #{i} of {count}",
        }
        # Critical: line-buffered single-line JSON so Monitor sees one line per event.
        print(json.dumps(event), flush=True)
        if i < count:
            time.sleep(interval)


if __name__ == "__main__":
    main()
