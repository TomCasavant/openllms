import json
import uuid
from dataclasses import dataclass
from typing import List, Dict

from openllms.models import LLMResponse
from openllms.models.llm import AuthenticatedClient

"""
{"model": "gpt-35-turbo-16k", "is_last": false, "choices": [{"messages": [{"role": "tool", "content": "{\"citations\": [], \"intent\": \"\", \"search_intent\": \"\"}"}, {"role": "assistant", "content": "I can provide information on New York City government topics. I can help with questions related to opening and operating a business in NYC or services covered by NYC311. If you have any specific questions, feel free to ask!"}]}], "id": "880b9253-e8b4-4bbb-8034-9216ddef9703", "created": 1765976302, "object": "chat.completion.chunk"}
{"model": "gpt-35-turbo-16k", "is_last": true, "choices": [{"messages": [{"role": "tool", "content": "{\"citations\": [], \"intent\": \"\", \"search_intent\": \"\"}"}, {"role": "assistant", "content": "I can provide information on New York City government topics. I can help with questions related to opening and operating a business in NYC or services covered by NYC311. If you have any specific questions, feel free to ask!"}]}], "id": "880b9253-e8b4-4bbb-8034-9216ddef9703", "created": 1765976302, "object": "chat.completion.chunk"}
"""
@dataclass
class MyCityResponse(LLMResponse):
    choices: List[Dict]

    model: str
    is_last: bool
    mycity_id: str
    created: int
    object_type: str

    @classmethod
    def from_raw(cls, data: dict) -> "MyCityResponse":
        model = data.get("model")
        is_last = data.get("is_last")
        choices = data.get("choices", [])
        mycity_id = data.get("id")
        created = data.get("created")
        object_type = data.get("object")

        message = ""
        if choices:
            for msg in choices[0].get("messages", []):
                if msg.get("role") == "assistant":
                    message = msg.get("content", "")
                    break

        return cls(
            message=message,
            choices=choices,
            model=model,
            is_last=is_last,
            mycity_id=mycity_id,
            created=created,
            object_type=object_type,
            raw=data,
        )


class MyCityClient(AuthenticatedClient):
    name = "mycity"

    BASE_URL = "https://chat.nyc.gov"
    chat_uuid: str

    async def query(self, prompt: str) -> MyCityResponse:
        await self.authenticate()

        prompt = self.build_prompt(prompt)
        url = f"{self.BASE_URL}/conversation"

        # We can pass in an array of messages here, not sure how that impacts the conversation
        # TODO: Add client that lets you load history, scoutly does it as well
        payload = {
            "messages": [
                {
                    "role": "tool",
                    "content": '{"citations": [], "intent": "", "search_intent": ""}',
                },
                {
                    "role": "user",
                    "content": prompt,
                    "index": 1,
                },
            ],
            "sessionUUID": self.session_id,
            "chatUUID": self.chat_uuid,
        }

        headers = {} # Headers do not seem to be required

        async with self.client.post(url, json=payload, headers=headers) as response:
            final_response: MyCityResponse | None = None

            async for raw_line in response.content:
                line = raw_line.decode().strip()
                if not line:
                    continue

                data = json.loads(line)
                parsed = MyCityResponse.from_raw(data)

                if parsed.is_last:
                    final_response = parsed

        if final_response is None:
            raise RuntimeError("No completed response found")

        return final_response

    async def fetch_session_id(self):
        # I believe we can just generate our own session UUID and chatUUID
        self.chat_uuid = str(uuid.uuid4())
        return str(uuid.uuid4())

    async def get_recaptcha_key(self):
        """
        https://chat.nyc.gov/get_recaptcha_site_key
        ALWAYS seems to return site_key "6LfaXO0nAAAAACCrMNflfmJDHSpF_kqcUQjB_sAf"? Probably not particularly useful
        :return:
        """
        endpoint = "/get_recaptcha_key"
        return await self._get(f"{self.BASE_URL}{endpoint}")
