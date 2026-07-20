# Deviation Protocol Roadmap

This file is a concise navigation aid for the current baseline, next phase,
and intentional deferrals. Detailed design remains in its owning documents.

## Current Baseline

- Branch: `main`
- Commit: `65af134 feat: add playable scenario progression API`
- Latest completed phase: Phase 2.4a
- Working-tree status at roadmap creation: clean and synchronized with
  `origin/main`

## Phase Status

| Phase | Status |
| --- | --- |
| Phase 1 | Complete |
| Phase 2.1 | Complete |
| Phase 2.2 | Complete |
| Phase 2.3a | Complete |
| Phase 2.3b | Complete |
| Phase 2.4a | Complete |
| Phase 2.4b | Next phase |
| Web client | Later phase |

## Phase 2.4b

Phase 2.4b extends the playable scenario through the public production API.
Its scope is to:

- complete the production investigation-clue path;
- complete the path after disposal escape;
- implement the self-fulfilling-truth path;
- implement rapid decisions in the core conflict;
- provide at least one successful ending;
- provide a deadline-failure ending; and
- prove the complete route with a deterministic public-API playtest.

Phase 2.4b does not implement a web frontend.

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
