# ============================================================
# Accounts Receivable Chaser
# Copyright (c) 2026 Dsoles. All rights reserved.
# MIT License — see LICENSE file for details.
# ============================================================

"""
notifier.py — Daily digest sender via Discord or Telegram.

Sends a summary of today's AR chaser run using the openclaw CLI.
Format: X invoices chased, total outstanding, breakdown by tier.
"""

import logging
import shlex
import subprocess
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)

# Tier labels for human-readable digest
TIER_LABELS = {
    1: "Friendly (1–29 days)",
    2: "Professional (30–59 days)",
    3: "Firm (60–89 days)",
    4: "Final Notice (90+ days)",
}


def build_digest(
    chased: list[dict[str, Any]],
    skipped: int,
    total_outstanding: float,
    dry_run: bool,
) -> str:
    """
    Build the daily digest message string.

    Args:
        chased: List of invoice dicts that had emails sent today (include 'tier' key).
        skipped: Number of invoices skipped (already emailed this tier or paid).
        total_outstanding: Total dollar amount of all unpaid invoices.
        dry_run: Whether this was a dry run.

    Returns:
        Formatted digest string ready to send.
    """
    today = date.today().isoformat()
    mode_tag = " *(DRY RUN — no emails sent)*" if dry_run else ""

    # Breakdown by tier
    tier_counts: dict[int, int] = {}
    for inv in chased:
        t = inv.get("tier", 0)
        tier_counts[t] = tier_counts.get(t, 0) + 1

    tier_lines = ""
    for tier in sorted(tier_counts):
        label = TIER_LABELS.get(tier, f"Tier {tier}")
        count = tier_counts[tier]
        tier_lines += f"\n  • {label}: {count} invoice{'s' if count != 1 else ''}"

    if not tier_lines:
        tier_lines = "\n  • No emails sent today"

    digest = (
        f"📬 **AR Chaser Digest — {today}**{mode_tag}\n"
        f"{'─' * 40}\n"
        f"✉️  Emails sent: {len(chased)}\n"
        f"⏭️  Skipped (already sent / paid): {skipped}\n"
        f"💰 Total AR outstanding: ${total_outstanding:,.2f}\n"
        f"\n**By tier:**{tier_lines}"
    )

    return digest


def send_digest(digest: str, config: dict) -> bool:
    """
    Send the daily digest to Discord or Telegram via the openclaw CLI.

    Uses: openclaw message send --channel <channel> --target <id> --message <msg>

    Args:
        digest: The formatted digest string.
        config: Config dict with notify_channel, discord_channel_id, telegram_chat_id.

    Returns:
        True if sent successfully, False otherwise.
    """
    channel = config.get("notify_channel", "discord").lower()

    if channel == "discord":
        target = config.get("discord_channel_id", "")
        channel_flag = "discord"
    elif channel == "telegram":
        target = config.get("telegram_chat_id", "")
        channel_flag = "telegram"
    else:
        logger.error("Unknown notify_channel: '%s'. Use 'discord' or 'telegram'.", channel)
        return False

    if not target:
        logger.error(
            "No target ID configured for channel '%s'. "
            "Set DISCORD_CHANNEL_ID or TELEGRAM_CHAT_ID in .env",
            channel,
        )
        return False

    # Build the openclaw CLI command
    cmd = [
        "openclaw",
        "message",
        "send",
        "--channel", channel_flag,
        "--target", target,
        "--message", digest,
    ]

    logger.info("Sending digest via %s to %s", channel_flag, target)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info("Digest sent successfully via %s", channel_flag)
            return True
        else:
            logger.error(
                "openclaw CLI returned exit code %d: %s",
                result.returncode,
                result.stderr.strip(),
            )
            return False

    except FileNotFoundError:
        logger.error("openclaw CLI not found. Is it installed and in PATH?")
        return False
    except subprocess.TimeoutExpired:
        logger.error("openclaw CLI timed out sending digest")
        return False
    except Exception as e:
        logger.error("Unexpected error sending digest: %s", e)
        return False
