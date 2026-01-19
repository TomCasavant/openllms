from openllms.clients.decagon.decagon_client import DecagonClient

class SubstackClient(DecagonClient):
    name = "substack"
    team_id: str = "14"
    #user_id: str = "decagon_anonymous_721489be-79d3-4014-bd66-f2736d3ab6c5"

    # Metadata (TODO: Test if METADATA is even required)
    flow_id: str = "substack"
    metadata_url: str = "https://substack.com/support"