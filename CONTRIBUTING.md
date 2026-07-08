# Contributing to Supafone Labs

Thanks for helping build the second mind for voice AI.

## Ground rules

- **Degrade-safe is sacred.** Nothing in Supafone Labs may block or break a host
  conversation. Oracle work runs off the hot path, time-bounded, and swallows its own
  errors. PRs that can throw into a live call will be rejected.
- **Reuse Adhera primitives.** Don't duplicate `CanonicalEvent` / `RuntimeState` /
  `RuntimeDecision`. Import from `adhera.*`.
- **Optional deps stay optional.** Any `anthropic` / `openai` / `dspy` / `langchain` /
  provider SDK import must be lazy/guarded so the core imports with zero extras.
- **Types + docstrings** on everything public.

## Dev setup

```bash
git clone https://github.com/samthedataman/supafone-labs
cd supafone_labs
make install        # editable installs + pytest + ruff
make test
```

## Adding a provider adapter

A provider adapter lives in `packages/adhera/src/adhera/adapters/<provider>.py` and
implements `parse_event` (raw → canonical events) and `compile` (decision → provider
action), plus a `capabilities()` declaration. Add a sample-payload test in
`packages/adhera/tests/`. See `docs/providers.md` for the contract and an example.

## Pull requests

1. Branch from `main`.
2. `make lint && make test` must pass.
3. Add/extend tests for behavior changes.
4. Describe the *why* in the PR body.
5. By contributing you agree your work is licensed under the project's MIT license.

## Reporting bugs / requesting features

Use the GitHub issue templates. For anything security-related, see
[SECURITY.md](SECURITY.md) — **do not** open a public issue.
