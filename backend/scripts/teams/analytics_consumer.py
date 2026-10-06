"""Analytics Team — Kafka consumer demo.

Subscribes to: product.created, order.placed, cart.updated
Simulates: aggregating events into data warehouse.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from scripts.teams._common import Colors, print_received, run_team_consumer


# In-memory counters (demo only — real analytics uses a DB)
_event_counts: dict[str, int] = defaultdict(int)


async def on_event(event: dict[str, Any], meta: dict[str, Any]) -> None:
    print_received(
        team_name="ANALYTICS TEAM",
        emoji="📊",
        color=Colors.CYAN,
        event=event,
        meta=meta,
    )

    topic = meta["topic"]
    _event_counts[topic] += 1

    if topic == "product.created":
        product_id = event.get("product_id", "?")
        category_id = event.get("category_id", "?")
        price = event.get("price", 0)

        print(f"{Colors.CYAN}📈 Analytics action:{Colors.RESET}")
        print(f"{Colors.CYAN}   → Insert into warehouse.product_events{Colors.RESET}")
        print(f"{Colors.CYAN}   │     product_id={product_id} | category_id={category_id} | price=${price}{Colors.RESET}")
        print(f"{Colors.CYAN}   → Update dashboard: total_products += 1{Colors.RESET}")

    elif topic == "order.placed":
        order_id = event.get("order_id", "?")
        total = event.get("total_amount", 0)

        print(f"{Colors.CYAN}📈 Analytics action:{Colors.RESET}")
        print(f"{Colors.CYAN}   → Insert into warehouse.order_events{Colors.RESET}")
        print(f"{Colors.CYAN}   │     order_id={order_id} | total=${total}{Colors.RESET}")
        print(f"{Colors.CYAN}   → Update daily_sales table{Colors.RESET}")

    elif topic == "cart.updated":
        cart_id = event.get("cart_id", "?")
        item_count = event.get("item_count", 0)

        print(f"{Colors.CYAN}📈 Analytics action:{Colors.RESET}")
        print(f"{Colors.CYAN}   → Track user engagement: cart_id={cart_id} items={item_count}{Colors.RESET}")

    # Print rolling counters (fun visual)
    print(f"{Colors.CYAN}📊 Session totals:{Colors.RESET}")
    for t, count in sorted(_event_counts.items()):
        print(f"{Colors.CYAN}   • {t}: {count} event(s){Colors.RESET}")

    print(f"{Colors.CYAN}{Colors.BOLD}{'─' * 70}{Colors.RESET}")


async def main() -> None:
    await run_team_consumer(
        team_name="Analytics Team",
        group_id="analytics-team",
        topics=["product.created", "order.placed", "cart.updated"],
        emoji="📊",
        color=Colors.CYAN,
        on_event=on_event,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Analytics team consumer stopped.")
