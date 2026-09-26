import type {
  CreateLabsAgentRequest,
  GetLabsAgentOptions,
  LabsRealtimeSelection,
  SupafoneLabs,
} from "./index.js";

export type S2SProviderName = "ultravox" | "openai" | "google" | "xai" | "smallest";
export interface S2SModelOptions {
  model?: string;
  voice?: string;
}
export interface S2SOptions extends S2SModelOptions {
  provider?: S2SProviderName;
}

/** Shared parent for Supafone-hosted S2S agents. Vendor keys stay on the server. */
export class SupafoneS2S {
  readonly provider: S2SProviderName;
  private readonly selection: LabsRealtimeSelection | null;

  constructor(protected readonly client: SupafoneLabs, options: S2SOptions = {}) {
    const provider = options.provider ?? "ultravox";
    if (!["ultravox", "openai", "google", "xai", "smallest"].includes(provider)) {
      throw new Error("Unsupported Supafone S2S provider");
    }
    if (provider === "ultravox" && (options.model !== undefined || options.voice !== undefined)) {
      throw new Error("Configure Ultravox voices through the agent's voice settings");
    }
    for (const field of ["model", "voice"] as const) {
      const value = options[field];
      if (value !== undefined && (typeof value !== "string" || !value.trim())) {
        throw new Error(`${field} must be a non-empty string`);
      }
    }
    this.provider = provider;
    this.selection = provider === "ultravox" ? null : {
      provider,
      ...(options.model !== undefined ? { model: options.model.trim() } : {}),
      ...(options.voice !== undefined ? { voice: options.voice.trim() } : {}),
    };
  }

  /** A fresh wire selection; null explicitly restores the default Ultravox runtime. */
  get realtime(): LabsRealtimeSelection | null {
    return this.selection ? { ...this.selection } : null;
  }

  /** Create through the normal hosted agent factory with this provider. */
  create(input: Omit<CreateLabsAgentRequest, "realtime">) {
    if ("realtime" in input) {
      throw new Error("Set provider/model/voice on the S2S adapter, not create({realtime: ...})");
    }
    return this.client.labs.agents.create({
      ...input,
      ...(this.realtime ? { realtime: this.realtime } : {}),
    });
  }

  /** Change the saved selection for subsequent calls, preserving the agent and number. */
  apply(agentKey: string, options: GetLabsAgentOptions = {}) {
    this.checkAgentKey(agentKey);
    return this.client.labs.agents.update(agentKey, { realtime: this.realtime }, options);
  }

  /** Preview the saved agent. Call apply first when switching providers. */
  testCall(agentKey: string, options: GetLabsAgentOptions = {}) {
    this.checkAgentKey(agentKey);
    return this.client.labs.agents.testCall(agentKey, options);
  }

  private checkAgentKey(agentKey: string): void {
    if (typeof agentKey !== "string" || !agentKey.trim()) throw new Error("agentKey is required");
  }
}

export class UltravoxS2S extends SupafoneS2S {
  constructor(client: SupafoneLabs) { super(client, { provider: "ultravox" }); }
}
export class OpenAIS2S extends SupafoneS2S {
  constructor(client: SupafoneLabs, options: S2SModelOptions = {}) {
    super(client, { ...options, provider: "openai" });
  }
}
export class GeminiS2S extends SupafoneS2S {
  constructor(client: SupafoneLabs, options: S2SModelOptions = {}) {
    super(client, { ...options, provider: "google" });
  }
}
export class GrokS2S extends SupafoneS2S {
  constructor(client: SupafoneLabs, options: S2SModelOptions = {}) {
    super(client, { ...options, provider: "xai" });
  }
}
/** Smallest AI Hydra: full-duplex audio, without transcript events. */
export class HydraS2S extends SupafoneS2S {
  constructor(client: SupafoneLabs, options: S2SModelOptions = {}) {
    super(client, { ...options, provider: "smallest" });
  }
}
