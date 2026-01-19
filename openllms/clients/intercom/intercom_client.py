from dataclasses import dataclass
from typing import Any, Dict

from openllms.models import LLMResponse

from openllms.models.llm import AuthenticatedClient


@dataclass
class IntercomResponse(LLMResponse):
    conversation_id: str | None = None

    @classmethod
    def from_raw(cls, data: Dict[str, Any]) -> "IntercomResponse":
        message = ""

        return cls(
            message=message,
            conversation_id=data.get("id"),
            raw=data,
        )

class IntercomClient(AuthenticatedClient):
    """
    WHILE IT DOES APPEAR WE CAN COMMUNICATE WITH THE INTERCOM CHAT BOTS, AFTER FURTHER RESEARCH IT SEEMS LIKE IT IS CAPABLE
    OF TRIGGERING REPLIES FROM ACTUAL HUMANS, SO I CONSIDER THIS OUT OF SCOPE.

    I'm sure you could figure out a way to make sure it never pings a real customer service agent. But not a priority at the moment.
    """
    name = "intercom"
    BASE_URL = "https://api-iam.intercom.io"
    app_id = "REDACTED"
    v: str = "3"
    s: str
    r: str

    conversation_id: str | None = None
    booted: bool = False

    async def fetch_session_id(self) -> str:
        # Stable per-session identifiers
        # REDACTED

        # Boot Intercom session
        await self.ping()

        return ""

    async def ping(self) -> None:
        # REDACTED
        pass

    async def query(self, user_message: str):
        await self.authenticate()
        # REDACTED
        pass

