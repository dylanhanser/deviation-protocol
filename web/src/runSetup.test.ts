import { describe, expect, it } from "vitest";
import { PublicApiClient } from "./api/client";
import { ApiClientError } from "./api/errors";
import { nativeRunEntryRequestSchema, publicNativeRunContextSchema, runEntryOptionsSchema } from "./api/schemas";
import { assertNativeResponse, nativeFailureIsUncertain } from "./runSetup";
import { nativeEntryFixture, runOptionsFixture } from "./test/fixtures";

export function frozenAttempt() {
  const response = nativeEntryFixture();
  return new PublicApiClient({baseUrl:"http://native.test/"}).freezeNativeEntry({
    player_character_id:response.run_context.player_character.player_character_id.value, expected_record_revision:1,
    profile_ref:response.run_context.profile_ref,entry_world:response.run_context.entry_world,overrides:[],presentation:response.run_context.presentation,
  },"native.fixed",runOptionsFixture.profiles[2]!,runOptionsFixture.entry_worlds[0]!);
}
describe("native setup contract", () => {
  it("retains exact URL, key and serialized body and checks authoritative values", () => {
    const frozen = frozenAttempt();
    expect(Object.isFrozen(frozen.profile.defaults)).toBe(true);
    expect(frozen.url).toBe("http://native.test/v1/runs/native");
    expect(() => assertNativeResponse(frozen,nativeEntryFixture())).not.toThrow();
    const crossed = nativeEntryFixture(); crossed.run_context.objectives.social_trust = 75;
    expect(() => assertNativeResponse(frozen,crossed)).toThrow();
  });
  it.each([true,1.5,9007199254740992,null,"1"])("rejects invalid version %s", (version) => {
    const request = JSON.parse(frozenAttempt().serializedBody); request.expected_record_revision=version;
    expect(nativeRunEntryRequestSchema.safeParse(request).success).toBe(false);
  });
  it.each([30,35,65,70])("validates pressure boundary %s without changing the number", (value) => {
    const context = nativeEntryFixture().run_context; context.objectives.resource_pressure=value;
    context.resource_pressure_label=value<=30?"Generous":value<=65?"Fluid":"Scarce";
    expect(publicNativeRunContextSchema.parse(context).objectives.resource_pressure).toBe(value);
    context.resource_pressure_label=value<=30?"Scarce":"Generous";
    expect(publicNativeRunContextSchema.safeParse(context).success).toBe(false);
  });
  it.each([31,34,66,69])("rejects off-lattice value %s", (value) => {
    const context = nativeEntryFixture().run_context; context.objectives.resource_pressure=value;
    expect(publicNativeRunContextSchema.safeParse(context).success).toBe(false);
  });
  it("rejects duplicate catalogue rules and crossed eligibility", () => {
    const catalog = structuredClone(runOptionsFixture);
    expect(runEntryOptionsSchema.safeParse(catalog).error).toBeUndefined();
    catalog.profiles[0]!.override_rules[1]=catalog.profiles[0]!.override_rules[0]!;
    expect(runEntryOptionsSchema.safeParse(catalog).success).toBe(false);
  });
  it.each([[404,"PLAYER_CHARACTER_NOT_FOUND","Player character was not found"], [409,"IDEMPOTENCY_CONFLICT","Idempotency key was reused"],
    [422,"INVALID_RUN_PROTOCOL","Run settings are not available"],[503,"NATIVE_RUN_ENTRY_NOT_AVAILABLE","Native Run entry is not available"]] as const)("retains taint after %s",(status,errorCode,message) => {
    const error = new ApiClientError(message,{kind:"api",status,errorCode});
    expect(nativeFailureIsUncertain(false,error)).toBe(false);
    expect(nativeFailureIsUncertain(true,error)).toBe(true);
  });
});
