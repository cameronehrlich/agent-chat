#!/usr/bin/env python3
"""Auto-fetch and inject urgent messages on user prompt."""
from utils import get_alert_count, fetch_alerts


def main() -> None:
    alerts_count = get_alert_count()
    if alerts_count > 0:
        print(f"\n!! URGENT ({alerts_count} unread in #alerts):")
        print(fetch_alerts(5))
        print("Consider addressing these before continuing.\n")


if __name__ == "__main__":
    main()
