# ============================================================
# Accounts Receivable Chaser
# Copyright (c) 2026 Dsoles. All rights reserved.
# MIT License — see LICENSE file for details.
# ============================================================

"""
ar_chaser.py — Main entry point for the Accounts Receivable Chaser.

Loads invoices, calculates days overdue, sends escalating email reminders
via SMTP, tracks sent reminders to prevent duplicates, and posts a daily
digest to Discord or Telegram.

Usage:
    python ar_chaser.py
    python ar_chaser.py --dry-run       # Override: force dry run
    python ar_chaser.py --csv path.csv  # Override invoice CSV path
"""

import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

from config import get_config
from email_templates import get_plain_text, get_template
from invoice_loader import load_invoices, load_sent_log, save_sent_log
from notifier import build_digest, send_digest
from smtp_sender import send_email

# ── Logging setup ──────────────────────────────────────────────────────────────

LOG_FILE = "ar_chaser.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("ar_chaser")

# ── Escalation tier thresholds (days overdue) ─────────────────────────────────

TIERS = [
    (90, 4),   # 90+ days → Final notice
    (60, 3),   # 60–89 days → Firm notice
    (30, 2),   # 30–59 days → Professional follow-up
    (1,  1),   # 1–29 days  → Friendly reminder
]


def get_tier(days_overdue: int) -> int | None:
    """
    Determine the escalation tier based on days overdue.

    Args:
        days_overdue: Number of days past the due date.

    Returns:
        Tier number (1–4), or None if not yet overdue.
    """
    for threshold, tier in TIERS:
        if days_overdue >= threshold:
            return tier
    return None  # Not overdue yet


def process_invoices(
    invoices: list[dict[str, Any]],
    sent_log: set[tuple[str, int]],
    config: dict,
    dry_run: bool,
) -> tuple[list[dict[str, Any]], int, float]:
    """
    Process all invoices: determine tier, send emails, track results.

    Args:
        invoices: List of validated invoice dicts.
        sent_log: Set of (invoice_id, tier) pairs already sent.
        config: Configuration dict.
        dry_run: If True, log what would be sent but don't actually send.

    Returns:
        Tuple of (chased_invoices, skipped_count, total_outstanding).
    """
    today = date.today()
    chased: list[dict[str, Any]] = []
    skipped = 0
    total_outstanding = 0.0

    # Add sender identity to config for template substitution
    invoice_extra = {
        "your_name": config["your_name"],
        "your_company": config["your_company"],
    }

    for inv in invoices:
        # Only process unpaid invoices
        if inv["status"] in ("paid", "closed", "void"):
            logger.debug("Invoice %s is %s — skipping", inv["invoice_id"], inv["status"])
            continue

        # Calculate days overdue
        days_overdue = (today - inv["due_date"]).days
        total_outstanding += inv["amount"]

        if days_overdue < 1:
            logger.debug("Invoice %s not yet due (%d days) — skipping", inv["invoice_id"], days_overdue)
            skipped += 1
            continue

        tier = get_tier(days_overdue)
        if tier is None:
            skipped += 1
            continue

        # Dedup: skip if we've already sent this tier for this invoice
        if (inv["invoice_id"], tier) in sent_log:
            logger.info(
                "Invoice %s: tier %d already sent — skipping",
                inv["invoice_id"],
                tier,
            )
            skipped += 1
            continue

        # Build email content
        invoice_ctx = {**inv, **invoice_extra, "days_overdue": days_overdue}
        subject, body_html = get_template(tier, invoice_ctx)
        body_text = get_plain_text(body_html)

        if dry_run:
            logger.info(
                "[DRY RUN] Would send Tier %d email to %s (%s) for invoice %s ($%.2f, %d days overdue)",
                tier,
                inv["client_name"],
                inv["client_email"],
                inv["invoice_id"],
                inv["amount"],
                days_overdue,
            )
            # Record as sent in dry run too, so we know what would have gone
            chased.append({**inv, "tier": tier, "days_overdue": days_overdue})
        else:
            logger.info(
                "Sending Tier %d email to %s (%s) for invoice %s ($%.2f, %d days overdue)",
                tier,
                inv["client_name"],
                inv["client_email"],
                inv["invoice_id"],
                inv["amount"],
                days_overdue,
            )
            success = send_email(
                to=inv["client_email"],
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                config=config,
            )

            if success:
                # Record to sent log so we don't resend
                entry = {
                    "invoice_id": inv["invoice_id"],
                    "tier": tier,
                    "sent_at": datetime.utcnow().isoformat(),
                    "client_email": inv["client_email"],
                    "amount": inv["amount"],
                    "days_overdue": days_overdue,
                }
                save_sent_log(config["sent_log"], entry)
                sent_log.add((inv["invoice_id"], tier))  # Update in-memory set too
                chased.append({**inv, "tier": tier, "days_overdue": days_overdue})
            else:
                logger.error(
                    "Failed to send email for invoice %s to %s",
                    inv["invoice_id"],
                    inv["client_email"],
                )
                skipped += 1

    return chased, skipped, total_outstanding


def main() -> None:
    """
    Main entry point. Parses args, loads config, processes invoices,
    sends emails, and posts daily digest.
    """
    # ── Argument parsing ──────────────────────────────────────────────────────
    parser = argparse.ArgumentParser(
        description="Accounts Receivable Chaser — automated invoice reminder agent"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate sending without actually emailing anyone",
    )
    parser.add_argument(
        "--csv",
        metavar="PATH",
        help="Override invoice CSV path from .env",
    )
    parser.add_argument(
        "--no-digest",
        action="store_true",
        help="Skip posting the daily digest notification",
    )
    args = parser.parse_args()

    # ── Load configuration ────────────────────────────────────────────────────
    config = get_config()

    # CLI flags override .env settings
    dry_run = args.dry_run or config["dry_run"]
    invoices_csv = args.csv or config["invoices_csv"]

    if dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE — no emails will actually be sent")
        logger.info("=" * 60)

    logger.info("Starting AR Chaser run | CSV: %s | Dry run: %s", invoices_csv, dry_run)

    # ── Load invoices ─────────────────────────────────────────────────────────
    invoices = load_invoices(invoices_csv)
    if not invoices:
        logger.warning("No valid invoices found. Exiting.")
        return

    # ── Load sent log (dedup) ─────────────────────────────────────────────────
    sent_log = load_sent_log(config["sent_log"])
    logger.info("Loaded %d prior sent records", len(sent_log))

    # ── Process invoices and send emails ──────────────────────────────────────
    chased, skipped, total_outstanding = process_invoices(
        invoices=invoices,
        sent_log=sent_log,
        config=config,
        dry_run=dry_run,
    )

    logger.info(
        "Run complete — Sent: %d | Skipped: %d | Total AR outstanding: $%.2f",
        len(chased),
        skipped,
        total_outstanding,
    )

    # ── Send daily digest ─────────────────────────────────────────────────────
    if not args.no_digest:
        digest = build_digest(
            chased=chased,
            skipped=skipped,
            total_outstanding=total_outstanding,
            dry_run=dry_run,
        )
        logger.info("Sending daily digest to %s", config["notify_channel"])
        send_digest(digest, config)
    else:
        logger.info("Digest skipped (--no-digest flag)")


if __name__ == "__main__":
    main()
