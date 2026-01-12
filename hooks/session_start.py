#!/usr/bin/env python3
"""Announce presence and inject urgent messages on session start."""
from utils import (
    get_nick,
    get_project,
    get_alert_count,
    fetch_alerts,
    send_status,
    join_project_channel,
    send_to_project,
)


def main() -> None:
    nick = get_nick()
    project = get_project()

    # Join/create the project-specific channel
    join_project_channel(project)

    # Announce to global #status (so all agents see who's online)
    send_status(f"[ONLINE] @{nick} | Project: {project}")

    # Also announce to the project channel
    send_to_project(f"[ONLINE] @{nick} joined", project)

    # Check for urgent messages
    alerts_count = get_alert_count()
    if alerts_count > 0:
        print(f"\n⚠️ URGENT MESSAGES ({alerts_count} in #alerts):")
        print(fetch_alerts(10))
        print("Review these before starting work.\n")

    # Let the agent know which project channel they're in
    print(f"\n📁 Project channel: #{project}")
    print("Use /chat to message your project channel, or #general for cross-project coordination.\n")


if __name__ == "__main__":
    main()
