# Receipt archive v1 — 核验档案室

This S7-3 implementation candidate follows the independently approved published
plan and P01–P09. It is a third visit to world.undelivered_receipt version 1,
region.undelivered_receipt.verification_archive version 1, with scenario
receipt_archive and content version receipt-archive-1.0.0. It is not an initial
entry option or a restart of the dispatch hall.

The raw LF/UTF-8 pack is independently pinned to SHA-256
`fa0af413ee0db565d9fa2cc3d46971518fccef123790a21fb9f16155be4edc39`.
Missing content or a same-version byte substitution fails before use. Existing
death-certificate and undelivered-receipt packs and pins remain unchanged.

Actual public play must end the first world, continue to the dispatch hall,
OBSERVE, TALK and choose 会签暂缓. Only the current second visit's genuine
receipt_held / RESOLVED ending unlocks the archive. Active, released or expired
dispatch visits cannot enter. The engine determines destination and eligibility;
the player confirms whether to continue. Cancellation before POST consumes nothing.

The archive starts from the latest validated ended dispatch state. The complete
PlayerState carries over, including zero composure. Old dispatch consequences,
ended clock and NPC state remain authoritative in their old region. Archive
entry grants no refill, item, fee, reward, character revision or clock.

Public arrival states: “会签暂缓仍然有效，送达仍未得到证明。你进入核验档案室，决定如何保留这项待核记录；原有资源不会恢复。”
OBSERVE 查看待核记录 opens the authored decision. Sealing ends RESOLVED at
receipt_archive.ending.unresolved_sealed; deferring ends FAILED at
receipt_archive.ending.review_deferred. Priorities 10 and 20 make sealing win
the separately labelled synthetic simultaneous-condition control, including
reversed definition order. Neither ending establishes delivery or alters canon.

There are no local NPCs or clocks. Ordinary custom actions retain the declared
no-effect behavior, and existing S5 action policies alone determine resource
effects. Both endings permit explicit Run exit 5→6, followed by separately
confirmed fresh admission with the same eligible character and a first action.
The regional pool remains exhausted; no fourth visit is implemented.

Verification separates genuine public zero-resource journeys from resource-only
zero fixtures where pressure is zero. The latter modify only resources before
immutable world-root creation and never inject an ending, unlock or receipt.
See [R01–R10 evidence and limits](../run_protocol.md#s7-3-implementation-candidate-evidence).
