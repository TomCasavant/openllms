import uuid
from dataclasses import dataclass
from typing import List
from enum import Enum
import aiohttp

from openllms.clients.scoutly.scoutly_response import ScoutlyResponse
from openllms.models import LLM

#TODO: This model implementation was created long before I created the general setup for LLMS
# This should probably be implemented directly with everything else so it's easier to manage
# Right now I set it up to inherit from LLM but it should be inheriting from the AuthenticatedLLM class

API_ENDPOINT = "https://scoutly.scouting.org/api/chat2"


class ScoutlyRole(Enum):
    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"


@dataclass
class ScoutlyHistoryItem:
    role: ScoutlyRole
    content: str
    answer: str = ""

    def to_dict(self):
        return {
            "role": self.role.value,
            "content": self.content,
            "answer": self.answer,
        }

class ScoutlyClient(LLM):
    """
    Scoutly integration as an LLM-compatible class.
    """
    name = "scoutly"

    def __init__(
        self,
        client: aiohttp.ClientSession,
        session: str = str(uuid.uuid4()),
        language: str = "en-US",
        initial_prompt: str = "",
    ):
        super().__init__(client)
        self.session = session
        self.language = language
        self.history: List[ScoutlyHistoryItem] = [] # History items seem to be present, but I think the current session id is what impacts the history so who knows why they pass this through?

        if initial_prompt:
            self.history.append(
                ScoutlyHistoryItem(
                    role=ScoutlyRole.SYSTEM,
                    content=initial_prompt,
                    answer="@system, Understood.",
                )
            )

    def load_history(self, history_items: List[ScoutlyHistoryItem]):
        """Load prior chat history items."""
        self.history.extend(history_items)

    async def query(self, question: str) -> ScoutlyResponse:
        """Send a question to Scoutly and return a standardized response."""
        question = self.build_prompt(question)
        user_item = ScoutlyHistoryItem(role=ScoutlyRole.USER, content=question, answer="")
        self.history.append(user_item)

        payload = {
            "question": question,
            "language": self.language,
            "session": self.session,
            "history": [h.to_dict() for h in self.history],
        }

        async with self.client.post(API_ENDPOINT, json=payload) as resp:
            resp.raise_for_status()
            data = await resp.json()

        answer = data.get("answer", "")

        user_item.answer = answer
        self.history.append(
            ScoutlyHistoryItem(
                role=ScoutlyRole.ASSISTANT,
                content=question,
                answer=answer,
            )
        )

        return ScoutlyResponse.from_raw(data)
