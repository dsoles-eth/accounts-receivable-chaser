# ============================================================
# Accounts Receivable Chaser
# Copyright (c) 2026 Dsoles. All rights reserved.
# MIT License — see LICENSE file for details.
# ============================================================

"""
smtp_sender.py — Email delivery via SMTP with retry logic.

Supports Gmail (port 587 TLS), Outlook, and custom SMTP servers.
All credentials are loaded from config — no hardcoded secrets.
"""

import logging
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

# Retry settings
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5


def send_email(
    to: str,
    subject: str,
    body_html: str,
    body_text: str,
    config: dict,
) -> bool:
    """
    Send an email via SMTP with up to 3 retry attempts.

    Supports STARTTLS on port 587 (Gmail, Outlook) and SSL on port 465.
    Falls back to plain SMTP for custom configurations.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body_html: HTML version of the email body.
        body_text: Plain-text fallback version.
        config: Configuration dict with smtp_host, smtp_port, smtp_user,
                smtp_password, your_name, your_company keys.

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    smtp_host = config["smtp_host"]
    smtp_port = config["smtp_port"]
    smtp_user = config["smtp_user"]
    smtp_password = config["smtp_password"]
    from_name = config.get("your_name", "")
    from_company = config.get("your_company", "")

    if not smtp_user or not smtp_password:
        logger.error("SMTP credentials not configured. Set SMTP_USER and SMTP_PASSWORD in .env")
        return False

    # Build the MIME multipart message (HTML + plain text)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} — {from_company} <{smtp_user}>" if from_name else smtp_user
    msg["To"] = to

    # Attach plain text first (lower priority), then HTML (higher priority)
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if smtp_port == 465:
                # SSL connection (less common)
                with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30) as server:
                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_user, to, msg.as_string())
            else:
                # STARTTLS connection — default for Gmail (587) and Outlook (587)
                with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_user, to, msg.as_string())

            logger.info("Email sent to %s (attempt %d/%d)", to, attempt, MAX_RETRIES)
            return True

        except smtplib.SMTPAuthenticationError as e:
            # Auth errors won't be fixed by retrying
            logger.error("SMTP authentication failed: %s", e)
            return False

        except (smtplib.SMTPException, OSError) as e:
            last_error = e
            logger.warning(
                "Email attempt %d/%d failed for %s: %s",
                attempt,
                MAX_RETRIES,
                to,
                e,
            )
            if attempt < MAX_RETRIES:
                logger.info("Retrying in %d seconds...", RETRY_BACKOFF_SECONDS)
                time.sleep(RETRY_BACKOFF_SECONDS)

    logger.error("All %d attempts failed for %s. Last error: %s", MAX_RETRIES, to, last_error)
    return False
