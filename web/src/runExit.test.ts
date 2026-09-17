import { describe, expect, it } from "vitest";
import { assertRunStatus, freezeRunExit } from "./runExit";
import { nativeRunStatusSchema, type NativeRunStatus } from "./api/schemas";
import { endedViewFixture, nativeEntryFixture } from "./test/fixtures";

const view = {...endedViewFixture("FAILED"), run_context:nativeEntryFixture().run_context};
const status: NativeRunStatus = {schema_version:"native-run-status/v1", session_id:view.metadata.session_id,
  run_id:view.run_context.run_id, session_state_version:view.metadata.state_version,
  run_state_version:3, lifecycle_status:"active", can_exit:true};

describe("Run exit intent", () => {
  it("freezes the exact request only for a matched ended native View", () => {
    const attempt = freezeRunExit(view, status, "exit.once");
    expect(Object.isFrozen(attempt)).toBe(true);
    expect(attempt.url).toBe(`v1/sessions/${view.metadata.session_id}/run-exit`);
    expect(attempt.serializedBody).toBe(JSON.stringify({expected_run_state_version:3,
      expected_session_state_version:view.metadata.state_version}));
    expect(() => freezeRunExit(view, {...status,can_exit:false}, "exit.once")).toThrow();
  });
  it.each(["session_id", "run_id", "session_state_version"] as const)("binds %s", (field) => {
    expect(() => assertRunStatus(view, {...status,[field]:field === "session_state_version" ? status.session_state_version+1 : "other"})).toThrow();
  });
  it.each([Number.MAX_SAFE_INTEGER+1, -1, 1.5, "3", null, true])("rejects unsafe version %s", (version) => {
    expect(nativeRunStatusSchema.safeParse({...status, session_state_version:version}).success).toBe(false);
  });
  it("keeps the status object closed and rejects terminal availability", () => {
    expect(nativeRunStatusSchema.safeParse({...status,secret:"x"}).success).toBe(false);
    expect(nativeRunStatusSchema.safeParse({...status,run_state_version:4,lifecycle_status:"terminated"}).success).toBe(false);
  });
});
