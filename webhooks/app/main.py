import json
import logging
from fastapi import FastAPI, Request, HTTPException

from app.services.slack_service import verify_slack_signature
from app.utils.message_utils import filter_message, store_in_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()


@app.post("/slack/events")
async def slack_events(request: Request):
    body = await request.body()
    headers = request.headers
    payload = json.loads(body)
    
    if payload.get("type") == "url_verification":
        logger.info("URL verification request")
        return {"challenge": payload.get("challenge")}
    
    timestamp = headers.get("X-Slack-Request-Timestamp", "")
    signature = headers.get("X-Slack-Signature", "")
    
    if not verify_slack_signature(body, timestamp, signature):
        logger.warning("Invalid signature")
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    if payload.get("type") == "event_callback" and payload.get("event", {}).get("type") == "message":
        text = payload["event"].get("text", "")
        message_ts = payload["event"].get("ts", "")
        logger.info(f"Processing message: {text}")
        
        if filter_message(text):
            store_in_db(payload["event"])
    
    return {"ok": True}