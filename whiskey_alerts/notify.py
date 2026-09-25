"""Notification channels. Each one turns on when its environment variables are set.

  ntfy (phone push, no account):  NTFY_TOPIC [, NTFY_SERVER, NTFY_TOKEN]
  Pushover:                       PUSHOVER_TOKEN, PUSHOVER_USER
  Email over SMTP:                SMTP_HOST, SMTP_USER, SMTP_PASSWORD, EMAIL_TO
                                  [, SMTP_PORT=587, EMAIL_FROM]
  Discord webhook:                DISCORD_WEBHOOK_URL
  Slack webhook:                  SLACK_WEBHOOK_URL
"""

import logging
import os
import smtplib
from email.message import EmailMessage

import requests

log = logging.getLogger(__name__)


def _env(name, default=None):
    v = os.environ.get(name, "").strip()
    return v or default


def ntfy(title, body, url):
    topic = _env("NTFY_TOPIC")
    if not topic:
        return False
    server = _env("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    headers = {"Title": title.encode("utf-8"), "Tags": "tumbler_glass",
               "Priority": "high"}
    if url:
        headers["Click"] = url
    if _env("NTFY_TOKEN"):
        headers["Authorization"] = f"Bearer {_env('NTFY_TOKEN')}"
    requests.post(f"{server}/{topic}", data=body[:4000].encode("utf-8"),
                  headers=headers, timeout=20).raise_for_status()
    return True


def pushover(title, body, url):
    token, user = _env("PUSHOVER_TOKEN"), _env("PUSHOVER_USER")
    if not (token and user):
        return False
    data = {"token": token, "user": user, "title": title[:250],
            "message": body[:1024], "priority": 1}
    if url:
        data["url"] = url
    requests.post("https://api.pushover.net/1/messages.json", data=data,
                  timeout=20).raise_for_status()
    return True


def email(title, body, url):
    host, to = _env("SMTP_HOST"), _env("EMAIL_TO")
    if not (host and to):
        return False
    user = _env("SMTP_USER")
    msg = EmailMessage()
    msg["Subject"] = title
    msg["From"] = _env("EMAIL_FROM", user)
    msg["To"] = to
    msg.set_content(body)
    with smtplib.SMTP(host, int(_env("SMTP_PORT", "587")), timeout=30) as s:
        s.starttls()
        if user:
            s.login(user, _env("SMTP_PASSWORD", ""))
        s.send_message(msg)
    return True


def discord(title, body, url):
    hook = _env("DISCORD_WEBHOOK_URL")
    if not hook:
        return False
    requests.post(hook, json={"content": f"**{title}**\n{body}"[:2000]},
                  timeout=20).raise_for_status()
    return True


def slack(title, body, url):
    hook = _env("SLACK_WEBHOOK_URL")
    if not hook:
        return False
    requests.post(hook, json={"text": f"*{title}*\n{body}"},
                  timeout=20).raise_for_status()
    return True


CHANNELS = [ntfy, pushover, email, discord, slack]


def send(title, body, url=None):
    """Send to every configured channel; return how many succeeded."""
    sent = 0
    for channel in CHANNELS:
        try:
            if channel(title, body, url):
                log.info("notified via %s", channel.__name__)
                sent += 1
        except Exception as e:
            log.error("notification via %s failed: %s", channel.__name__, e)
    if not sent:
        log.warning("no notification channel configured or all failed; "
                    "printing instead")
        print(f"\n=== {title} ===\n{body}\n")
    return sent
