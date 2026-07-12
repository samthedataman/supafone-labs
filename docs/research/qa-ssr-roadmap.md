# QA/SSR credibility roadmap (from methodology research, 2026-07-10)

Research verdict: our two core bets are RIGHT — nominal SSR labels beat numeric
judge scores (judge float scores show Krippendorff alpha as low as 0.33), and
paired same-scenario A/B is the single biggest variance win (arm correlation
0.3-0.7). Do NOT switch to pairwise A-vs-B judging (it manufactures winners).

## Sprint order

0. **BUG (fix first, 5 lines)**: `_ssr_closest_label` silently maps parse
   failures to "ok" (0.35) — attenuates measured lift. Parse failures must
   become an `ungraded` outcome, excluded + counted, never defaulted.
1. **S — 3 judge votes per call**, median label (ordinal), report
   `votes/unanimous/spread`; escalate to 5 votes when spread >= 2. Optional:
   vote #3 from a different model family (PoLL jury, ~7x cheaper than one
   frontier judge, kills self-preference bias).
2. **S/M — bootstrap CI over the paired lift**: resample SCENARIOS 1000x,
   report `+0.12 [95% CI +0.05,+0.19] · nW/nT/nL` + a 5x5 label-shift matrix.
   "Significant" only when CI excludes 0. Wilson intervals for binary rates.
3. **M — golden calibration set**: 100-200 human-labeled calls, quadratic-
   weighted Cohen's kappa (target >= 0.6), auto re-run + judge config
   pinned/versioned so judge drift is a diff, not a mystery.
4. **M — non-flaky CI gate**: block only when CI excludes 0 AND effect >=
   0.03; warn band otherwise; quarantine scenarios whose median label flips
   across identical reruns; baseline = rolling master window.
5. **M/L — perturbation replays** (text-level, no audio needed): ASR-noise
   turn corruption, entity-stress (spelled emails/names — the #1 real-world
   killer per tau-Voice: agents keep only 30-45% of text capability on
   voice), barge-in simulation, disfluency injection. Report
   `robustness_delta` per axis. Headline product feature.

## Defaults
votes=3 (median, temp 0.3-0.7, pinned judge version) · quick suite=50 paired
scenarios · headline/gate suite=100-200 · mix 40% happy/30% edge/15% error/
10% adversarial/5% ASR-stress · 6-12 turns, ONE objective per scenario ·
golden set refresh quarterly or on judge change.

## Report UI must-haves (trust-building order)
1. Lift as interval + W/T/L, never a point; "not resolved" badge + power hint.
2. 5x5 paired label-shift matrix (where the lift comes from).
3. Raw votes per call + unanimity badge + suite unanimity %.
4. Judge provenance + calibration kappa badge ("last calibrated" date).
5. Five label bars as the PRIMARY distribution; caption the 10-bucket
   smoothed histogram as illustrative until backed by measured vote spread.
6. Robustness panel: clean vs ASR-noise vs barge-in per arm.
7. Per-scenario drill-down: rationale, vote-flip, quarantine flag, transcript.
8. History vs rolling baseline sparkline with warn/block bands.

Full source list lives in the research transcript (Rating Roulette, Coin Flip
Judge, Likert or Not, PoLL juries, Anthropic error-bars-for-evals, tau-Voice,
VoiceBench, MEDSAGE, Hamming/Cekura/Braintrust guides).
