#!/usr/bin/env python3
"""Block stop if urgent messages unread."""
import json

from utils import get_nick, get_alert_count, send_status


def main() -> None:
    alerts_count = get_alert_count()

    if alerts_count > 0:
        output = {
            "decision": "block",
            "reason": f"!! {alerts_count} unread messages in #alerts. Run `/listen #alerts` before stopping."
        }
    else:
        nick = get_nick()
        send_status(f"[OFFLINE] @{nick} session ended")
        output = {"decision": "allow"}

    print(json.dumps(output))


if __name__ == "__main__":
    main()
