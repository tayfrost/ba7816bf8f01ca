import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse

from core.db import init_db
from providers.factory import get_provider
from services.ingestion_service import process_message

load_dotenv()
print("ENV CHECK:",
      "BASE_URL=", os.getenv("BASE_URL"),
      "GMAIL_CLIENT_ID=", os.getenv("GMAIL_CLIENT_ID"),
      "GMAIL_CLIENT_SECRET=", "set" if os.getenv("GMAIL_CLIENT_SECRET") else None)


app = FastAPI()

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def root():
    return {"ok": True}

# ---- OAuth (Gmail) ----

@app.get("/auth/login")
def gmail_login():
    provider = get_provider("gmail")
    auth_url = provider.get_auth_url()
    return RedirectResponse(auth_url)

@app.get("/auth/callback")
def gmail_callback(code: str):
    provider = get_provider("gmail")
    user_email = provider.exchange_code_and_store_user(code)

    # Create watch immediately so it's hands-off after OAuth
    provider.subscribe(user_email)

    return {"ok": True, "connected_user": user_email, "watch": "created"}

# ---- Webhook (Pub/Sub push) ----

@app.post("/webhooks/gmail")
async def gmail_webhook(request: Request):
    provider = get_provider("gmail")
    body = await request.body()

    # Verify Pub/Sub push JWT (OIDC token)
    await provider.verify(request, body)
    
    

    payload = await request.json()
    messages = await provider.extract_messages(payload)

    for m in messages:
        await process_message(m)

    return {"ok": True, "processed": len(messages)}
