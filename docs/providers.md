# Providers & frameworks

Supafone Labs exposes fourteen audited runtime integrations. Every integration
normalizes provider events into one canonical vocabulary. When a platform has a
supported control channel, the same abstract `inject_hidden_instruction`
decision compiles into its current native message.

The distinction matters:

- **Native control**: Supafone, Ultravox, Vapi, OpenAI Realtime, Grok, Gemini
  Live, ElevenLabs, Deepgram Voice Agent, and Inworld Realtime.
- **Context you own**: Retell custom LLM, LiveKit Agents, and Pipecat.
- **Observation-only by default**: Bland has no documented prompt-injection
  control; Cartesia Line needs an explicit custom-event hook in your agent.

## Capability matrix

`ProviderCapabilities` declares what each provider supports, so Supafone Labs picks the
best injection path automatically.

| Runtime | Integration mode | Compiled action | Acceptance criterion |
|---|---|---|---|
| Supafone Agent Factory | managed native control | Ultravox `user_text_message`, `urgency=later` | managed call accepts the data message |
| Ultravox | native control | `user_text_message`, `urgency=later` | Send Data Message returns HTTP 204 |
| Vapi | native call control | `add-message` with a system message | POST to the live call `controlUrl` succeeds |
| Retell | custom LLM context | system context entry | entry is present before the next response |
| Bland | observation only | no action | event parses and no unsupported action is emitted |
| OpenAI Realtime | native control | system `conversation.item.create` | item-created/done event, or no provider error |
| Grok Voice Agent | native control | `response.create.instructions` | `response.created` is received |
| Gemini Live | native control | `clientContent` user turn (system is invalid mid-session) | next turn follows the updated instruction |
| ElevenLabs Agents | native control | `contextual_update` | socket remains healthy and next turn completes |
| Deepgram Voice Agent | native control | `UpdatePrompt` | `PromptUpdated` is received |
| LiveKit Agents | framework context | `ChatContext.add_message` | `update_chat_ctx` persists the system entry |
| Pipecat | framework context | `LLMMessagesAppendFrame` | context aggregator retains the developer entry |
| Cartesia Line | explicit agent hook required | no default action | event parses and no universal injection is claimed |
| Inworld Realtime | native control | system `conversation.item.create` | item-added/done event, or no provider error |

`GenericWebhookAdapter` remains available as a configurable fallback, but it is
not counted as one of the fourteen audited runtimes.

## E2E release gate

`tests/test_provider_injection_e2e.py` is credential-free and runs every runtime
through the complete SDK boundary:

1. A current provider event enters the public `SupafoneLabs` facade.
2. The adapter emits canonical events.
3. The Watcher forms a belief, directive, and runtime decision.
4. The adapter compiles the exact native control or framework-context payload.
5. The test validates that payload byte-for-byte, or validates a safe no-action
   result for Bland and Cartesia.

`tests/test_live_injection_contracts.py` then provides credentialed acceptance
probes for Ultravox, Vapi, OpenAI Realtime, Grok, Gemini Live, Deepgram, and
Inworld. The ElevenLabs live suite sends a real `contextual_update`. Missing
credentials are reported as **skips, never passes**. Retell, LiveKit, and
Pipecat are integration-owned context paths and are tested locally; Supafone's
managed path uses its Ultravox transport. All contract rows link to primary
provider documentation in
`src/supafone_labs/runtime/provider_contracts.py` and carry a review date.

Telephony is tested independently at the PSTN boundary. The phone-grader suite
runs all fourteen runtime labels across the ten console telephony targets (140
combinations) and requires every one to use the same managed outbound dialer.
The target carrier is metadata; it cannot change injection compilation.

## Writing an adapter

An adapter implements two methods plus a capability declaration:

```python
from supafone_labs.runtime.adapters.base import BaseAdapter
from supafone_labs.runtime.core.capabilities import ProviderCapabilities
from supafone_labs.runtime.core.decision import DecisionKinds, ProviderAction, RuntimeDecision
from supafone_labs.runtime.core.events import EventTypes, make_event
from supafone_labs.runtime.core.state import RuntimeState


class MyProviderAdapter(BaseAdapter):
    provider_name = "myprovider"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(supports_mid_call_prompt_patch=True)

    async def parse_event(self, raw_event: dict) -> list:
        if raw_event.get("type") == "transcript":
            return [make_event(
                EventTypes.CALLER_TRANSCRIPT_FINAL,
                session_id=self._session_id(raw_event),
                provider=self.provider_name,
                actor="caller",
                text=raw_event.get("text", ""),
                data=raw_event,
            )]
        return []

    async def compile(self, decision: RuntimeDecision, state: RuntimeState) -> list[ProviderAction]:
        if decision.kind == DecisionKinds.INJECT_HIDDEN_INSTRUCTION:
            return [ProviderAction(
                provider=self.provider_name,
                kind="inject",
                payload={"text": decision.payload["text"]},
            )]
        return []
```

Drop it in `src/supafone_labs/runtime/adapters/`, add a sample-payload test, and it works
with the entire Supafone Labs brain for free.
