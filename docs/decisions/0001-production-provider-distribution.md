# ADR 0001: Production Provider Distribution

Status: **Accepted design — not implemented**

## Context

The implemented application has a supplier-neutral `NarrativeProvider`
interface, a normally configured DeepSeek adapter, and an isolated deterministic
Demo Provider. Those components do not provide player-selectable
multi-Provider routing, commercial quotas, billing, or credential distribution.

Production distribution must let a player explicitly select an available
Provider/model channel without exposing upstream credentials or silently
changing Provider identity. The accepted conceptual boundary is:

```text
player
  -> deviation-protocol backend/application identity
  -> Production Distribution Gateway
  -> explicitly selected upstream Provider/model
```

This ADR assigns the design to Phase 4.0. It does not select or implement a
gateway product.

## Decision

- Real DeepSeek, OpenAI, and Gemini credentials remain server-side. Players
  never receive upstream Provider credentials.
- A player explicitly selects an available Provider/model channel. Each request
  uses only that selected route.
- Silent cross-Provider fallback is prohibited. If the selected upstream
  Provider is unavailable, the system preserves Provider identity and returns
  an explicit unavailable or failure result.
- A self-controlled **Production Distribution Gateway** (also called a
  **Provider Distribution Gateway**) performs authentication, quota checks,
  rate limiting, usage metering, and abuse control.
- Quota or pricing reflects the selected Provider/model and metered usage.
- An unavailable or failed route is not reported or charged as a successful
  completion.
- The deterministic Demo Provider remains isolated from commercial Provider
  distribution.
- Current Demo functionality does not implement multi-Provider routing,
  key-pool distribution, billing, or commercial quota management.

Provider selection does not grant narrative authority. A selected Provider
still returns an untrusted proposal; the engine and its trusted policies retain
authority over objective mechanics, state, facts, and canon.

## Security rationale

Keeping credentials behind the backend and gateway prevents client extraction,
direct upstream use, and user-controlled route substitution. Explicit route
selection plus fail-closed Provider identity prevents a failure on one vendor
from being disguised as output from another. Server-side metering and abuse
controls create one accountable boundary for upstream consumption without
moving game authority into the distribution layer.

## Operational implications

- The gateway must authenticate deviation-protocol application identities and
  bind each request to the explicitly selected Provider/model route.
- Availability, usage, quota, and charge outcomes need auditable server-side
  records without exposing upstream secrets to clients.
- Failure handling must distinguish successful completions from unavailable,
  rejected, failed, and any future partial-generation outcomes.
- Provider-specific availability and commercial policy remain deployment
  concerns; they do not change the application `NarrativeProvider` authority
  boundary.
- Demo composition, storage, deterministic metadata, and replay evidence remain
  separate from this production network path.

## Consequences

The design preserves Provider identity and makes cost control enforceable at a
trusted boundary. It also means availability is not improved by silently
rerouting a request: the player receives an explicit failure and may make a new
selection according to a future public product flow. Operating the gateway
adds authentication, metering, abuse-control, reconciliation, and regional
policy responsibilities.

## Non-goals

- Selecting a particular gateway implementation.
- Implementing Phase 4.0 in the current Demo or Web walkthrough phases.
- Giving a Provider authority over objective game mechanics or permanent
  state.
- Treating deterministic Demo output as a billable upstream completion.
- Promising universal Provider availability in every region.

## Deferred

- Final gateway implementation.
- Whether New API, One API, or another system is used.
- Exact model catalogue.
- Exact pricing and quota formula.
- Failure and partial-generation charging details.
- Key-pool allocation and rotation policy.
- Per-account and per-IP rate limits.
- Abuse-detection thresholds.
- Final mainland-China OpenAI availability policy.
- Whether regional availability is determined by IP, account region, sales
  region, or another signal.

## Related documents

- [Project roadmap](../../PLANS.md)
- [Implemented and future Provider boundaries](../narrative_provider.md)
- [Run Protocol design](../run_protocol.md)
- [NPC Relationship and Temporary Residence](../npc_relationship_residence.md)
