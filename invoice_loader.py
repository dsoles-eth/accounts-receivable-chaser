# ============================================================
# Accounts Receivable Chaser
# Copyright (c) 2026 Dsoles. All rights reserved.
# MIT License — see LICENSE file for details.
# ============================================================

"""
invoice_loader.py — Invoice data management: load, validate, and track sent reminders.
"""

import csv
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Regex for basic email validation
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Required fields in each invoice record
REQUIRED_FIELDS = {"invoice_id", "client_name", "client_email", "amount", "due_date", "status"}


def _validate_invoice(row: dict[str, Any], line_num: int) -> dict[str, Any] | None:
    """
    Validate a single invoice row.

    Args:
        row: Raw row dict from CSV/JSON.
        line_num: Source line number for error messages.

    Returns:
        Cleaned invoice dict, or None if validation fails.
    """
    # Check required fields
    missing = REQUIRED_FIELDS - set(row.keys())
    if missing:
        logger.warning("Line %d: missing fields %s — skipping", line_num, missing)
        return None

    # Validate email
    email = row["client_email"].strip()
    if not EMAIL_RE.match(email):
        logger.warning("Line %d: invalid email '%s' — skipping", line_num, email)
        return None

    # Validate and parse due_date
    due_date_str = row["due_date"].strip()
    try:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
    except ValueError:
        logger.warning("Line %d: invalid due_date '%s' (expected YYYY-MM-DD) — skipping", line_num, due_date_str)
        return None

    # Validate amount
    try:
        amount = float(str(row["amount"]).replace(",", "").replace("$", "").strip())
    except ValueError:
        logger.warning("Line %d: invalid amount '%s' — skipping", line_num, row["amount"])
        return None

    return {
        "invoice_id": str(row["invoice_id"]).strip(),
        "client_name": str(row["client_name"]).strip(),
        "client_email": email,
        "amount": amount,
        "due_date": due_date,
        "status": str(row["status"]).strip().lower(),
    }


def load_invoices(csv_path: str) -> list[dict[str, Any]]:
    """
    Load and validate invoices from a CSV file.

    Expected columns: invoice_id, client_name, client_email, amount, due_date, status

    Args:
        csv_path: Path to the CSV file.

    Returns:
        List of validated invoice dicts. Invalid rows are skipped with a warning.
    """
    path = Path(csv_path)
    if not path.exists():
        logger.error("Invoice CSV not found: %s", csv_path)
        return []

    invoices: list[dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for line_num, row in enumerate(reader, start=2):  # start=2 accounts for header
            invoice = _validate_invoice(dict(row), line_num)
            if invoice:
                invoices.append(invoice)

    logger.info("Loaded %d valid invoices from %s", len(invoices), csv_path)
    return invoices


def load_invoices_json(json_path: str) -> list[dict[str, Any]]:
    """
    Load and validate invoices from a JSON file.

    Expected format: list of objects with the same fields as the CSV.

    Args:
        json_path: Path to the JSON file.

    Returns:
        List of validated invoice dicts. Invalid rows are skipped with a warning.
    """
    path = Path(json_path)
    if not path.exists():
        logger.error("Invoice JSON not found: %s", json_path)
        return []

    with open(path, encoding="utf-8") as f:
        try:
            raw = json.load(f)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON: %s", e)
            return []

    if not isinstance(raw, list):
        logger.error("JSON invoice file must contain a list at the top level")
        return []

    invoices: list[dict[str, Any]] = []
    for line_num, row in enumerate(raw, start=1):
        invoice = _validate_invoice(row, line_num)
        if invoice:
            invoices.append(invoice)

    logger.info("Loaded %d valid invoices from %s", len(invoices), json_path)
    return invoices


def load_sent_log(log_path: str) -> set[tuple[str, int]]:
    """
    Load the set of (invoice_id, tier) pairs that have already been emailed.

    Args:
        log_path: Path to the sent log JSON file.

    Returns:
        Set of (invoice_id, tier) tuples already sent.
    """
    path = Path(log_path)
    if not path.exists():
        return set()

    with open(path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            logger.warning("Sent log corrupted, starting fresh: %s", log_path)
            return set()

    # Stored as list of [invoice_id, tier] pairs
    return {(entry["invoice_id"], entry["tier"]) for entry in data if "invoice_id" in entry and "tier" in entry}


def save_sent_log(log_path: str, entry: dict[str, Any]) -> None:
    """
    Append a sent-email record to the log file.

    Args:
        log_path: Path to the sent log JSON file.
        entry: Dict with at minimum {"invoice_id": str, "tier": int, "sent_at": str}.
    """
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing log
    existing: list[dict[str, Any]] = []
    if path.exists():
        with open(path, encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []

    existing.append(entry)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, default=str)
