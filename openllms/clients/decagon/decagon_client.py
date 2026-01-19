import asyncio
import time
from dataclasses import dataclass
import uuid

from openllms.models.llm import LLMResponse, AuthenticatedClient


@dataclass
class DecagonResponse(LLMResponse):
    decagon_id: str
    role: str

    @classmethod
    def from_raw(cls, data: dict) -> "DecagonResponse":
        message = data.get("text", "")
        decagon_id = data.get("id")
        role = data.get("role")
        return cls(
            message=message,
            role=role,
            decagon_id=decagon_id,
            raw=data
        )

class DecagonClient(AuthenticatedClient):
    name = "decagon"

    # All companies that use decagon have the same base endpoint, the metadata requires the website URL though
    BASE_URL = "https://api.decagon.ai"
    DECAGON_URL = "https://decagon.ai"
    DECAGON_USER_BASE = "decagon_anonymous_"

    team_id: str
    _user_id: str = None

    # Metadata
    flow_id: str # This seems to be required, none of the other metadata is
    metadata_url: str = ""
    user_device: str = ""  # Unclear how this changes results
    widget_location: str = ""  # Unclear how this changes results
    timezone: str = "America/New_York"
    user_browser: str = ""

    @property
    def user_id(self) -> str:
        if self._user_id is None:
            generated_id = uuid.uuid4()
            self._user_id = f"{self.DECAGON_USER_BASE}{generated_id}"

        return self._user_id

    def get_headers(self):
        # TODO: Look into how to generate anonymous user ID
        # TODO: We will assume for now that TEAM-ID is a per company ID, in which case each child will need one
        return {
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Content-Type": "application/json",
            "Origin": self.DECAGON_URL,
            "Referer": self.DECAGON_URL,
            "X-DECAGON-AUTH-TEAM-ID": self.team_id,
            "X-DECAGON-AUTH-USER-ID": self.user_id,
        }

    def get_metadata_json(self):
        # TODO: Not immediately clear if this is necessary, but will spoof for now
        return {
            "flow_id": self.flow_id,
            "metadata": {
                "url": self.metadata_url,
                "user_device": self.user_device,
                "widget_location": self.widget_location,
                "timezone": self.timezone,
                "user_browser": self.user_browser,
            }
        }

    async def fetch_session_id(self):
        """
        DecagonClients call their sessions "conversations" and have an endpoint to create a new one
        """
        endpoint = "/conversation/new"
        full_url = f"{self.BASE_URL}{endpoint}"
        json = self.get_metadata_json()
        data = await self._post(full_url, headers=self.get_headers(), json=json)
        return data.get("conversation_id")

    async def get_history(self):
        endpoint = "/conversation/history"
        full_url = f"{self.BASE_URL}{endpoint}"
        params = {
            "conversation_id": self.session_id,
            "trigger_message": "",  # Not clear what this does
            "user_type": "user",    # Not sure what options are available for this
        }
        return await self._get(full_url, headers=self.get_headers(), params=params)

    async def poll_history_for_response(self, poll_interval=3, timeout=60):
        start = time.monotonic()

        # Perhaps not the best solution, but sleep briefly for user to load in

        while True:
            history = await self.get_history()
            messages = history.get("messages", [])

            if messages:
                # Reverse like your working sync version
                most_recent_message = messages[-1]
                if most_recent_message.get("role") == "AI":
                    return most_recent_message

            if time.monotonic() - start > timeout:
                raise TimeoutError("Timed out waiting for Decagon response")

            await asyncio.sleep(poll_interval)

    async def query(
        self,
        query: str,
        chat_type: str = "chat_message",  # unknown if there are other types
        timeout: int = 60,
        poll_interval: int = 3,
    ) -> DecagonResponse:

        # Ensure we have a conversation
        await self.authenticate()

        endpoint = f"/chat/{self.session_id}/message"
        full_url = f"{self.BASE_URL}{endpoint}"

        prompt = self.build_prompt(query)
        payload = self.get_metadata_json()
        payload["type"] = chat_type
        payload["text"] = prompt

        await self._post(full_url, headers=self.get_headers(), json=payload)

        # Unlike other clients, decagon seems to require us to poll an endpoint until the AI response is generated
        response = await self.poll_history_for_response(
            timeout=timeout,
            poll_interval=poll_interval,
        )


        return DecagonResponse.from_raw(response)