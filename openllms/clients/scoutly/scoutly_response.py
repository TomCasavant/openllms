from dataclasses import dataclass

from openllms.models import LLMResponse


@dataclass
class ScoutlyResponse(LLMResponse):

    @classmethod
    def from_raw(cls, data: dict) -> "ScoutlyResponse":
        # Scoutly returns {"answer": "..."}
        return cls(message=data.get("answer", ""), raw=data)
