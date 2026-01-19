import urllib

import asyncio
import time
import uuid
from openllms.models.llm import AuthenticatedClient, LLMResponse
from dataclasses import dataclass

@dataclass
class ShopifyResponse(LLMResponse):
    _id: str
    turn_number: int
    sequence_number: int
    created_at: str
    role: str
    content: str

    @classmethod
    def from_raw(cls, data) -> "ShopifyResponse":
        content = data.get('content')
        message = ""
        if isinstance(content, list) and content and isinstance(content[0], dict):
            message = content[0].get('markdown', '')
        elif isinstance(content, str):
            # We were doing this before but probably not necessary anymore, I was just parsing it completely wrong.
            message = content

        return cls(
            message=message,
            _id=data.get('id'),
            role=data.get('role'),
            sequence_number=data.get('sequence_number'),
            turn_number=data.get('turn_number'),
            created_at=data.get('created_at'),
            content=content,
            raw=data
        )

class ShopifyClient(AuthenticatedClient):
    name = "shopify"
    BASE_URL = "https://sidekick.shopify.com/api/messages"
    CONVERSATION_URL = "https://sidekick.shopify.com/api/conversations"
    ANON_URL = "https://sidekick.shopify.com/api/anonymous_user"

    conversation_id: str | None = None
    user_id: str | None = None

    headers = {
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
    }

    async def fetch_session_id(self):
        """Create anonymous user + conversation if not already set."""

        if not self.user_id:
            data = await self._post(self.ANON_URL, headers={**self.headers, "Accept": "application/json"}, json={})
            self.user_id = data.get("identifier")
            self.headers["x-anonymous-user-id"] = self.user_id

        if not self.conversation_id:
            assistant_url = (
                "https://help.shopify.com/en/search/What"
                "?_data=routes%2F%28%24locale%29._assistant.search.%24searchId"
            )
            form_data = {
                "actionName": "createSidekickConversation",
                "query": "",
                "optimisticQuery": "",
                "anonymousUserId": self.user_id
            }

            # Use parent's client directly for raw request to get headers
            async with self.client.post(
                assistant_url,
                headers={**self.headers, "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
                data=urllib.parse.urlencode(form_data),
                allow_redirects=False  # we only want headers
            ) as resp:
                if resp.status not in (200, 204, 302):
                    raise RuntimeError(f"Failed to create conversation: {resp.status}")

                redirect = resp.headers.get("x-remix-redirect")
                if redirect:
                    # URL format: .../What.<conversation_id>?q=...
                    # This *can't* be how they parse out the conversation id? But it works for me
                    conv_id = redirect.split(".")[-1].split("?")[0]
                    self.conversation_id = conv_id
        return self.user_id

    async def post_message(self, user_message: str) -> None:
        user_message = self.build_prompt(user_message)
        request_id = str(uuid.uuid4())
        payload = {
            "message": {
                "conversation_id": self.conversation_id or str(uuid.uuid4()),
                "content": user_message,
                "scenario": "help/search",
                "features": ["help/search/default"],
                "request_id": request_id,
            }
        }

        # Make raw POST using parent's client
        async with self.client.post(
                self.BASE_URL, headers=self.headers, json=payload
        ) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Shopify API /messages returned {resp.status}")
            # just read & ignore event stream; no JSON decoding
            await resp.release()

    async def get_history(self) -> dict:
        conversation_url = f"{self.CONVERSATION_URL}/{self.conversation_id}?features[]=help/search/default"
        return await self._get(conversation_url, headers={**self.headers, "Accept": "application/json"})

    async def poll_history_for_response(self, last_query: str, poll_interval=2, timeout=60) -> dict:
        start = time.monotonic()
        while True:
            history = await self.get_history()
            messages = history.get("conversation", {}).get("messages", [])
            # scan backwards to match the last user message
            for i in range(len(messages) - 1, 0, -1):
                user_msg = messages[i - 1]
                assistant_msg = messages[i]
                if (
                    user_msg.get("role") == "user"
                    and user_msg.get("content") == last_query
                    and assistant_msg.get("role") == "assistant"
                ):
                    return assistant_msg
            if time.monotonic() - start > timeout:
                raise TimeoutError("Timed out waiting for Shopify AI response")
            await asyncio.sleep(poll_interval)

    async def query(self, user_message: str, timeout: int = 60, poll_interval: int = 2) -> ShopifyResponse:
        await self.authenticate()
        await self.post_message(user_message)
        message_data = await self.poll_history_for_response(user_message, timeout=timeout, poll_interval=poll_interval)
        return ShopifyResponse.from_raw(message_data)
