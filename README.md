# 📬 Accounts Receivable Chaser

> **Set it and forget it AR automation.** Automatically monitors unpaid invoices and sends professionally escalating email reminders — so you never have to chase a client manually again.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Requires: python-dotenv](https://img.shields.io/badge/requires-python--dotenv-green.svg)](https://pypi.org/project/python-dotenv/)

---

## What It Does

AR Chaser runs daily, reads your invoice list, and automatically emails overdue clients with escalating urgency — from a friendly nudge all the way to a final collections warning. It tracks every email sent so clients never get spammed, and posts a daily digest to your Discord or Telegram when it's done.

**One command. Run at 9 AM. Never chase an invoice manually again.**

---

## Features

- 📊 **Loads invoices** from CSV (or JSON) — drop-in simple
- ⚡ **4-tier escalating reminders** based on days overdue
- 🔁 **Deduplication** — each tier is sent exactly once per invoice
- 📧 **Gmail / Outlook / custom SMTP** support
- 🧪 **Dry run mode** — test without emailing anyone
- 📣 **Daily digest** to Discord or Telegram via openclaw CLI
- 📝 **Full audit log** written to `ar_chaser.log`
- 🍎 **macOS launchd** plist for hands-free daily scheduling

---

## Escalation Tiers

| Days Overdue | Tier | Tone | Subject Line |
|---|---|---|---|
| 1–29 days | 1 — Friendly | Warm, helpful | "Just checking in..." |
| 30–59 days | 2 — Professional | Direct, polite | "We haven't received payment..." |
| 60–89 days | 3 — Firm | Urgent, assertive | "Immediate payment required..." |
| 90+ days | 4 — Final Notice | Serious, legal tone | "Final notice before collections..." |

Each tier fires **once per invoice** — no repeated nagging at the same level. When the invoice ages into the next tier, the next email goes out automatically.

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/dsoles/accounts-receivable-chaser.git
cd accounts-receivable-chaser
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your SMTP credentials and settings
```

### 3. Add your invoices

```bash
cp data/sample_invoices.csv data/invoices.csv
# Edit data/invoices.csv with your real invoices
```

### 4. Test with dry run (safe — no emails sent)

```bash
python ar_chaser.py --dry-run
```

### 5. Go live

```bash
# Set DRY_RUN=false in .env, then:
python ar_chaser.py
```

---

## CSV Format

Your invoice file must be a CSV with these columns:

| Column | Type | Description | Example |
|---|---|---|---|
| `invoice_id` | string | Unique invoice identifier | `INV-001` |
| `client_name` | string | Client display name | `Acme Corp` |
| `client_email` | string | Client billing email | `billing@acme.com` |
| `amount` | number | Amount owed (USD) | `4500.00` |
| `due_date` | date | Due date (YYYY-MM-DD) | `2026-03-01` |
| `status` | string | Invoice status | `unpaid` |

**Example CSV:**

```csv
invoice_id,client_name,client_email,amount,due_date,status
INV-001,Acme Corporation,billing@acmecorp.com,4500.00,2026-03-01,unpaid
INV-002,Globex Systems,accounts@globex.com,1250.00,2026-03-15,unpaid
```

**Valid status values:** `unpaid` (will be chased), `paid` / `closed` / `void` (skipped)

> ⚠️ `data/invoices.csv` is in `.gitignore` — your real client data never gets committed.

---

## SMTP Setup

### Gmail (Recommended)

Gmail requires an **App Password** (not your regular password) when 2FA is enabled:

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Under "How you sign in to Google", click **2-Step Verification**
3. Scroll to the bottom → **App passwords**
4. Select app: "Mail", select device: "Other (custom name)" → type "AR Chaser"
5. Copy the 16-character password into your `.env` as `SMTP_PASSWORD`

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop
```

### Outlook / Microsoft 365

```env
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=you@yourcompany.com
SMTP_PASSWORD=your_password
```

### Custom SMTP

```env
SMTP_HOST=mail.yourhost.com
SMTP_PORT=587
SMTP_USER=noreply@yourcompany.com
SMTP_PASSWORD=your_password
```

---

## Customizing Email Templates

Templates live in `templates/` as HTML files:

| File | Tier | Used when |
|---|---|---|
| `friendly.html` | 1 | 1–29 days overdue |
| `professional.html` | 2 | 30–59 days overdue |
| `firm.html` | 3 | 60–89 days overdue |
| `final.html` | 4 | 90+ days overdue |

Each template supports these `{placeholders}`:

| Placeholder | Value |
|---|---|
| `{client_name}` | Client's name |
| `{invoice_id}` | Invoice number |
| `{amount}` | Dollar amount (e.g. `4,500.00`) |
| `{due_date}` | Original due date |
| `{days_overdue}` | Days past due |
| `{your_name}` | Your name (from `.env`) |
| `{your_company}` | Your company name (from `.env`) |

The subject line is read from the first line of each HTML file as a comment:

```html
<!-- subject: Your Subject Line Here with {invoice_id} placeholder -->
```

If a template file is missing or malformed, the built-in defaults are used automatically.

---

## Scheduling with launchd (macOS)

Run AR Chaser every day at 9:00 AM automatically:

### 1. Edit the plist

Open `launchd/com.dsoles.ar-chaser.plist` and update these paths to match your system:

```xml
<string>/Users/YOUR_USERNAME/path/to/accounts-receivable-chaser/ar_chaser.py</string>
```

### 2. Install the launchd job

```bash
cp launchd/com.dsoles.ar-chaser.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.dsoles.ar-chaser.plist
```

### 3. Verify it's scheduled

```bash
launchctl list | grep ar-chaser
```

### 4. Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/com.dsoles.ar-chaser.plist
rm ~/Library/LaunchAgents/com.dsoles.ar-chaser.plist
```

---

## Project Structure

```
accounts-receivable-chaser/
├── ar_chaser.py          # Main entry point
├── config.py             # .env loader
├── email_templates.py    # Template engine (4 tiers)
├── invoice_loader.py     # CSV/JSON loader + sent log
├── smtp_sender.py        # SMTP delivery with retry
├── notifier.py           # Daily digest (Discord/Telegram)
├── requirements.txt
├── .env.example          # Config template
├── .gitignore
├── data/
│   └── sample_invoices.csv
├── templates/
│   ├── friendly.html     # Tier 1: 1-29 days
│   ├── professional.html # Tier 2: 30-59 days
│   ├── firm.html         # Tier 3: 60-89 days
│   └── final.html        # Tier 4: 90+ days
└── launchd/
    └── com.dsoles.ar-chaser.plist
```

---

## CLI Options

```
usage: ar_chaser.py [-h] [--dry-run] [--csv PATH] [--no-digest]

options:
  --dry-run     Simulate without sending emails (overrides DRY_RUN in .env)
  --csv PATH    Override invoice CSV path from .env
  --no-digest   Skip posting the daily digest notification
```

---

## License

MIT License — © 2026 Dsoles. All rights reserved.

See [LICENSE](LICENSE) for full terms.
