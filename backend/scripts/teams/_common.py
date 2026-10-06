"""Shared utilities for team consumer demos.

Each team runs its own process that subscribes to a Kafka topic and
prints user-visible messages (simulating Slack/email notifications).
"""

from __future__ import annotations

import asyncio
import json
import signal
import sys
from datetime import UTC, datetime
from typing import Any

from aiokafka import AIOKafkaConsumer

from shopify_cart.config import get_settings
from shopify_cart.logging_config import configure_logging

# ═══════════════════════════════════════════════════════════
# ANSI colors for terminal output (makes demo pop)
# ═══════════════════════════════════════════════════════════
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"


def timestamp() -> str:
    return datetime.now(UTC).strftime("%H:%M:%S")


async def run_team_consumer(
    *,
    team_name: str,
    group_id: str,
    topics: list[str],
    emoji: str,
    color: str,
    on_event,  # async callable
) -> None:
    """Run a consumer that processes each event via `on_event`.

    Args:
        team_name: Human-readable team name (e.g., "Sales Team")
        group_id: Kafka consumer group id (unique per team)
        topics: List of Kafka topics to subscribe to
        emoji: Display emoji for terminal output
        color: ANSI color for terminal output
        on_event: async function(event_type, payload, meta) -> None
    """
    settings = get_settings()
    configure_logging(debug=False, json_logs=False)

    print(f"\n{color}{Colors.BOLD}{'═' * 70}{Colors.RESET}")
    print(f"{color}{Colors.BOLD}{emoji}  {team_name} — Kafka Consumer{Colors.RESET}")
    print(f"{color}{Colors.BOLD}{'═' * 70}{Colors.RESET}")
    print(f"{Colors.CYAN}Consumer group: {Colors.WHITE}{group_id}{Colors.RESET}")
    print(f"{Colors.CYAN}Subscribed topics:{Colors.WHITE} {', '.join(topics)}{Colors.RESET}")
    print(f"{Colors.CYAN}Bootstrap: {Colors.WHITE}{settings.kafka_bootstrap_servers}{Colors.RESET}")
    print(f"{color}{Colors.BOLD}{'═' * 70}{Colors.RESET}\n")

    consumer = AIOKafkaConsumer(
        *topics,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=group_id,
        auto_offset_reset="latest",  # Only new events
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        enable_auto_commit=True,
    )

    # Graceful shutdown on Ctrl+C
    stop_event = asyncio.Event()

    def _on_signal(sig: int) -> None:
        print(f"\n{Colors.YELLOW}⚠  Received signal {sig} — stopping...{Colors.RESET}")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _on_signal, sig)
        except NotImplementedError:
            # Windows doesn't support signal handlers on event loop
            signal.signal(sig, lambda s, f: _on_signal(s))

    await consumer.start()
    print(f"{color}✓ Connected to Kafka — waiting for events...{Colors.RESET}\n")

    try:
        while not stop_event.is_set():
            try:
                msg = await asyncio.wait_for(consumer.getone(), timeout=1.0)
            except TimeoutError:
                continue

            topic = msg.topic
            event = msg.value or {}
            meta = {
                "topic": topic,
                "partition": msg.partition,
                "offset": msg.offset,
                "key": msg.key.decode("utf-8") if msg.key else None,
            }

            # Call the team-specific handler
            try:
                await on_event(event, meta)
            except Exception as exc:  # noqa: BLE001
                print(
                    f"{Colors.RED}✗ Error handling event from {topic}: {exc}{Colors.RESET}"
                )
    finally:
        await consumer.stop()
        print(f"\n{color}✓ {team_name} disconnected.{Colors.RESET}")


def print_received(
    *,
    team_name: str,
    emoji: str,
    color: str,
    event: dict[str, Any],
    meta: dict[str, Any],
) -> None:
    """Print a prominent message header for a received event."""
    print(f"\n{color}{Colors.BOLD}{'─' * 70}{Colors.RESET}")
    print(
        f"{color}{Colors.BOLD}{emoji}  {team_name} → message received "
        f"at {timestamp()}{Colors.RESET}"
    )
    print(f"{color}{Colors.BOLD}{'─' * 70}{Colors.RESET}")
    print(f"{Colors.CYAN}Topic:    {Colors.WHITE}{meta['topic']}{Colors.RESET}")
    print(f"{Colors.CYAN}Key:      {Colors.WHITE}{meta.get('key') or '—'}{Colors.RESET}")
    print(
        f"{Colors.CYAN}Partition:{Colors.WHITE} {meta['partition']}  "
        f"{Colors.CYAN}Offset: {Colors.WHITE}{meta['offset']}{Colors.RESET}"
    )
