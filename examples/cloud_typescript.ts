/**
 * Supafone Labs Cloud from TypeScript — oracle, TTS, and live multilingual STT
 * with one key. No SDK needed; it's plain HTTP + WebSocket.
 *
 *   npm i ws && SUPAFONE_LABS_API_KEY=sl_live_... npx tsx cloud_typescript.ts
 */
import WebSocket from "ws";
import { writeFileSync } from "node:fs";

const API = "https://api.labs.supafone.ai";
const KEY = process.env.SUPAFONE_LABS_API_KEY!;
const auth = { Authorization: `Bearer ${KEY}` };

// 1) The oracle: turn a live transcript into a silent coaching directive.
async function oracle(transcript: string): Promise<string> {
  const r = await fetch(`${API}/v1/oracle/complete`, {
    method: "POST",
    headers: { ...auth, "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "supafone-labs-oracle", // or any claude-* / gpt-* / grok-* id
      messages: [
        {
          role: "system",
          content:
            "You are the coaching core of a second mind for a live voice agent. " +
            "Return ONE short silent directive the agent reads but never speaks.",
        },
        { role: "user", content: transcript },
      ],
    }),
  });
  if (!r.ok) throw new Error(`oracle: ${r.status} ${await r.text()}`);
  return (await r.json()).text;
}

// 2) Hosted TTS: four engines, one namespace.
async function speak(text: string, voice = "supafone-labs-calm-en"): Promise<void> {
  const r = await fetch(`${API}/v1/tts`, {
    method: "POST",
    headers: { ...auth, "Content-Type": "application/json" },
    body: JSON.stringify({ voice, text }),
  });
  if (!r.ok) throw new Error(`tts: ${r.status}`);
  writeFileSync("reply.wav", Buffer.from(await r.arrayBuffer()));
}

// 3) Live multilingual STT: stream PCM in, language-tagged Results out.
function liveTranscribe(sampleRate = 16000): WebSocket {
  const ws = new WebSocket(
    `${API.replace("https", "wss")}/v1/stt/live?api_key=${KEY}` +
      `&language=multi&encoding=linear16&sample_rate=${sampleRate}`,
  );
  ws.on("message", (m) => {
    const d = JSON.parse(m.toString());
    const alt = d.channel?.alternatives?.[0];
    if (alt?.transcript)
      console.log(`[${alt.languages?.join(",") ?? "?"}]`, alt.transcript, d.is_final ? "(final)" : "");
  });
  return ws; // then ws.send(pcmChunk) per audio frame
}

// 4) The audit trail: every whisper, itemized and billed.
async function logs(): Promise<void> {
  const r = await fetch(`${API}/v1/logs?limit=10`, { headers: auth });
  console.table((await r.json()).logs);
}

(async () => {
  const directive = await oracle(
    "caller: I was rear-ended at a red light yesterday and my neck hurts.",
  );
  console.log("whisper:", directive);
  await speak("I'm so sorry to hear that. Are you safe right now?");
  await logs();
})();
