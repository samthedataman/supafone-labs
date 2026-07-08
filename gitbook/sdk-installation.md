# SDK Installation

Supafone Labs publishes a Python package and an unscoped TypeScript package.

## Python

```bash
pip install supafone-labs
```

Recommended full install for hosted cloud, HTTP, STT, and server helpers:

```bash
pip install "supafone-labs[all]"
```

Minimal usage:

```python
import supafone_labs

brain = supafone_labs.supercharge(my_agent)
```

Explicit usage:

```python
from supafone_labs import SupafoneLabs

brain = SupafoneLabs(
    provider="ultravox",
    llm="hosted",
    agent_label="intake",
)
```

Environment:

```bash
export SUPAFONE_LABS_API_KEY=sl_live_...
```

If no Labs key is present, use BYO provider keys such as `ANTHROPIC_API_KEY`,
`OPENAI_API_KEY`, `XAI_API_KEY`, or local fake providers for tests.

## TypeScript

```bash
npm i supafone-labs
```

ESM:

```ts
import { Supafone } from "supafone-labs";

const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_LABS_API_KEY!,
});
```

CommonJS:

```js
const { Supafone } = require("supafone-labs");
```

Hosted-agent usage:

```ts
const supafone = new Supafone({
  apiKey: process.env.SUPAFONE_LABS_API_KEY || process.env.SUPAFONE_API_KEY!,
  supafoneApiKey: process.env.SUPAFONE_API_KEY!,
  supafoneApiBaseUrl: "https://api.supafone.ai",
});
```

The package works in Node 18+ and browsers using native `fetch`. Live STT needs
a global `WebSocket`; on older Node versions, pass a WebSocket implementation.

```ts
import WebSocket from "ws";

const live = supafone.liveTranscribe({
  WebSocketImpl: WebSocket,
  language: "multi",
  onResult: (r) => console.log(r.transcript)
});
```

## Package Names

| Ecosystem | Install name | Import name |
| --- | --- | --- |
| Python | `supafone-labs` | `supafone_labs` |
| npm | `supafone-labs` | `Supafone` from `"supafone-labs"` |

