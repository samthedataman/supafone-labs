import type { CreateLabsAgentRequest, GetLabsAgentOptions, SupafoneLabs, UpdateLabsAgentRequest } from './index.js';

/** Shared hosted Agent Factory operations for hybrid, S2S and pipeline routes. */
export abstract class SupafoneVoice {
  constructor(protected readonly client: SupafoneLabs) {}
  abstract routePayload(creating?: boolean): UpdateLabsAgentRequest;
  create(input: Omit<CreateLabsAgentRequest, 'realtime' | 'pipeline'>) {
    if ('realtime' in input || 'pipeline' in input) {
      throw new Error('Set the route on the voice/S2S adapter, not create({realtime: ... or pipeline: ...})');
    }
    return this.client.labs.agents.create({ ...input, ...this.routePayload(true) } as CreateLabsAgentRequest);
  }
  /** Applies to subsequent calls, preserving workflow, numbers and history. */
  apply(agentKey: string, options: GetLabsAgentOptions = {}) {
    this.checkAgentKey(agentKey);
    return this.client.labs.agents.update(agentKey, this.routePayload(), options);
  }
  /** Preview saved configuration; never implicitly switch the speaking model. */
  testCall(agentKey: string, options: GetLabsAgentOptions = {}) {
    this.checkAgentKey(agentKey);
    return this.client.labs.agents.testCall(agentKey, options);
  }
  protected checkAgentKey(agentKey: string) {
    if (typeof agentKey !== 'string' || !agentKey.trim()) throw new Error('agentKey is required');
  }
}
