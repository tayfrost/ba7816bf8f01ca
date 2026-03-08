"""
Uses Google Cloud Console to do so
"""

from fastapi import Request, HTTPException
from fastapi.responses import PlainTextResponse
from providers.base import WebhookProvider


class GmailProvider(WebhookProvider):

    async def verify(self, request: Request, body: bytes):

        resource_state = request.headers.get("X-Goog-Resource-State")
        if not resource_state:
            return PlainTextResponse(content="Webhook received")

        channel_token = request.headers.get("X-Goog-Channel-Token")
        if channel_token != "test_token":  
            raise HTTPException(status_code=403, detail="Invalid channel token")

        return None  

    async def extract_message(self, payload: dict):
        if not payload:
            return None
        return payload
