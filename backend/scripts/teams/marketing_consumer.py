"""Marketing Team — Kafka consumer demo.

Subscribes to: product.created
Simulates: sending Slack/social media notification.
"""

from __future__ import annotations

import asyncio
from typing import Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from scripts.teams._common import Colors, print_received, run_team_consumer


async def on_event(event: dict[str, Any], meta: dict[str, Any]) -> None:
    print_received(
        team_name="MARKETING TEAM",
        emoji="📢",
        color=Colors.MAGENTA,
        event=event,
        meta=meta,
    )

    topic = meta["topic"]

    if topic == "product.created":
        name = event.get("name", "?")
        sku = event.get("sku", "?")
        category_id = event.get("category_id", "?")
        image_url = event.get("image_url") or "no image"

        # Simulate Slack message format
        print(f"{Colors.MAGENTA}💬 Slack message posted:{Colors.RESET}")
        print(f"{Colors.MAGENTA}   ┌─ #new-products ────────────────────{Colors.RESET}")
        print(f"{Colors.MAGENTA}   │ 🎉 New product live!{Colors.RESET}")
        print(f"{Colors.MAGENTA}   │ 📦 {Colors.BOLD}{name}{Colors.RESET}")
        print(f"{Colors.MAGENTA}   │ 🏷  {sku}{Colors.RESET}")
        print(f"{Colors.MAGENTA}   │ 🖼  {image_url}{Colors.RESET}")
        print(f"{Colors.MAGENTA}   └────────────────────────────────────{Colors.RESET}")
        print(f"{Colors.MAGENTA}   → Creating Instagram story draft...{Colors.RESET}")
        print(f"{Colors.MAGENTA}   → Adding to content calendar...{Colors.RESET}")

    else:
        print(f"{Colors.YELLOW}   → Unhandled topic: {topic}{Colors.RESET}")

    print(f"{Colors.MAGENTA}{Colors.BOLD}{'─' * 70}{Colors.RESET}")


async def main() -> None:
    await run_team_consumer(
        team_name="Marketing Team",
        group_id="marketing-team",
        topics=["product.created"],
        emoji="📢",
        color=Colors.MAGENTA,
        on_event=on_event,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Marketing team consumer stopped.")
