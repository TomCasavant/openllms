import json
from dataclasses import dataclass
from typing import Optional, List, Dict

from openllms.models.llm import LLMResponse


@dataclass
class ATTResponse(LLMResponse):
    question: Optional[str] = None
    score: Optional[float] = None
    citations: Optional[List[Dict]] = None

    @classmethod
    def from_raw(cls, data: dict) -> "ATTResponse":
        """
        Parse AT&T API JSON into a standardized response object.
        """
        # TODO: AT&T Also returns a fusion object, might as well parse that as well

        docs = data.get("response", {}).get("docs", [])
        if not docs:
            #TODO: Probably should standardize a way to handle when the llm does not give a valid response
            return cls(message="", raw=data)

        first_doc = docs[0]
        raw_answer = first_doc.get("answer")
        try:
            parsed = json.loads(raw_answer) if isinstance(raw_answer, str) else raw_answer
        except json.JSONDecodeError:
            parsed = {"answer": str(raw_answer)}

        message = parsed.get("answer", "")
        question = parsed.get("question")
        citations = parsed.get("articles", [])

        score = parsed.get("score")

        return cls(
            message=message,
            question=question,
            score=score,
            citations=citations,
            raw=data
        )