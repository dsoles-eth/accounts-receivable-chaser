# ============================================================
# Accounts Receivable Chaser
# Copyright (c) 2026 Dsoles. All rights reserved.
# MIT License — see LICENSE file for details.
# ============================================================

"""
email_templates.py — Email template engine for escalating AR reminders.

Templates are loaded from the templates/ directory when available,
falling back to hardcoded defaults. Supports {placeholder} substitution.
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Template directory (relative to project root)
TEMPLATE_DIR = Path(__file__).parent / "templates"

# Map tier number → template filename stem
TIER_FILENAMES = {
    1: "friendly",
    2: "professional",
    3: "firm",
    4: "final",
}

# ── Hardcoded default templates (HTML) ───────────────────────────────────────

DEFAULTS: dict[int, dict[str, str]] = {
    1: {
        "subject": "Friendly Reminder: Invoice #{invoice_id} Due {due_date}",
        "body": """\
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <p>Hi {client_name},</p>
  <p>Just checking in — we wanted to give you a friendly heads-up that
     <strong>Invoice #{invoice_id}</strong> for <strong>${amount}</strong>
     was due on <strong>{due_date}</strong> ({days_overdue} days ago).</p>
  <p>If you've already sent payment, please disregard this message. If not,
     we'd appreciate you taking a moment to process it at your earliest convenience.</p>
  <p>Don't hesitate to reach out if you have any questions.</p>
  <p>Thanks so much,<br>
     <strong>{your_name}</strong><br>
     {your_company}</p>
</body>
</html>""",
    },
    2: {
        "subject": "Follow-Up: Invoice #{invoice_id} — Payment Overdue",
        "body": """\
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <p>Hi {client_name},</p>
  <p>We haven't received payment for <strong>Invoice #{invoice_id}</strong>
     totaling <strong>${amount}</strong>, which was due on <strong>{due_date}</strong>
     ({days_overdue} days ago).</p>
  <p>We'd appreciate your prompt attention to this matter. Please arrange payment
     at your earliest convenience, or contact us to discuss payment arrangements.</p>
  <p>If you believe this is an error, please let us know right away.</p>
  <p>Best regards,<br>
     <strong>{your_name}</strong><br>
     {your_company}</p>
</body>
</html>""",
    },
    3: {
        "subject": "URGENT: Invoice #{invoice_id} — Immediate Payment Required",
        "body": """\
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <p>Dear {client_name},</p>
  <p>This is a firm notice regarding <strong>Invoice #{invoice_id}</strong>
     for <strong>${amount}</strong>, now <strong>{days_overdue} days overdue</strong>
     (original due date: {due_date}).</p>
  <p>Despite previous reminders, we have not received payment. We require immediate
     settlement of this outstanding balance. Please process payment today or contact
     us immediately to arrange a payment plan.</p>
  <p>Failure to respond may result in additional action to recover this debt.</p>
  <p>Sincerely,<br>
     <strong>{your_name}</strong><br>
     {your_company}</p>
</body>
</html>""",
    },
    4: {
        "subject": "FINAL NOTICE: Invoice #{invoice_id} — Collections Action Pending",
        "body": """\
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <p>Dear {client_name},</p>
  <p><strong>This is your final notice.</strong></p>
  <p>Invoice <strong>#{invoice_id}</strong> for <strong>${amount}</strong> is now
     <strong>{days_overdue} days overdue</strong> (original due date: {due_date}).
     This account is severely past due and has not been resolved despite multiple notices.</p>
  <p>If we do not receive full payment or a confirmed payment arrangement within
     <strong>5 business days</strong>, we will be forced to refer this matter to a
     collections agency, which may impact your credit standing.</p>
  <p>To avoid this outcome, please contact us immediately at the information below.</p>
  <p>Regards,<br>
     <strong>{your_name}</strong><br>
     {your_company}</p>
</body>
</html>""",
    },
}


def _load_template_file(tier: int) -> dict[str, str] | None:
    """
    Attempt to load subject and body from the templates/ directory.

    Expects files named e.g. templates/friendly.html with a subject comment
    on the first line: <!-- subject: Your Subject Here -->

    Args:
        tier: Escalation tier (1-4).

    Returns:
        Dict with "subject" and "body" keys, or None if file not found.
    """
    filename = TIER_FILENAMES.get(tier)
    if not filename:
        return None

    template_path = TEMPLATE_DIR / f"{filename}.html"
    if not template_path.exists():
        return None

    content = template_path.read_text(encoding="utf-8")

    # Parse optional subject from first line comment: <!-- subject: ... -->
    lines = content.splitlines()
    subject = f"Invoice Reminder — Tier {tier}"  # fallback
    body_start = 0
    if lines and lines[0].strip().startswith("<!-- subject:"):
        subject = lines[0].replace("<!-- subject:", "").replace("-->", "").strip()
        body_start = 1

    body = "\n".join(lines[body_start:])
    return {"subject": subject, "body": body}


def get_template(tier: int, invoice: dict[str, Any]) -> tuple[str, str]:
    """
    Get the email subject and HTML body for a given escalation tier and invoice.

    Loads from templates/ directory first, falls back to hardcoded defaults.
    Performs {placeholder} substitution using invoice fields.

    Args:
        tier: Escalation tier (1=friendly, 2=professional, 3=firm, 4=final).
        invoice: Invoice dict with client_name, invoice_id, amount, due_date,
                 days_overdue, your_name, your_company fields.

    Returns:
        Tuple of (subject, body_html).
    """
    if tier not in (1, 2, 3, 4):
        logger.warning("Unknown tier %d, defaulting to tier 4", tier)
        tier = 4

    # Try file-based template first
    template = _load_template_file(tier)
    if template:
        logger.debug("Loaded template for tier %d from file", tier)
    else:
        template = DEFAULTS[tier]
        logger.debug("Using default template for tier %d", tier)

    # Build substitution context
    ctx = {
        "client_name": invoice.get("client_name", "Valued Client"),
        "invoice_id": invoice.get("invoice_id", "N/A"),
        "amount": f"{invoice.get('amount', 0):,.2f}",
        "due_date": str(invoice.get("due_date", "")),
        "days_overdue": str(invoice.get("days_overdue", 0)),
        "your_name": invoice.get("your_name", ""),
        "your_company": invoice.get("your_company", ""),
    }

    subject = template["subject"].format(**ctx)
    body = template["body"].format(**ctx)

    return subject, body


def get_plain_text(body_html: str) -> str:
    """
    Generate a plain-text fallback by stripping HTML tags.

    Args:
        body_html: HTML email body.

    Returns:
        Plain text version of the email.
    """
    import re
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", body_html)
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
