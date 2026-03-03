import os
from fastapi import Request, HTTPException
from google.oauth2 import id_token as google_id_token
from google.auth.transport.requests import Request as GoogleRequest

WEBHOOK_ENDPOINT = os.getenv("GMAIL_WEBHOOK_ENDPOINT")

def verify_gmail_token(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    
    token = auth_header.split(" ", 1)[1].strip()
    
    try:
        info = google_id_token.verify_oauth2_token(
            token, GoogleRequest(), audience=WEBHOOK_ENDPOINT
        )
        iss = info.get("iss")
        if iss not in ("https://accounts.google.com", "accounts.google.com"):
            raise HTTPException(status_code=401, detail=f"Unexpected issuer: {iss}")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid JWT: {e}")