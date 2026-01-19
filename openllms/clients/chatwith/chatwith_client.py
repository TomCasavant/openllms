import uuid
import json
from dataclasses import dataclass
from typing import List, Dict, Any

from openllms.models import LLMResponse
from openllms.models.llm import AuthenticatedClient


@dataclass
class ChatWithResponse(LLMResponse):

    @classmethod
    def from_raw(cls, data: dict) -> "ChatWithResponse":
        return cls(
            message=data.get("message"),
            raw=data,
        )


class ChatWithClient(AuthenticatedClient):
    name = "chatwith"

    BASE_URL = "https://api0.chatwith.tools"
    chatbot_id: str = "d653985a-3e95-42b8-a726-d7a4173c3b55" # Default to ChatWith's chat bot (so I don't have to make ChatWithChatWithClient)

    async def query(
        self, user_message: str
    ) -> ChatWithResponse:
        url = f"{self.BASE_URL}/chat"

        messages = [{"role": "user", "content": user_message}] # TODO: Optionally load in longer history

        payload = {
            "id": self.session_id,
            "messages": messages,
            "chatbotId": self.chatbot_id,  # fixed chatbot
            "sessionContext": {}, # We can pass in session context directly? May be useful for coding models??
        }

        headers = {}

        async with self.client.post(url, json=payload, headers=headers) as response:
            # I think chatwith just returns the raw text as message
            text = await response.text()

        return ChatWithResponse.from_raw({"message": text})

    async def fetch_session_id(self):
        # I think we can just generate a random session id
        return str(uuid.uuid4())
