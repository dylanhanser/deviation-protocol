# Deferred findings

This is the canonical register for confirmed non-blocking findings accepted
under the [workflow disposition policy](codex_workflow.md#findings-and-milestone-disposition).
Keep one concise entry per finding; link evidence instead of copying audit
transcripts. Never fabricate findings or record speculative improvements here.

Use stable IDs `DF-001`, `DF-002`, and so on; never recycle them. Each entry uses:

- **ID / status:** deferred, reassessment required, escalated blocker, or closed.
- **Affected feature/path:** exact affected surface.
- **Evidence:** confirmed reproduction or evidence reference.
- **User impact / exposure:** consequences and reachable/operational conditions.
- **Non-blocking rationale:** why the current named milestone can proceed.
- **Containment/workaround:** required measure, or explicitly not needed.
- **Repair/reassessment:** milestone and responsible role.
- **Closure evidence:** fix and verification reference when closed.

Reassess when reachability or impact expands or containment is lost, and at the
post-playable stabilization checkpoint before wider release. Retain closed IDs
and evidence; escalate blockers under the workflow policy.

## Current entries

None recorded by this amendment. The already-fixed S3 planning findings are
historical closures documented in [run_protocol.md](../run_protocol.md#published-p33-s3-plan--implementation-not-started),
not open debt. This statement does not claim the repository has no defects.
