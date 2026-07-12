# 💡 Why Supafone — the pain points, and the fixes

Building a production voice agent today means fighting five problems at once.
Supafone's stack exists to delete them. **One API key** (`sl_…`) drives all of
it — provisioning, supervision, QA, grading, the builder copilot.

## The five pain points

| Pain | What it looks like | The Supafone fix |
| --- | --- | --- |
| **You can't see failures until a customer hits one** | Agents pass the demo, then hallucinate a refund policy on call #400. | **Self-healing watcher**: every live call is tapped, a supervisor oracle watches the transcript off the latency path and *whispers* corrections into the agent's native control channel — silently, mid-call. |
| **No objective function** | "Did the agent do well?" is a vibe, so prompts drift and regressions ship. | **The objective function is explicit**: every agent carries an operator objective; every call is graded against it — not against generic "helpfulness". |
| **LLM judges give noisy scores** | The same call scores 0.62 then 0.81; dashboards are judge noise. | **SSR grading**: the judge picks one of five *nominal* levels — "the agent did *{poorly, ok, good, great, perfectly}* at achieving the objective". The score AND a full bucket distribution are derived deterministically from the label. Reliable labels in; a real score distribution out. |
| **Testing is manual role-play** | Someone calls the agent, tries three things, ships. | **Auto QA suites** (`POST /v1/qa/suite`): one call reads your agent's own objective, invents adversarial test callers targeted at *its* specific rules, plays each as a real mock call against your configured agent, then reports pass/fail per assertion + an SSR grade per call. |
| **You can't measure whether supervision helps** | "The watcher seems better?" | **A/B by construction** (`POST /v1/qa/run`): every scenario plays twice — bare agent vs. supervised agent — and the report is the measured lift. |

## The loop, end to end

```
objective  →  live calls  →  watcher whispers (self-healing)
    ↑                                        ↓
optimizer  ←  SSR grades  ←  auto QA suite (adversarial mock calls)
```

1. **Define** the objective once (builder, SDK, or the copilot chat).
2. **Run** live calls — the watcher supervises in real time.
3. **Test** with `qa/suite`: adversarial callers generated from the objective
   attack your real agent config in mock calls.
4. **Grade** every call (live or mock) with SSR nominal levels against the
   objective.
5. **Improve**: the optimizer (OPRO-style) rewrites the standing directive
   from graded calls; A/B runs prove the lift before you trust it.

## One key

Your `sl_` key is the single credential for **everything** — literally. It
authenticates the Labs gateway (oracle whispers, TTS/STT, QA generation and
runs, SSR grading, the builder wizard, usage and logs) *and* the main product
API (campaigns, dialing, agents, calls): the product API introspects the key
against the Labs cloud and maps it to your app.supafone.ai account by owner
email. Set one env var — `SUPAFONE_TOKEN=sl_live_...` — and the MCP server and
both SDKs work end to end; in the SDKs a lone `sl_` credential fills both the
labs and account lanes automatically. Account login (email/password or JWT)
still works everywhere it did before.
