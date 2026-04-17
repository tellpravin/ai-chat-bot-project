"""
Meta (Facebook) account connector for the AI Chat Bot.
Integrates with Meta's Graph API for Messenger and Facebook data.
"""

import os
import requests


META_GRAPH_API_BASE = "https://graph.facebook.com/v19.0"
WINDSOR_AUTHORIZATION_URL = "https://onboard.windsor.ai/app/facebook"


class MetaConnector:
    def __init__(self, access_token: str | None = None):
        self.access_token = access_token or os.environ.get("META_ACCESS_TOKEN")
        if not self.access_token:
            raise ValueError(
                "Meta access token is required. Set META_ACCESS_TOKEN env var "
                f"or connect your account at: {WINDSOR_AUTHORIZATION_URL}"
            )
        self.session = requests.Session()

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        params = params or {}
        params["access_token"] = self.access_token
        url = f"{META_GRAPH_API_BASE}/{endpoint.lstrip('/')}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_me(self) -> dict:
        return self._get("me", {"fields": "id,name,email"})

    def get_pages(self) -> list[dict]:
        data = self._get("me/accounts", {"fields": "id,name,access_token,category"})
        return data.get("data", [])

    def get_page_conversations(self, page_id: str, page_token: str) -> list[dict]:
        data = self._get(
            f"{page_id}/conversations",
            {"fields": "participants,updated_time", "access_token": page_token},
        )
        return data.get("data", [])

    def send_message(self, page_token: str, recipient_id: str, message_text: str) -> dict:
        url = f"{META_GRAPH_API_BASE}/me/messages"
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": message_text},
            "access_token": page_token,
        }
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def get_ad_accounts(self) -> list[dict]:
        data = self._get("me/adaccounts", {"fields": "id,name,account_status,currency"})
        return data.get("data", [])


def get_authorization_url() -> str:
    return WINDSOR_AUTHORIZATION_URL


def connect_from_env() -> MetaConnector:
    return MetaConnector()
