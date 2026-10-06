"""Sales Team — Kafka consumer demo.

Subscribes to: product.created, order.placed
Simulates: notifying sales team about new products and orders.
"""

from __future__ import annotations

import asyncio
from typing import Any

# Ensure src/ is on path when run as script
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from scripts.teams._common import Colors, print_received, run_team_consumer


async def on_event(event: dict[str, Any], meta: dict[str, Any]) -> None:
    print_received(
        team_name="SALES TEAM",
        emoji="📈",
        color=Colors.GREEN,
        event=event,
        meta=meta,
    )

    topic = meta["topic"]

    if topic == "product.created":
        name = event.get("name", "?")
        sku = event.get("sku", "?")
        price = event.get("price", "?")
        category_id = event.get("category_id", "?")

        print(f"{Colors.GREEN}💼 Sales team action:{Colors.RESET}")
        print(f"{Colors.GREEN}   → New product ready for campaign: {Colors.BOLD}{name}{Colors.RESET}")
        print(f"{Colors.GREEN}   → SKU: {sku} | Price: ${price} | Category ID: {category_id}{Colors.RESET}")
        print(f"{Colors.GREEN}   → Adding to 'potential bestsellers' list...{Colors.RESET}")
        print(f"{Colors.GREEN}   → Sending weekly digest to sales@company.com...{Colors.RESET}")

    elif topic == "order.placed":
        order_id = event.get("order_id", "?")
        total = event.get("total_amount", "?")
        user_id = event.get("user_id", "?")

        print(f"{Colors.GREEN}💰 Sales team action:{Colors.RESET}")
        print(f"{Colors.GREEN}   → Order #{order_id} received — total ${total}{Colors.RESET}")
        print(f"{Colors.GREEN}   → Customer user_id: {user_id}{Colors.RESET}")
        print(f"{Colors.GREEN}   → Updating sales dashboard KPIs...{Colors.RESET}")

    else:
        print(f"{Colors.YELLOW}   → Unhandled topic: {topic}{Colors.RESET}")

    print(f"{Colors.GREEN}{Colors.BOLD}{'─' * 70}{Colors.RESET}")


async def main() -> None:
    await run_team_consumer(
        team_name="Sales Team",
        group_id="sales-team",
        topics=["product.created", "order.placed"],
        emoji="📈",
        color=Colors.GREEN,
        on_event=on_event,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Sales team consumer stopped.")
