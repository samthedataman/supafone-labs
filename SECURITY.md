# Security Policy

## Reporting a vulnerability

Email **samatcrispy@gmail.com** with details. Please do **not** open a public issue
for security problems. We aim to acknowledge within 72 hours.

## Scope worth flagging

Supafone Labs sits in the path of live conversations and handles call transcripts, which
may contain PII/PHI. We care especially about:

- Secrets handling — API keys must come from the environment, never code or logs.
- Transcript/PII handling in the replay corpus and optimizer datasets.
- Any path where the oracle could block, stall, or crash a live call (a safety bug).
- Prompt-injection from caller speech influencing tool calls or injected instructions.
