import { SupafoneVoice } from "./voice.js";
import type {
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
export class SupafoneS2S extends SupafoneVoice {
  readonly provider: S2SProviderName;
  private readonly selection: LabsRealtimeSelection | null;

  constructor(client: SupafoneLabs, options: S2SOptions = {}) {
    super(client);
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

  routePayload(creating = false) {
    // Explicit realtime (including null) clears a saved pipeline server-side.
    return creating && !this.realtime ? {} : { realtime: this.realtime };
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
