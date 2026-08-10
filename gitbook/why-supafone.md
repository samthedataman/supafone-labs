# 💡 Why Supafone — the pain points, and the fixes

Building a production voice agent today means fighting six problems at once.
Supafone's stack exists to remove them. **One API key** (`sl_…`) drives all of
it — planning, provisioning, supervision, QA, grading, and the builder copilot.

## The six pain points

| Pain | What it looks like | The Supafone fix |
| --- | --- | --- |
| **Every new agent starts as a blank prompt** | A developer spends days turning a business brief into prompts, stages, transitions, tools, and fallbacks, then repeats the work for the next customer. | **Hosted call planner**: one description becomes a complete, editable 3–8 stage program. The private service keeps the model key; validation and a safe deterministic fallback keep creation reliable. |
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

## What this changes for developers and customers

Developers can use raw REST, Python, TypeScript, or MCP against the same
versioned plan and agent contract. They can preview, edit, approve, diff, and
store the plain JSON rather than trusting an invisible prompt. Their frontend
never needs a model credential or carrier secret to generate the plan.

Customers receive a consistent working flow—greeting, discovery,
qualification or routing, confirmed action, and close—plus the recordings,
transcripts, summaries, and supervision needed to operate it. They are not
locked into generated copy: every stage remains editable before creation and
observable afterward.
