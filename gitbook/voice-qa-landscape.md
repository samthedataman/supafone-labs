# ✅ Testing Voice Agents (and the 2026 QA Landscape)

🐍 [Python — `pip install "supafone-labs[all]"`](https://pypi.org/project/supafone-labs/) ·
🟦 [TypeScript — `npm i supafone-labs`](https://www.npmjs.com/package/supafone-labs) ·
⭐ [GitHub — samthedataman/supafone](https://github.com/samthedataman/supafone) ·
🌐 [labs.supafone.ai](https://labs.supafone.ai) ·
📄 [*Grading the Call* (paper)](https://labs.supafone.ai/research.html)

Your voice agent fails probabilistically: the same caller intent, phrased
twice, can produce a clean booking and a hallucinated one. This page shows
you how to test for that with Supafone Labs — and how what you get here
compares to every other voice-QA tool you might be evaluating in 2026.

## Test your agent in 30 seconds

You don't write test cases. The suite is generated from your agent's own
prompt, played against your **real** configuration, and judged twice per call.

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({ apiKey: process.env.SUPAFONE_LABS_API_KEY! });
await supafone.login(process.env.SM_EMAIL!, process.env.SM_PASSWORD!);

const suite = await supafone.qa.suite({ count: 4, turns: 2 });

console.log(suite.summary);
// {
//   tests: 4, passed: 3,
//   avg_ssr_score: 0.57,
//   ssr_histogram: { poorly: 0, ok: 1, good: 2, great: 1, perfectly: 0 },
//   oracle_calls_billed: 21
// }
```

```python
from supafone_labs import Supafone

supafone = Supafone(api_key="sl_live_...")
supafone.labs_login("you@company.com", "...")

suite = supafone.qa.suite(count=4, turns=2)
print(suite["summary"]["ssr_histogram"])
```

Each result gives you the scenario that was played (persona + opening line),
the one assertion your agent had to satisfy, a pass/fail verdict with quoted
evidence, the full transcript, and an SSR grade. Want scenarios without
running them? `qa.generate({ agentPrompt, count })` works with just your API
key.

## What each piece does

**Scenarios come from your prompt.** `POST /v1/qa/generate` reads your
agent's system prompt and produces adversarial scenarios — an angry refund
caller, a rambler who buries the intent, a caller who asks for the one thing
your prompt forbids. Each scenario is `{title, persona, opener, assertion}`
where the assertion is a single falsifiable claim ("the agent must not quote
a fee").

**Mock calls run against your real agent.** Not a copy, not a staging
config — the same prompt, stages, and standing directive that answer your
production calls. An adversarial caller model plays the persona; your agent
responds turn by turn.

**Every call is judged twice.** First: did the agent satisfy the scenario's
assertion? Pass/fail, with the judge quoting the moment that decided it.
Second: the SSR grade against your overall objective (next section).

**A/B the supervisor.** `qa.run()` plays every scenario twice — once bare,
once with the Labs watcher whispering silent corrections — and reports the
**lift**: how much supervision improved the score, per scenario. That tells
you exactly which failure modes the watcher fixes before you pay for it in
production.

```ts
const qa = await supafone.qa.run({ turns: 2 });
// qa.results[0].lift            -> +0.42 on "refund bully"
// qa.summary.avg_lift           -> 0.31
// qa.summary.passed_supervised  -> 4/4 (vs 2/4 unsupervised)
```

**Production calls get the same grading.** Turn on `postCallAnalysis: true`
(TS) / `post_call_analysis=True` (Python) and every finished call you report
is automatically classified against your objective — achieved/missed,
per-criterion verdicts, failure reasons — blended with deterministic ground
truth (did the booking tool actually confirm?), and filed for the optimizer.

```ts
const supafone = new Supafone({ apiKey, postCallAnalysis: true });
const { analysis } = await supafone.reportCall({
  session_id: "call-1", agent: "intake",
  transcript: "agent: Hi...\ncaller: I want to book...\nagent: Booked for 3pm.",
  ground_truth: { booking_requested: true, booking_verified: true },
});
// analysis.achieved -> true, analysis.failure_reasons -> []
```

**Graded calls improve the agent.** `optimizer.improve()` rewrites your
agent's standing directive (OPRO-style) from the accumulated reports, and
`GET /v1/optimizer/objective/stats` shows achievement rate **per directive
version** — so you can see whether each rewrite actually helped.

## How SSR grading works (and why not a 0–100 score)

Ask an LLM judge for a number between 0 and 1 and you get noise wearing a
decimal point. Ask it to pick one of five ordered descriptions and it's
remarkably consistent. SSR does the second thing:

> "The agent did **{poorly | ok | good | great | perfectly}** at achieving
> the objective."

The judge picks exactly one label — never a number. Each label maps
**deterministically** to a canonical score and a distribution over ten score
buckets:

```json
{
  "label": "great",
  "score": 0.78,
  "distribution": [0, 0, 0, 0.02, 0.07, 0.18, 0.30, 0.28, 0.13, 0.02],
  "rationale": "Confirmed the booking only after the tool returned success."
}
```

The only stochastic step is the label choice — the judgment LLMs make most
reliably. Aggregate a hundred calls and the histogram has a real statistical
shape instead of averaged judge noise. No other tool in the table below does
this; they return raw judge scalars or binary pass/fail.

## How this compares to other tools

If you're evaluating the field, this is it — six dimensions across every
platform that matters in 2026:

| Tool | Test generation | Simulation | Scoring | A/B & regression | CI | Pricing |
| --- | --- | --- | --- | --- | --- | --- |
| **Supafone Labs** | Auto from your agent's own prompt/objective | Text-level mock calls vs your **real** config (audio mode on the roadmap) | Pass/fail assertions + **SSR nominal grading** with deterministic distributions | **Supervision-lift A/B**; achievement trend per directive version | API today (Action + webhooks on the roadmap) | Metered oracle credits, exact `oracle_calls_billed`, free minutes at signup |
| **Hamming** | Auto from agent prompt; prod calls → tests; red-team | Real phone calls at scale (1k+ concurrent), IVR/DTMF | 50+ metrics, STT/LLM/TTS breakdowns | Agent-version A/B, golden-call checks | GH Actions/Jenkins, webhooks | Sales-led (contact us) |
| **Coval** | Personas/permutations (27 voices, 10 languages, 20 environments) | Voice-native audio + text | Metrics + tool-call validation + verdict cards with human override | Vendor bakeoffs, behavioral regression | GH Actions, schedules, CLI | $100 / $500 / $4,500+ per mo, metered sim + monitoring minutes |
| **Roark** | From your real call types; prod replay → tests | Real audio, 45 languages/accents, noise | Audio-native metrics (emotion, stress, pace) + rubrics | Prompt diffs, cross-metric regression watch | Merge gates, SDKs, webhooks | $0.15→$0.05/sim-min + provider passthrough; $0.04/metric/min |
| **Cekura** | Auto from agent description; persona library | Real telephony, parallel calls | Instruction/tool metrics; tunable judges | Trouble-spot replays | Dependency-free GH Action, **cron suites**, tags, MCP | $30/mo + 750 credits (≈$0.20/sim-min) |
| **Bluejay** | Persona sims from real customer profiles | Production replay + simulation | Task completion, tone, conversion | Test→monitor→improve loop | Yes (sales-led) | Sales-led |
| **Vapi (built-in)** | You write tester scripts + rubrics | Chat mode, or two assistants on a real call | LLM judges rubric → pass/fail + reasoning | 5 attempts/test; suites being replaced by "Simulations" | Dashboard only | Test calls billed like regular calls |
| **Retell (built-in)** | You write persona prompts | Text-level chat roleplay, batch | Your success criteria per test | Batch re-runs | Webhooks/API | Included in platform usage |
| **Bland (built-in)** | 8 failure categories, golden sets | Batch-test API, real calls | Infra + prompt + outcome layers | Live-traffic A/B splits | Built into deploys | Platform usage |
| **promptfoo (OSS)** | YAML tests; `simulated-user` personas; red-team | Text-only | Assertions + `llm-rubric` | Run diffs | First-class CLI/CI | Free (OSS) |
| **DeepEval (OSS)** | `ConversationalGolden` → simulator | Text-only | Multi-turn metrics, G-Eval | Dataset versioning (cloud) | pytest-style | Free; cloud from $9.99/user/mo |
| **Braintrust** | Synthetic data via LLM + TTS audio | Component + end-to-end, Realtime audio | Autoevals + judges + custom scorers | Experiment comparison, score distributions | SDK evals per change | Free tier; Pro $249/mo |
| **voicetest / fixa (OSS)** | Imported/manual cases | Multi-turn vs Retell/Vapi/Bland/LiveKit | LLM judges → pass/fail | Exports | GH Action fails build | Apache 2.0 |

**Practical guidance:**

- Already on **Vapi/Retell/Bland**? Their built-in tests are fine smoke
  checks, but you author every scenario yourself and scoring is a raw LLM
  verdict. Supafone generates the suite and controls judge noise.
- Need **real phone-audio testing today** (accents, noise, barge-in)? That's
  Hamming/Coval/Roark/Cekura territory until our audio mode ships — see the
  roadmap below.
- Want **free and local**? promptfoo and DeepEval are the strongest OSS
  transcript-level options; neither touches audio or measures supervision.
- Benchmarking **models, not your agent**? That's
  [τ²-bench](https://github.com/sierra-research/tau2-bench) (simulated users,
  pass^k reliability, now with a full-duplex voice mode) and
  [VoiceBench](https://arxiv.org/abs/2410.17196) (6,783 spoken instructions
  across 8 task sets).

One number worth internalizing from τ-bench: **pass^k**. If your agent
succeeds 90% of the time per call, the chance all 8 of a customer's calls go
clean is 0.9⁸ ≈ 43%. Test repeatedly, not once.

## The vendor field in depth

Evaluating vendors or just curious who's who — here's the funded cohort:

| Company | Raise | Backers | What they're best at |
| --- | --- | --- | --- |
| **Coval** | $28M Series A (Jun 2026) | Norwest, Base10, Twilio Ventures, YC | Enterprise simulation + human review queues; clearest public pricing in the category |
| **Hamming** | $3.8M seed, YC S24 | Mischief + angels | Scale (50K+ concurrent test calls), banking/health compliance reports |
| **Bluejay** | $4M seed, YC Spring '25 | Homebrew | "Human simulation" of 1:1 customer replicas |
| **Cekura** (ex-Vocera, YC F24) | ~$2.4M seed | YC + angels | Developer ergonomics: $30 tier, GitHub Action, cron suites, judge-tuning workbench |
| **Roark** (YC W25) | ~$500K+ | YC, F-Prime, True Ventures, Liquid 2 | Production-first: replay real calls against new logic, audio-native metrics, transparent per-minute pricing |

Dashboard patterns you'll see in their demos (and increasingly in our
console): suite pass/fail matrices and trend lines (Hamming), transcript
verdict cards with human override and review queues (Coval), side-by-side
prompt diffs with per-metric movement (Roark), judge-tuning against recorded
calls (Cekura). Our console's signature views are the **SSR histogram**, the
**supervision-lift ladder**, and the **achievement-per-directive-version
trend** — charts none of them have, because the underlying measurements don't
exist elsewhere.

## What's not here yet (honest roadmap)

Five things you might expect that Supafone QA doesn't do today, in the order
we're building them:

1. **Real-audio test calls.** Today's arena is text-level roleplay — it
   catches prompt/logic/tool failures but not accent, noise, barge-in, or
   latency failures. Planned shape:

   ```http
   POST /v1/qa/suites/{id}/run
   { "mode": "audio",
     "audio": { "voice": "supafone-labs-warm-en", "background": "street",
                "interrupt_rate": 0.2, "dtmf": true } }
   ```

   (Hosted TTS voices the caller over a loopback call to your agent's real
   number; hosted STT feeds the same dual judge. Telephony passes through at
   cost.)

2. **Saved suites + scheduled runs.** Today every `qa.suite()` regenerates;
   caps are 6 scenarios / 3 turns. Planned:

   ```http
   POST /v1/qa/suites            { "name": "intake smoke", "generate": { "count": 24 }, "tags": ["critical"] }
   POST /v1/qa/suites/{id}/run   { "concurrency": 8, "scenarios_tagged": "critical" }
   POST /v1/qa/schedules         { "suite_id": "...", "cron": "0 6 * * *",
                                   "gate": { "min_pass_rate": 0.85, "min_avg_ssr": 0.6 },
                                   "webhook_url": "https://ci.example.com/hooks/qa" }
   ```

3. **Run-over-run regression diffs.**

   ```http
   POST /v1/qa/compare { "run_a": "...", "run_b": "..." }
   → { "regressions": [ { "scenario": "auto_3", "was": "great", "now": "ok",
         "ssr_delta": -0.43 } ], "gate": "fail" }
   ```

4. **A published GitHub Action + webhooks** — `supafone qa run --suite
   intake-smoke --wait --fail-below-ssr 0.6` exiting nonzero on failure, and
   a `qa.run.finished` webhook payload for anything else.

5. **Per-criterion SSR in responses.** The grading module already labels
   named criteria (`"no_hallucinated_facts": "great"`); wiring it through
   `qa.suite` responses and a `GET /v1/qa/ssr/aggregate` endpoint unlocks
   criterion heatmaps. Also coming: `attempts: k` per scenario with pass^k
   reporting.

History you can already build on: every run persists — `qa.history()` /
`GET /v1/qa/runs` returns timestamped scenario/pass/score/evidence rows.

## Using this on a team (and the enterprise question)

For a single developer or small team, what ships today is the point: suites
with zero authoring, judge-noise-controlled scores, supervision priced per
scenario, everything metered in the same credits as the rest of Labs with
exact `oracle_calls_billed` — no sales call.

If you're wondering whether this category supports enterprise budgets: it
demonstrably does — Coval's enterprise tier starts at $4,500/mo and Roark's
at $4,000/mo, sold into banks and healthcare where a bad call is a compliance
event. What those contracts require, and what's on our enterprise track in
order: real-audio simulation (regulated buyers won't accept text-only),
scheduled regression gates, compliance artifacts + SSO/RBAC (compliance
should ship on every tier — gate white-label reports and self-hosting, not
SOC 2), 100%-of-calls production monitoring with human review queues, and
white-label QA reports for agencies.

## Sources

Hamming ([site](https://hamming.ai/), [pricing](https://hamming.ai/pricing), [seed](https://www.businesswire.com/news/home/20241218104943/en/Hamming.ai-Announces-$3.8-Million-Seed-Led-by-Mischief)) ·
Coval ([site](https://www.coval.ai/), [pricing](https://www.coval.ai/pricing), [Series A](https://www.prnewswire.com/news-releases/coval-raises-28-million-series-a-to-define-safety-and-reliability-for-autonomous-voice-agents-302808740.html)) ·
Roark ([site](https://roark.ai/), [pricing](https://roark.ai/pricing), [YC](https://www.ycombinator.com/companies/roark)) ·
Cekura ([site](https://www.cekura.ai/), [pricing](https://www.cekura.ai/pricing), [YC launch](https://www.ycombinator.com/launches/M57-cekura-formerly-vocera-testing-monitoring-for-ai-voice-agents), [GitHub Action](https://docs.cekura.ai/documentation/guides/github-actions-ci-cd)) ·
Bluejay ([seed](https://homebrew.co/blog/2025/08/27/ai-models-are-evolving-fast-but-their-use-is-gated-by-how-easy-it-is-to-test-bluejay-makes-testing-voice-and-text-ai-agents-easy-with-a-usd4-million-seed)) ·
Bland ([testing guide](https://www.bland.ai/blog/how-can-i-test-my-voice-agent-after-building)) ·
Retell ([simulation docs](https://docs.retellai.com/test/llm-simulation-testing), [batch](https://docs.retellai.com/test/batch-test-simulation)) ·
Vapi ([test suites](https://docs.vapi.ai/test/test-suites), [voice testing](https://docs.vapi.ai/test/voice-testing)) ·
promptfoo ([simulated user](https://www.promptfoo.dev/docs/providers/simulated-user/)) ·
DeepEval ([conversation simulator](https://deepeval.com/docs/conversation-simulator)) ·
Confident AI ([pricing](https://www.confident-ai.com/pricing)) ·
Braintrust ([voice evals](https://www.braintrust.dev/articles/how-to-evaluate-voice-agents)) ·
voicetest ([site](https://voicetest.dev/)) · fixa ([GitHub](https://github.com/fixadev/fixa)) ·
τ²-bench ([GitHub](https://github.com/sierra-research/tau2-bench), [paper](https://arxiv.org/abs/2406.12045)) ·
VoiceBench ([paper](https://arxiv.org/abs/2410.17196)) ·
Speechmatics 11-platform roundup ([article](https://www.speechmatics.com/company/articles-and-news/de-risk-your-voice-agent-11-best-voice-agent-testing-platforms))
