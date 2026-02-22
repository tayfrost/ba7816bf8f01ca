import os
import json
import base64
from typing import List, Tuple, Optional

from dotenv import load_dotenv
from fastapi import Request, HTTPException
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import id_token as google_id_token  #JWT verificatiozn

from providers.base import EmailProvider
from core.db import (
    upsert_gmail_user,
    get_gmail_user,
    update_user_history_id,
    update_user_watch
)

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/pubsub",
]

CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")
CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")
BASE_URL = os.getenv("BASE_URL")
REDIRECT_URI = f"{BASE_URL}/auth/callback" if BASE_URL else None
GMAIL_PUBSUB_TOPIC = os.getenv("GMAIL_PUBSUB_TOPIC")
WEBHOOK_ENDPOINT = os.getenv("GMAIL_WEBHOOK_ENDPOINT")


class GmailProvider(EmailProvider):
    """
    OAuth is handled via:
      GET /auth/login -> Google consent -> GET /auth/callback
    """

    def _flow(self) -> Flow:
        if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
            raise RuntimeError("Missing env vars: GMAIL_CLIENT_ID/GMAIL_CLIENT_SECRET/BASE_URL (for REDIRECT_URI)")

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [REDIRECT_URI],
                }
            },
            scopes=SCOPES,
        )
        flow.redirect_uri = REDIRECT_URI
        return flow

    def get_auth_url(self) -> str:
        flow = self._flow()
        auth_url, _state = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
        )
        return auth_url

    def exchange_code_and_store_user(self, code: str) -> str:
        """
        Exchanges auth code for tokens, stores token_json in DB,
        returns the user_email
        """
        flow = self._flow()
        flow.fetch_token(code=code)
        creds = flow.credentials

        # Identify the Gmail account this token belongs to
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        user_email = profile["emailAddress"]

        token_json = creds.to_json()
        upsert_gmail_user(user_email, token_json)

        return user_email


    def subscribe(self, user_email: str) -> dict:

        user = get_gmail_user(user_email)
        if not user:
            raise RuntimeError(f"User not found in DB: {user_email}")

        creds = Credentials.from_authorized_user_info(json.loads(user["token_json"]), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())

        service = build("gmail", "v1", credentials=creds)
        body = {"labelIds": ["INBOX", "SENT"], "topicName": GMAIL_PUBSUB_TOPIC}

        resp = service.users().watch(userId="me", body=body).execute()

        history_id = str(resp.get("historyId"))
        expiration_ms = str(resp.get("expiration"))  # milliseconds epoch in string

        # Persist watch state
        update_user_watch(user_email, history_id, expiration_ms)

        return resp


    async def verify(self, request: Request, body: bytes):
        """
        Verifies Pub/Sub push with OIDC token:
        Authorization: Bearer <JWT>
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing Bearer token (configure Pub/Sub push OIDC token)")

        token = auth_header.split(" ", 1)[1].strip()

        if not WEBHOOK_ENDPOINT:
            raise HTTPException(status_code=500, detail="Server misconfig: WEBHOOK_ENDPOINT missing")

        try:
            info = google_id_token.verify_oauth2_token(
                token,
                GoogleRequest(),
                audience=WEBHOOK_ENDPOINT,
            )
            iss = info.get("iss")
            if iss not in ("https://accounts.google.com", "accounts.google.com"):
                raise HTTPException(status_code=401, detail=f"Unexpected issuer: {iss}")

            return None
        except ValueError as e:
            raise HTTPException(status_code=401, detail=f"Invalid JWT: {e}")

    # ---------- Message extraction (history incremental) ----------

    def _fetch_new_messages(self, user_email: str, start_history_id: str) -> Tuple[List[dict], str]:
        """
        Fetch messages added since start_history_id. Returns (messages, latest_history_id).
        """
        user = get_gmail_user(user_email)
        if not user:
            return [], start_history_id

        creds = Credentials.from_authorized_user_info(json.loads(user["token_json"]), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())

        service = build("gmail", "v1", credentials=creds)

        try:
            hist = service.users().history().list(
                userId="me",
                startHistoryId=start_history_id,
                historyTypes=["messageAdded"],
            ).execute()

            latest_history_id = str(hist.get("historyId") or start_history_id)

            messages: List[dict] = []
            for h in hist.get("history", []):
                for added in h.get("messagesAdded", []):
                    msg_id = added["message"]["id"]
                    full_msg = service.users().messages().get(
                        userId="me",
                        id=msg_id,
                        format="full"
                    ).execute()
                    messages.append(full_msg)

            return messages, latest_history_id

        except HttpError as e:
            # History window too old => reset
            if getattr(e, "resp", None) and e.resp.status == 404:
                profile = service.users().getProfile(userId="me").execute()
                current_history_id = str(profile.get("historyId"))
                return [], current_history_id
            raise

    async def extract_messages(self, payload: dict) -> List[dict]:
        """
        Incrementally fetch using last_history_id stored per user.
        """
        try:
            msg_data = payload["message"]["data"]
            decoded = base64.b64decode(msg_data).decode("utf-8")
            event = json.loads(decoded)

            user_email = event.get("emailAddress")
            notif_history_id = str(event.get("historyId") or "")

            if not user_email:
                return []

            user = get_gmail_user(user_email)
            if not user:
                return []

            last_history_id: Optional[str] = user.get("last_history_id")

            if not last_history_id:
                if notif_history_id:
                    update_user_history_id(user_email, notif_history_id)
                return []

            messages, latest_history_id = self._fetch_new_messages(user_email, last_history_id)
            update_user_history_id(user_email, latest_history_id)
            return messages

        except Exception as e:
            print("extract_messages error:", e)
            return []
