from openllms.clients.decagon.decagon_client import DecagonClient

class NotionClient(DecagonClient):
    name = "notion"
    team_id = "31"
    flow_id = "notion"