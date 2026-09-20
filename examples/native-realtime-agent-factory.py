import os
from supafone_labs import Supafone

supafone = Supafone(api_key=os.environ["SUPAFONE_API_KEY"])
agent = supafone.labs.agents.create_inbound({
    "agentKey": "native-realtime-intake",
    "name": "Native realtime intake",
    "realtime": {"provider": "openai", "model": "gpt-realtime-2.1", "voice": "marin"},
})
preview = supafone.labs.agents.test_call(agent["agent"]["agent_key"])
print(preview["browser_session"]["transport"])
