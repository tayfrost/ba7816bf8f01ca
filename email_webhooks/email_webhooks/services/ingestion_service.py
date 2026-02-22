import asyncio
"""
async def process_message(message: dict):
    try:
        headers = {h["name"]: h["value"] for h in message["payload"]["headers"]}
        subject = headers.get("Subject", "(no subject)")
        sender = headers.get("From", "(unknown sender)")
        print(f"📩 New email | From: {sender} | Subject: {subject}")
        await asyncio.sleep(0) 
    except Exception as e:
        print("process_message error:", e)
"""

import base64
import re
from typing import Optional, Dict, Any, Tuple

def _b64url_decode(data: str) -> str:
    if not data:
        return ""
    # Gmail uses base64url without padding sometimes
    padding = "=" * (-len(data) % 4)
    raw = base64.urlsafe_b64decode((data + padding).encode("utf-8"))
    return raw.decode("utf-8", errors="replace")

def _strip_html(html: str) -> str:
    # simple/cheap html stripping for logs
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _walk_parts(payload: Dict[str, Any]):
    stack = [payload]
    while stack:
        node = stack.pop()
        yield node
        for p in node.get("parts", []) or []:
            stack.append(p)

def extract_best_body(message: Dict[str, Any]) -> Tuple[str, str]:
    """
    Returns (body_text, body_type) where body_type is 'text/plain' or 'text/html' or ''.
    """
    payload = message.get("payload") or {}
    # 1) direct body
    mime = payload.get("mimeType", "")
    data = (payload.get("body") or {}).get("data")
    if data and mime in ("text/plain", "text/html"):
        body = _b64url_decode(data)
        if mime == "text/html":
            body = _strip_html(body)
        return body, mime

    # 2) multipart: pick best part
    plain_candidate: Optional[str] = None
    html_candidate: Optional[str] = None

    for part in _walk_parts(payload):
        mt = part.get("mimeType", "")
        pdata = (part.get("body") or {}).get("data")
        if not pdata:
            continue
        decoded = _b64url_decode(pdata)
        if mt == "text/plain" and not plain_candidate:
            plain_candidate = decoded
        elif mt == "text/html" and not html_candidate:
            html_candidate = _strip_html(decoded)

    if plain_candidate:
        return plain_candidate, "text/plain"
    if html_candidate:
        return html_candidate, "text/html"
    return "", ""

async def process_message(message: Dict[str, Any], user_email: str = ""):
    headers = {h["name"]: h["value"] for h in (message.get("payload", {}).get("headers") or [])}
    subject = headers.get("Subject", "(no subject)")
    sender = headers.get("From", "(unknown sender)")
    to = headers.get("To", "")
    date = headers.get("Date", "")

    labels = message.get("labelIds", []) or []
    direction = "sent" if "SENT" in labels else ("received" if "INBOX" in labels else "other")

    body, body_type = extract_best_body(message)
    preview = (body[:500] + "…") if len(body) > 500 else body

    print("—" * 60)
    print(f"📩 Gmail {direction.upper()} | user={user_email}")
    print(f"From: {sender}")
    print(f"To:   {to}")
    print(f"Date: {date}")
    print(f"Subj: {subject}")
    if preview:
        print(f"Body ({body_type}): {preview}")
    else:
        print("Body: (no decodable text/plain or text/html found)")