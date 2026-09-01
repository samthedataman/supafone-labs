# Supervisor Models and Controls

This URL is retained for older links. The current guide is
[Supervisor Models: Managed and BYOK](supervisor-models.md), which documents
managed Supafone models plus Claude, OpenAI, Gemini, OpenRouter, Groq, and
Cerebras configurations.

Supafone Supervisor is the product. Its model is an independent reasoning
model beside the call, not the model speaking to the caller. It proposes a
structured directive, and deterministic confidence, policy, cooldown, and
tool-truth gates decide whether an adapter may deliver it.

See [Programmable Supervisor Directives](programmable-supervisor-directives.md)
for the packet fields and their human-supervisor meaning.

## Deprecated compatibility names

Older SDK releases exposed the names below. They remain compatibility aliases
so existing integrations do not break, but new code should use the Supervisor
names.

| Deprecated literal | Current name |
| --- | --- |
| `oracle_model` | `supervisor_model` |
| `oracle_timeout_seconds` | `supervisor_timeout_seconds` |
| `oracle_instructions` | `supervisor_instructions` |
| `discover_oracle_models()` | `discover_supervisor_models()` |
| `supafone.oracle()` | `supafone.completeWithSupervisor()` in TypeScript |
| `POST /v1/oracle/complete` | `POST /v1/supervisor/complete` |
| `supafone-labs-oracle` | `supafone-supervisor` |
| `supafone-labs-oracle-pro` | `supafone-supervisor-pro` |

The compatibility aliases do not identify a second product or a second
supervision process. They route to the same Supafone Supervisor behavior.
