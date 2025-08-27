#!/usr/bin/env python3
"""Send a simple message (or Adaptive Card fallback text) to a Microsoft Teams Incoming Webhook.

Usage:
  python scripts/notify_teams.py --webhook $TEAMS_WEBHOOK_URL --title "dbt Failure" --text "dbt run failed"

If JSON payload fails, falls back to plain text.
"""
from __future__ import annotations
import argparse
import json
import sys
import urllib.request

def build_payload(title: str, text: str, color: str | None = None) -> dict:
    # Basic Office 365 Connector card schema
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": color or "E81123",  # red default
        "summary": title,
        "title": title,
        "text": text,
    }
    return payload

def send(webhook: str, payload: dict):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(webhook, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 (external webhook)
        if resp.status >= 300:
            raise SystemExit(f"Teams webhook failed: {resp.status} {resp.read().decode()}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--webhook', required=True)
    ap.add_argument('--title', required=True)
    ap.add_argument('--text', required=True)
    ap.add_argument('--color')
    args = ap.parse_args()
    payload = build_payload(args.title, args.text, args.color)
    try:
        send(args.webhook, payload)
    except Exception as e:
        print(f"Primary send failed: {e}; attempting plain text fallback", file=sys.stderr)
        fallback = {"text": f"{args.title}: {args.text}"}
        try:
            send(args.webhook, fallback)
        except Exception as ee:
            raise SystemExit(f"Teams notification completely failed: {ee}")

if __name__ == '__main__':
    main()
