# 《未送达的回执》 — continuation content v1

This authored destination implements the published P3.3-S7-2 plan. It is available
only after explicit continuation from an eligible ending of 《死亡证明已签发》.
It is absent from initial scenario/Run entry options. No third destination or
revisit is enabled.

The independent review returned four P2 findings; the bounded correction is delivered and
focused re-review is next. The exact incoming pack bytes remain unchanged. Its
trusted catalogue pins SHA-256
`74af55faf2eca0dd826be1f025272d070c23a2000383183e886ec823f495582c`.
The pack-specific `.gitattributes` override preserves its frozen UTF-8/CRLF bytes
without normalizing content; missing or same-version substituted bytes reject.

| Identity | Value |
| --- | --- |
| Pack | `config/scenarios/undelivered_receipt_v1.json` |
| Scenario / content | `undelivered_receipt` / `undelivered-receipt-1.0.0` |
| World | `world.undelivered_receipt`, version 1 |
| Region | `region.undelivered_receipt.dispatch_hall`, version 1 |
| Character definition | `character.death_certificate.investigator` |
| Deadline | `dispatch_deadline`, maximum 40 |

The source `protocol_broken` and `record_challenged` endings start the deadline
at 0. Source `deadline_reached` starts it at 4. The entire remaining PlayerState
is carried unchanged, including zero composure. There is no refill, reward,
inventory grant, character revision, death or replacement of the permanent line.
The destination starts with new local runtime, NPCs, clocks and memory. The old
Session, events, snapshots and replay evidence remain authoritative history.

The public path is OBSERVE at the receipt desk, TALK to the dispatch clerk, then
CHOOSE whether to hold or release dispatch. Initial public facts distinguish a
missing receipt from a schedule marked complete; a hold prevents dispatch but
does not prove delivery. Existing five-policy mechanics determine costs. Repeated
ineffective actions can exhaust the deadline. The content adds no anomaly route.

| Priority | Ending ID | Result |
| --- | --- | --- |
| 10 | `undelivered_receipt.ending.deadline_reached` | FAILED |
| 20 | `undelivered_receipt.ending.receipt_held` | RESOLVED |
| 30 | `undelivered_receipt.ending.dispatch_closed` | FAILED |

The Director resolves deadline before hold before release, independently of
definition order. The priority tests at 39/40 are detached synthetic boundaries;
separate public-play cases prove reachable endings, all profiles, permitted
objective extremes and zero-composure play.

After the destination ending, explicit Run exit moves revision 4 to terminated
revision 5 and frees the character for separately confirmed fresh admission.
This is not normal Run completion. History and exact earlier receipts remain
readable after exit and after a subsequent Run begins.

Content routing uses separate preloaded bundles and exact Session scenario/content
identities. The original pack and v1 Run prompt are unchanged. A bounded private
visit annotation conveys only the authored world/region and prior ending notice;
the corrected continuation GET separately projects the actual previous ending
class/title and fixed variant notice for display at arrival/action/reload. This
bounded public projection was absent from the incoming candidate. Neither
projection exposes roots, snapshots, seeds or hidden facts through the public API.

See [the approved plan](../phase_3_3_s7_2_same_line_world_continuation_plan.md),
[implementation evidence](../run_protocol.md#s7-2-evidence-map)
and [public contract](../public_client_contract.md). The unstaged implementation candidate has automated integrated-play evidence
and awaits focused independent re-review; no browser acceptance or release readiness is claimed.
