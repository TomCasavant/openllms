import asyncio
import inspect
from typing import List
from openllms.clients import ScoutlyClient, ATTClient, SubstackClient, ChatWithClient, BKSafetyWearClient, \
    MicroTikClient, PuzzlesUnlimitedClient, IntercomClient, ShopifyClient
import aiohttp

from openllms.clients.decagon import WhopClient
from openllms.clients import NotionClient, BiltClient, ClasspassClient, CurologyClient
from openllms.clients.mycity import MyCityClient
import openllms.clients as clients_module
from openllms.models import LLM


async def chat_loop(clients: List):
    print("LLM Chat (type 'exit' to quit)")
    print("Address clients using @<name>, e.g. '@Scoutly Hello'")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break

        if not user_input.startswith("@"):
            print("Error: Please address a client using @<name>")
            continue

        try:
            at_name, message = user_input.split(" ", 1)
            target_name = at_name[1:]  # remove @
        except ValueError:
            print("Error: Please provide a message after the client handle")
            continue

        client = next((c for c in clients if c.name == target_name), None)
        if not client:
            print(f"Error: No client named '{target_name}'")
            continue

        try:
            resp = await client.query(message)
            print(f"{client.name}: {resp.message}")
        except Exception as e:
            print(f"{client.name} Error: {e}")


if __name__ == "__main__":
    async def main():
        async with aiohttp.ClientSession() as session:
            # Instantiate clients
            # Grab all classes in openllms.clients that inherit from LLM
            all_client_classes = [
                cls for name, cls in inspect.getmembers(clients_module, inspect.isclass)
                if issubclass(cls, LLM)
            ]

            clients = [cls(client=session) for cls in all_client_classes]

            await chat_loop(clients)

    asyncio.run(main())
