# Deviation Protocol

Deviation Protocol is a data-driven AI narrative-game engine and public Web
client. The engine owns objective mechanics, trusted scenario state, facts,
resources, clocks, endings, memory, and permanent canon. Narrative Providers
receive bounded player-safe context and return untrusted candidates; they do not
write authoritative state.

Detailed phase status is owned by [PLANS.md](PLANS.md).

## Implemented now

The current implementation includes:

- deterministic domain rules, independent action policies, authoritative
  scenario orchestration, idempotent requests, atomic state/event/memory
  persistence, and MySQL 8 support through SQLAlchemy `AsyncSession` and
  `asyncmy`;
- a supplier-neutral application `NarrativeProvider` interface and normal
  composition with the configured DeepSeek infrastructure adapter;
- strict model-input/output boundaries, server-owned outcome authorization,
  fixed-fact protection, and accepted-text persistence;
- public scenario discovery, Session creation, authoritative Session Views,
  request-status polling, and server-derived `DECISION`, `FREE_ACTIONS`, and
  `ENDED` affordances;
- the React/Vite public action loop and bounded same-tab recovery without action
  replay;
- bounded deterministic player memory; and
- the complete public `death_certificate` vertical slice with success and
  deadline-failure endings; and
- the current Phase 3.2b local Demo Web layer, including deterministic-Demo
  dotenv isolation, explicit local/temporary/non-production presentation, the
  canonical 19-action Web regression, one-command launcher, and bounded smoke.

### Phase 3.2a deterministic Demo backend

Phase 3.2a is **implemented, verified, committed, and closed** at
`f1fd5e2cd07d342e852430e9352f64b84014c88e`.

It provides a separate Demo composition root with:

- a generic deterministic Demo `NarrativeProvider`;
- process-local transactional storage implementing the existing ports;
- deterministic Session/event/job/lease/worker IDs, Session seeds, and logical
  UTC time;
- the same public HTTP contract and authoritative action affordances as normal
  composition;
- exact two-process replay evidence for the canonical complete path; and
- tests proving the core Demo path needs no MySQL, Provider credential, or
  non-loopback service.

Demo state lasts only for the backend process. The Demo Provider is isolated
from normal DeepSeek composition and is not a production Provider, commercial
router, billing system, or fallback.

`death_certificate_v1` is the canonical current Demo and vertical-slice
scenario. It is not a permanent decision that this must be the first world in
the production game. The Phase 3.3 design limits entry selection to a small
authored eligible set, freezes the selected world for the run, and assigns
later deterministic selection to the engine; exact catalogues and algorithms
remain Deferred.

The historical specification and implementation evidence are in
[Phase 3.2 Deterministic Demo Environment](docs/phase_3_2_deterministic_demo_environment.md).

### Phase 3.2b local Demo Web

Phase 3.2b is implemented, verified, accepted, and closed. Automated
verification and the bounded smoke passed; controlled manual acceptance passed
the canonical 19-action browser walkthrough to version 19 and `ENDED`,
same-tab recovery after backend restart, Ctrl+C launcher shutdown, and final
owned-process and port cleanup. Phase 3.2 is complete.

With existing Python and Web dependencies, start the long-running local Demo:

```powershell
pwsh -NoProfile -File .\scripts\start-demo.ps1
```

The launcher starts the dedicated Demo backend at `127.0.0.1:8000` and Vite at
`127.0.0.1:5173`. It installs nothing and opens no browser. The page labels this
mode as a deterministic, local-only Demo with temporary data and explicitly
states that it is not a production Provider. State survives a same-tab reload
only while that backend process remains alive; restarting it intentionally
loses the process-local state and the client safely invalidates the missing
Session without replaying an action.

Run the finite startup/proxy/schema/sentinel/build smoke separately:

```powershell
pwsh -NoProfile -File .\scripts\smoke-demo.ps1
```

