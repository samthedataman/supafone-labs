# Log Streaming

Developers need to see what the system is doing: oracle calls, whispers, TTS,
STT, call reports, provider metadata, latency, and billing seconds. Supafone
Labs exposes both snapshots and an SSE stream.

## Snapshot

TypeScript:

```ts
const { logs } = await supafone.logs(100);
console.table(logs.map((log) => ({
  id: log.id,
  endpoint: log.endpoint,
  seconds: log.seconds_billed,
  duration: log.duration_ms,
  detail: log.detail,
})));
```

Python:

```python
logs = supafone.logs(100)["logs"]
for row in logs:
    print(row["id"], row["endpoint"], row["detail"])
```

REST:

```bash
curl "https://api.labs.supafone.ai/v1/logs?limit=100" \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY"
```

## Live SSE Stream

TypeScript:

```ts
for await (const log of supafone.streamLogs({
  limit: 100,
  pollMs: 1000,
  snapshot: true,
})) {
  console.log(log.at, log.endpoint, log.detail, log.meta);
}
```

Python:

```python
for log in supafone.stream_logs(limit=100, poll_ms=1000, snapshot=True):
    print(log["at"], log["endpoint"], log["detail"])
```

REST:

```bash
curl -N "https://api.labs.supafone.ai/v1/logs/stream?limit=100&poll_ms=1000&snapshot=true" \
  -H "Authorization: Bearer $SUPAFONE_LABS_API_KEY"
```

Each event is emitted as:

```text
event: log
id: 123
data: {"id":123,"endpoint":"oracle","detail":"...","meta":{"provider":"anthropic"}}
```

## Builder UI Behavior

The builder should have a persistent log rail:

- connect with the Labs key,
- show latest snapshot immediately,
- continue with SSE,
- filter by endpoint and provider,
- show provider/model/voice from `meta`,
- show duration and billed seconds,
- copy a log row as JSON.

If SSE is unavailable in the browser environment, poll `/v1/logs` and de-dupe
by `id`.

## MCP Logs

Claude Desktop tools are request/response, so the MCP server exposes bounded
polling instead of an infinite SSE stream:

```json
{
  "limit": 100,
  "iterations": 10,
  "intervalSeconds": 2
}
```

Use `tail_logs` or `poll_logs` for agent-team debugging.
