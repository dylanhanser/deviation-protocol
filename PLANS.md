# Deviation Protocol Roadmap

This file is a concise navigation aid for the current baseline, next phase,
and intentional deferrals. Detailed design remains in its owning documents.

## Current Baseline

- Branch: `main`
- Commit: `c473fc586219a126ff17002bd5f0c7dedaf6b5c5`
- Latest completed phase: Phase 3.0
- Repository status: clean

## Phase Status

| Phase | Status |
| --- | --- |
| Phase 1 | Complete |
| Phase 2.1 | Complete |
| Phase 2.2 | Complete |
| Phase 2.3a | Complete |
| Phase 2.3b | Complete |
| Phase 2.4a | Complete |
| Phase 2.4b | Complete |
| Phase 3.0 | Complete |
| Phase 3.1a | Implemented; awaiting independent audit |
| Phase 3.1b and later | Not started |

## Phase 2.4b

Phase 2.4b completed the first-copy public API playthrough:

- The public API is fully playable for the first copy.
- The `life_disputed` to resolution route is reachable in production.
- `protocol_broken` and `record_challenged` are successful endings.
- `deadline_reached` is a failure ending.
- Deterministic end-to-end and MySQL routes cover the complete path.

## Phase 3.1a

The first player-facing Web batch is implemented but not yet independently
audited or released. It adds:

- an isolated React/Vite/TypeScript project under `web/`;
- Zod-backed public DTOs and one public API client boundary;
- scenario/role discovery, session creation, and manual full View reads;
- MSW contract tests plus a minimal accessible verification page; and
- no actions, polling, persistence recovery, authentication, or deployment.

## Next Step

Run an independent XHigh read-only review of Phase 3.1a and its verification
evidence. Do not begin Phase 3.1b as part of that review. Later Web batches are
expected to:

- support free input, `CONTINUE`, request polling, and reconnection recovery; and
- avoid direct reads of snapshots or internal job state.

## Deferred by Design

- Memory rebuild and compaction.
- Scenario replay and `scenario_run_id`.
- Cross-scenario NPC identity.
- `DeviationEvaluator`.
- Combat.
- Worker, queue, or distributed system.

## Stable Decisions

- Models generate narrative candidates only.
- Local server rules own state-write authority.
- Ordinary scenarios are not designed for replay solely to enable collection.
- Live DeepSeek is not a normal test dependency.
- MySQL is the only database target; there is no SQLite fallback.

## Workflow

1. Sol High implements the bounded phase.
2. Sol XHigh performs an independent review.
3. Run the applicable Quick, Offline, and MySQL verification.
4. Explicitly stage only reviewed paths.
5. Commit and push only when separately authorized.

## Document Ownership

- `PLANS.md` records phase status, next steps, and intentional deferrals only.
- Architecture details: `docs/architecture.md`.
- Memory boundaries: `docs/player_memory.md`.
- Playable-slice contract: `docs/playable_vertical_slice.md`.
- Engineering guardrails: `docs/engineering/guardrails.md`.
