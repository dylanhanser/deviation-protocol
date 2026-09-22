# Opening talents — implementation candidate

The owner approved the revised 100-entry talent document, the 12-entry CURRENT
pool, and one narrow persistence migration on 2026-09-21. This implementation
is an unstaged candidate, not independently approved, published, or browser
accepted. It does not reopen D1, D2/D3, Phase 3.3 or DF-001/DF-002.

## Authored content and authority

`src/deviation_protocol/domain/opening_talents_v1.json` preserves all 100 IDs,
names, descriptions and effect/dependency text from the approved document.
The immutable version is `opening-talents/v1`; its independently pinned UTF-8
SHA-256 is `1600d3fbaafd4b6e6a47270716556f4b491e8c44f3aef4dddb26ee4cbba4078d`.
Composition validates the bytes, exact IDs T001–T100, unique names, tier counts
5/20/35/40, and status counts 12 CURRENT / 88 FUTURE. Future entries are content
only: they cannot be drawn, selected, or executed as silent no-ops. Models and
player prose confer no talent authority.

## Preparation, recovery and admission

The existing native Web launcher first freezes character, difficulty, overrides,
presentation and entry world, then explicitly requests a preparation. The
server generates a private 256-bit seed and ranks CURRENT IDs by SHA-256 of
`opening-talents:hash-rank/v1`, catalog version, seed and ID (NUL-separated),
breaking ties by ID. The first five distinct eligible entries are issued,
skipping additional top-tier entries. No tier probability claims are made.
Catalog version, seed, actual ordered candidate IDs and frozen admission intent
are durably saved before returning a response. Reads never generate candidates.

`opening_preparations` is the only new table. It binds each preparation to the
authenticated controller, player and character, a character-local ordinal,
initial request key, lifecycle, canonical frozen content, and optional confirmed
Run/result. Unique constraints cover owner/request, character/ordinal, pending
character and confirmed Run. Owned character locks and the existing native
admission connection lock serialize issuance and confirmation. Repositories
never commit. Demo uses the same service/catalog/policy and its existing
process-local atomic store; it does not claim restart durability.

There is no cancellation or reroll operation. Leaving the launcher does not
discard preparation. A new request for a character with pending preparation
returns the existing candidates **and existing settings**, even if the submitted
settings differ. This deliberately forbids parameter changes after issuance;
the UI explains this before preparation. Validation failures leave it intact.
If character revision/eligibility later changes, confirmation rejects rather
than silently rewriting frozen intent. A new preparation becomes available
only after the preceding confirmed Run is terminal and the character is again
eligible. Retrying the original preparation request still returns its original
record. The owner can choose another character, which has separate preparation.

Confirmation validates current ownership, character eligibility/revision, the
preparation identity/state/version, and exactly two distinct issued CURRENT IDs.
The two IDs are normalized into ID order and immutable thereafter. Selection,
existing Run revisions 1–3, Session initialization, protocol/world binding,
receipt and preparation finalization commit in one UoW. Failure rolls them all
back. Concurrent confirmation creates at most one Run. A successful exact retry
revalidates the existing native receipt and returns the original result; a
different choice conflicts. There is no automatic confirmation or admission.

Before each Web confirmation POST, a versioned character/preparation locator is
saved and read back through the existing tab-local sessionStorage boundary,
partitioned by normalized API base URL. Storage failure prevents that POST.
No credentials, choices, admission payload or claimed result are stored in the
locator. On refresh it is read independently of selected/eligible characters;
the authenticated preparation GET must match both IDs. A pending result shows
the original offer for explicit selection; a confirmed result offers a read-only
journey recovery. That action checks the preparation again, its frozen admission
against the public entry definitions, the exact Run/character/Session View and
Journey associations before saving the Session recovery target. It never
replays confirmation or admission POST. Existing Session recovery takes priority;
client/operation invalidation and a final storage check isolate late reads.
Unresolved, missing, foreign or unavailable references remain retained and locked
for explicit GET retry; network failure alone never discards them. Successful
Session persistence safely supersedes the locator. This does not claim recovery
after the user deletes tab storage or closes the tab.

New talent-bearing Run IDs use the reserved server-issued `opening.` prefix.
Every turn loads confirmed talents by that Run ID, including later visits;
a missing record for such a Run is an integrity error, never legacy fallback.
The version/IDs remain readable through owned Session history without changing
current recovery identity. Existing Runs, standalone Sessions and the retained
older direct-admission API have explicit no-talent behavior: no random backfill,
snapshot rewrite or frozen-content modification. The Web primary native path
uses preparation and explicit selection.
Both `/v1/runs` and `/v1/runs/native` reject fresh admission while an opening
preparation is pending. They share the same check under the owned-character lock
and transaction used by issuance/confirmation, after historical receipt replay
and before admission writes. Legacy admission without a pending offer remains
talent-free; a later preparation cannot invalidate an earlier exact receipt.
Fresh client admissions cannot claim the reserved `opening.` operation-key
namespace; historical exact receipts still replay before that restriction.

## Mechanical boundary

Only additional action clock cost changes. The independent
`OpeningTalentClockPolicy` sums the selected modifiers and applies
`base + max(0, original additional cost + sum of modifiers)`, still capped by
the existing clock maximum. Mandatory base progression cannot be removed.
Auto-continue beats and other action types receive no talent modifier.

| ID | Current additional-clock modifier |
| --- | --- |
| T001 | EXPLORE −1; CUSTOM −1 |
| T006 | TALK −1; EXPLORE +1 |
| T007 | OBSERVE −1; TALK +1 |
| T008 | CUSTOM −1; OBSERVE +1 |
| T026 | TALK −1 |
| T027 | OBSERVE −1 |
| T028 | EXPLORE −1 |
| T029 | CUSTOM −1 |
| T061 | TALK +1 |
| T062 | OBSERVE +1 |
| T063 | EXPLORE +1 |
| T064 | CUSTOM +1 |

No talent changes success, trust, probability, resource policy, facts, rewards,
or ending-selection authority. Existing time-based consequences can naturally
occur earlier/later when clock costs change. Confirmed binding and resulting
clock deltas are private task/event evidence, revalidated before Provider work
and finalization. Existing event/snapshot/response/job transactions and exact
action replay prevent duplicate application. Old job evidence retains its old
field shape and zero talent behavior.

## Migration and verification boundary

Migration `20260921_0012` extends the actual head `20260920_0011`. It creates only
the preparation table and its keys/constraints, without rewriting old rows.
Upgrade and downgrade hold the existing native-admission advisory lock.
Downgrade refuses whenever **any** preparation exists, including unconfirmed
offers, before dropping anything; operator inspection is required to preserve
data. Do not downgrade a database containing player preparations.

Focused tests cover catalog/active-pool invariants, recovery, concurrent issuance
and confirmation, invalid choices, atomic rollback, immutable replay, effects,
legacy compatibility and Web controls. Dedicated MySQL checks record initial
schema/data, compare ORM metadata at actual head, exercise refusal with a pending
record, and restore the initial empty test schema exactly. Automated rendering
does not establish browser acceptance. Later browser acceptance should check
five cards and tier text at desktop/390 px, keyboard two-choice selection,
refresh recovery, fixed parameters, guarded confirmation, immutable display,
and one submitted action/retry with authoritative clock progression.

The original independent review returned `CHANGES_REQUIRED` for lost-confirmation
refresh recovery and the legacy pending-offer bypass. The narrow correction
candidate addresses those findings and awaits focused independent re-review;
the original failures and applicable unchanged-content conclusions remain history.
