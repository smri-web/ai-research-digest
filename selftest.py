"""Local-only preview: email one digest to yourself via Gmail SMTP.

Production delivery uses Buttondown (delivery.py). This module exists only so you can preview a
real email in your own inbox before going live. It reads Gmail credentials from a git-ignored
.env file; they never leave your machine and are never committed.
"""
import logging
import os
import smtplib
import ssl
from email.mime.text import MIMEText

log = logging.getLogger(__name__)


def send_via_gmail(subject: str, body_html: str, to_addr: str) -> bool:
    user = os.environ.get("GMAIL_ADDRESS")
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not (user and pw and to_addr):
        log.error("Set GMAIL_ADDRESS, GMAIL_APP_PASSWORD, and TEST_RECIPIENT in .env for --selftest")
        return False
    msg = MIMEText(body_html, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
            server.login(user, pw)
            server.sendmail(user, [to_addr], msg.as_string())
        return True
    except Exception as e:
        log.error("Gmail test send failed: %s", e)
        return False
