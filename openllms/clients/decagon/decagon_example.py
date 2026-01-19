import requests
import time
import logging
import urllib3
from typing import Dict, Any, Optional

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("decagon-chatbot")

BASE_URL = "https://api.decagon.ai"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Content-Type": "application/json",
    "Origin": "https://decagon.ai",
    "Referer": "https://decagon.ai/",
    "X-DECAGON-AUTH-TEAM-ID": "14",
    "X-DECAGON-AUTH-USER-ID": "decagon_anonymous_721489be-79d3-4014-bd66-f2736d3ab6c5",
}


def create_conversation() -> str:
    """Create a new conversation and return its ID."""
    resp = requests.post(
        f"{BASE_URL}/conversation/new",
        headers=HEADERS,
        json={
            "flow_id": "substack",
            "metadata": {
                "url": "https://substack.com/support",
                "user_device": "cli",
                "widget_location": "terminal",
            },
        },
        verify=False,
        timeout=30
    )
    resp.raise_for_status()
    conversation_id = resp.json()["conversation_id"]
    logger.info("Created conversation: %s", conversation_id)
    return conversation_id


def send_message(conversation_id: str, text: str) -> None:
    """Send a user message to the AI asynchronously."""
    payload = {
        "type": "chat_message",
        "text": text,
        "flow_id": "substack",
        "metadata": {
            "user_device": "cli",
            "widget_location": "terminal",
            "timezone": "America/New_York",
            "user_browser": "Python-requests",
        }
    }
    resp = requests.post(
        f"{BASE_URL}/chat/{conversation_id}/message",
        headers=HEADERS,
        json=payload,
        verify=False,
        timeout=30
    )
    resp.raise_for_status()
    logger.info("Sent message: %s", text)


def poll_history(conversation_id: str, last_ai_id: Optional[str] = None, poll_interval: float = 3.0) -> Dict[str, Any]:
    """Poll conversation history until a new AI message appears."""
    while True:
        resp = requests.get(
            f"{BASE_URL}/conversation/history",
            headers=HEADERS,
            params={
                "conversation_id": conversation_id,
                "trigger_message": "",
                "user_type": "user"
            },
            verify=False,
            timeout=30
        )
        resp.raise_for_status()
        history = resp.json()
        messages = history.get("messages", [])
        # Look for the latest AI message
        messages = list(reversed(messages))
        recent_message = messages[0]
        if recent_message.get("role") == "AI":
            if recent_message.get("id") != last_ai_id:
                return recent_message

        time.sleep(poll_interval)


def run_chatbot():
    #conversation_id = create_conversation()
    conversation_id = "923b6ebc-983b-4df6-ba22-6520b1369593"
    last_ai_id = None

    print("\nDecagon Chatbot (type 'exit' to quit)\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input or user_input.lower() in {"exit", "quit"}:
                print("Goodbye!")
                break

            # Send the message
            send_message(conversation_id, user_input)

            # Poll for AI reply
            ai_msg = poll_history(conversation_id, last_ai_id)
            last_ai_id = ai_msg.get("id")
            ai_text = ai_msg.get("text", "(AI did not respond)")
            print(f"\nAI: {ai_text}\n")

        except KeyboardInterrupt:
            print("\nExiting.")
            break
        except Exception:
            logger.exception("Chat error")


if __name__ == "__main__":
    run_chatbot()