The smoke remains loopback-only, writes its Vite build to an owned temporary
directory rather than `web/dist`, directly reuses the production public
scenario Zod schema, executes the existing jsdom/React test stack to require the
exact rendered Demo warning under the Web child's effective Demo-mode value,
and cleans only resources it created. It does not treat the warning literal in
`App.tsx` source bytes as rendering evidence.

This acceptance applies to the deterministic local Demo vertical slice. It does
not establish production readiness or implement later final-product systems.

## Planned or accepted design — not implemented

- **Phase 3.3 — Run Protocol and Difficulty/World Profiles:** approved product
  design, not implemented. See
  [Run Protocol, Difficulty, and World Profiles](docs/run_protocol.md).
- **Phase 3.4 — NPC Relationship and Temporary Residence:** approved product
  design, not implemented. See
  [NPC Relationship and Temporary Residence](docs/npc_relationship_residence.md).
- **Phase 4.0 — Production Provider Distribution:** accepted architectural
  direction, not implemented. See
  [ADR 0001: Production Provider Distribution](docs/decisions/0001-production-provider-distribution.md).

The three later systems do not belong to Phase 3.2b. No current code implements
a frozen `RUN_PROTOCOL`, difficulty/world profiles, NPC residence mode,
player-selectable multi-Provider routing, commercial quotas, billing, or
unrestricted daily AI chat.

## Current public action and authority boundary

Clients act only through the latest authoritative `action_affordances`:

- `DECISION` submits one displayed `CHOOSE` choice with the bound
  `decision_id`;
- `FREE_ACTIONS` exposes only the action types, input kinds, limits, and visible
  targets authorized for the current View; and
- `ENDED` exposes no action controls.

`NarrativeFrame.suggested_actions` is presentation, not an executable
capability. A refreshed View replaces all earlier affordances. Player text and
model prose cannot grant resources, invent betrayal or death, change
relationship stages, rewrite facts, or create permanent canon.

See [Public Client Contract](docs/public_client_contract.md),
[NarrativeProvider boundary](docs/narrative_provider.md), and
[Architecture](docs/architecture.md).

## Repository layout

```text
src/deviation_protocol/
  domain/            # pure domain state, rules, facts, and events
  application/       # orchestration, ports, policies, and public projections
  infrastructure/    # MySQL, Provider, and deterministic Demo adapters
  api/               # FastAPI composition roots and public routes
web/                 # React/Vite/TypeScript public client
config/              # action policies and versioned content
alembic/              # MySQL migrations
tests/                # unit, integration, end-to-end, and opt-in live tests
docs/                 # architecture, contracts, roadmap detail, and designs
```

Dependencies point toward the domain:
`api/infrastructure -> application -> domain`.

## Windows development

Use PowerShell 7+ and the repository virtual environment. Do not use system
Python:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m compileall -q src tests alembic
```

For explicitly offline work, use the sanitized verifier:

```powershell
.\scripts\verify.ps1 -Mode Offline
```

Do not create or replace `.venv` silently. Do not commit `.env`. Live DeepSeek
tests remain disabled unless the user explicitly opts in.

The normal application uses MySQL and does not fall back to SQLite:

```powershell
$env:DATABASE_URL = "mysql+asyncmy://game_user:secret@127.0.0.1:3306/deviation_protocol?charset=utf8mb4"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn deviation_protocol.api.main:app --app-dir src --reload
```

The current fixed `demo-dev-only` principal is suitable only for local
development and tests, not Internet deployment.

## Documentation

- [Roadmap and phase status](PLANS.md)
- [Implemented architecture](docs/architecture.md)
- [Engineering guardrails](docs/engineering/guardrails.md)
- [Codex workflow](docs/engineering/codex_workflow.md)
- [Narrative Provider boundary](docs/narrative_provider.md)
- [Phase 3.2 specification and evidence](docs/phase_3_2_deterministic_demo_environment.md)
- [Run Protocol design](docs/run_protocol.md)
- [NPC relationship and residence design](docs/npc_relationship_residence.md)
- [Production Provider distribution ADR](docs/decisions/0001-production-provider-distribution.md)
