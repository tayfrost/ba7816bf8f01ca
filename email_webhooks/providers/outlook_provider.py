"""
Outlook (Microsoft Graph) webhook provider.
Works via Azure and Azure only

To get emails from Outlook: Microsoft Graph API is required.
To use Microsoft Graph: authentication via Microsoft Azure is required
To test your webhook locally: ngrok exposes localhost to the internet so Microsoft Graph can call it.

"""

import os
from fastapi import Request, HTTPException
from providers.base import WebhookProvider
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

load_dotenv()

TEST_ACCESS_TOKEN = os.getenv('MY_ENV_VAR')
class OutlookProvider(WebhookProvider):

    async def verify(self, request: Request, body: bytes):

        validation_token = request.query_params.get("validationToken")
        if validation_token:
            return PlainTextResponse(content=validation_token)

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            auth_header = f"Bearer {self.TEST_ACCESS_TOKEN}"

    async def extract_message(self, payload: dict):
        value = payload.get("value", [])
        if not value:
            return None

        return value[0]  
