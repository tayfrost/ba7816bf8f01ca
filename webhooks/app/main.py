from fastapi import FastAPI, Request, HTTPException

from app.services.slack_service import verify_slack_signature
from app.utils.message_utils import filter_message, store_in_db

app = FastAPI()


@app.post("/slack/events")
async def slack_events(request: Request):
    body = await request.body()
    headers = request.headers
    
    timestamp = headers.get("X-Slack-Request-Timestamp", "")
    signature = headers.get("X-Slack-Signature", "")
    
    if not verify_slack_signature(body, timestamp, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    payload = await request.json()
    
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}
    
    if payload.get("event", {}).get("type") == "message": # v1 focuses only on messages, not reactions or edits
        text = payload["event"].get("text", "")
        print(text)
        
        if filter_message(text):
            store_in_db(payload["event"])
    
    return {"ok": True}