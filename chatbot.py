"""
AI Chat Bot with Meta (Facebook) integration.
Uses Claude for AI responses and Meta Messenger as the chat channel.
"""

import os
from anthropic import Anthropic
from meta_connector import MetaConnector, get_authorization_url


class MetaChatBot:
    def __init__(self, meta_token: str | None = None, claude_model: str = "claude-sonnet-4-6"):
        self.claude = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.model = claude_model
        self.meta = MetaConnector(access_token=meta_token)
        self.conversation_history: dict[str, list[dict]] = {}

    def _get_ai_response(self, sender_id: str, user_message: str) -> str:
        history = self.conversation_history.setdefault(sender_id, [])
        history.append({"role": "user", "content": user_message})

        response = self.claude.messages.create(
            model=self.model,
            max_tokens=1024,
            system="You are a helpful AI assistant responding via Facebook Messenger. Be concise and friendly.",
            messages=history,
        )
        assistant_text = response.content[0].text
        history.append({"role": "assistant", "content": assistant_text})
        return assistant_text

    def handle_messenger_event(self, event: dict, page_token: str) -> None:
        messaging = event.get("messaging", [])
        for msg_event in messaging:
            sender_id = msg_event.get("sender", {}).get("id")
            message = msg_event.get("message", {})
            text = message.get("text")
            if sender_id and text:
                reply = self._get_ai_response(sender_id, text)
                self.meta.send_message(page_token, sender_id, reply)

    def get_account_info(self) -> dict:
        return {
            "user": self.meta.get_me(),
            "pages": self.meta.get_pages(),
            "ad_accounts": self.meta.get_ad_accounts(),
        }


def main():
    print("Meta Account Connection URL:", get_authorization_url())
    print()

    bot = MetaChatBot()
    info = bot.get_account_info()

    print(f"Connected as: {info['user'].get('name')} (id={info['user'].get('id')})")
    print(f"Pages: {len(info['pages'])}")
    for page in info["pages"]:
        print(f"  - {page['name']} ({page['id']})")
    print(f"Ad Accounts: {len(info['ad_accounts'])}")
    for account in info["ad_accounts"]:
        print(f"  - {account['name']} ({account['id']})")


if __name__ == "__main__":
    main()
