import logging
from abc import ABC, abstractmethod
import aiohttp
from dataclasses import dataclass
from typing import Optional

@dataclass
class LLMResponse(ABC):
    message: str
    raw: dict

    @classmethod
    @abstractmethod
    def from_raw(cls, data: dict) -> "LLMResponse":
        """
        Parse raw provider JSON into a standardized LLMResponse.
        Must be implemented by each provider subclass.
        """
        pass

class LLM(ABC):
    name: str
    prepend_prompt: str
    append_prompt: str

    def __init__(self, client: aiohttp.ClientSession, prepend_prompt="", append_prompt="", logger=None):
        self.client = client
        self.logger = logger or logging.getLogger(__name__)
        self.prepend_prompt = prepend_prompt
        self.append_prompt = append_prompt

    def build_prompt(self, message: str) -> str:
        """
        Modifies the prompt so that self.prepend is before the message and self.append is after. Returns the result
        """
        return f"{self.prepend_prompt}{message}{self.append_prompt}"

    async def _get(self, url: str, **kwargs):
        async with self.client.get(url, **kwargs) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def _post(self, url: str, **kwargs):
        async with self.client.post(url, **kwargs) as resp:
            resp.raise_for_status()
            return await resp.json()

    @abstractmethod
    async def query(self, **params) -> LLMResponse:
        pass

class AuthenticatedClient(LLM, ABC):
    """
    Some clients require some form of anonymous authentication.

    (Some clients require you to login to their website not anonymously, but that's out of scope)
    """
    session_id: Optional[str] = None

    def __init__(
        self,
        *args,
        session_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.session_id = session_id

    @abstractmethod
    async def fetch_session_id(self):
        """
        Gets and returns a session id. Some LLMs have endpoints for this, for others you can just manually generate a UUID for your session.
        """
        pass

    async def authenticate(self):
        """
        Sets the session_id by calling fetch_session_id on the client
        """
        if self.session_id is None:
            self.session_id = await self.fetch_session_id()

