# ============================================================
# Accounts Receivable Chaser
# Copyright (c) 2026 Dsoles. All rights reserved.
# MIT License — see LICENSE file for details.
# ============================================================

"""
config.py — Load and validate environment configuration from .env file.
"""

import os
from dotenv import load_dotenv

# Load .env from project root
load_dotenv()


def get_config() -> dict:
    """
    Load all configuration from environment variables.

    Returns:
        dict: Configuration dictionary with all settings.
    """
    return {
        # SMTP settings
        "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "smtp_user": os.getenv("SMTP_USER", ""),
        "smtp_password": os.getenv("SMTP_PASSWORD", ""),

        # Sender identity
        "your_name": os.getenv("YOUR_NAME", "Your Name"),
        "your_company": os.getenv("YOUR_COMPANY", "Your Company LLC"),

        # Invoice data path
        "invoices_csv": os.getenv("INVOICES_CSV", "data/invoices.csv"),

        # Notification channel
        "notify_channel": os.getenv("NOTIFY_CHANNEL", "discord").lower(),
        "discord_channel_id": os.getenv("DISCORD_CHANNEL_ID", ""),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),

        # Sent log path
        "sent_log": os.getenv("SENT_LOG", "data/sent_log.json"),

        # Dry run mode — defaults to True for safety
        "dry_run": os.getenv("DRY_RUN", "true").lower() == "true",
    }
