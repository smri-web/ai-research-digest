import logging
import os
import requests

log = logging.getLogger(__name__)
API = "https://api.buttondown.email/v1/emails"


def send(subject: str, body_html: str) -> bool:
    key = os.environ.get("BUTTONDOWN_API_KEY")
    if not key:
        log.error("BUTTONDOWN_API_KEY not set")
        return False
    try:
        resp = requests.post(
            API,
            headers={"Authorization": f"Token {key}"},
            json={"subject": subject, "body": body_html, "status": "sent"},
            timeout=30,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        log.error("Buttondown send failed: %s", e)
        return False
