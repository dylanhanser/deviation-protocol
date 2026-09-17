import { nativeRunEntryRequestSchema, objectiveNames, type NativeRunEntryRequest, type NativeRunEntryResponse,
  type PublicEntryWorld, type PublicRunProfile, type PublicNativeRunContext, type PlayerSessionView } from "./api/schemas";
import { ApiClientError } from "./api/errors";

export const objectiveLabels = {resource_pressure:"资源压力", social_trust:"社会信任", consequence_severity:"后果强度", information_opacity:"信息不透明度", conflict_intensity:"冲突强度"};
export const proposedPresentation: NativeRunEntryRequest["presentation"] = {world_tone:"balanced", reality_boundary:"lawful", relationship_overlay:"off"};
export interface FrozenNativeEntry {
  readonly url: string;
  readonly key: string;
  readonly serializedBody: string;
  readonly profile: PublicRunProfile;
  readonly world: PublicEntryWorld;
}
export function validateSetup(request: NativeRunEntryRequest, profile: PublicRunProfile, world: PublicEntryWorld): NativeRunEntryRequest {
  const parsed = nativeRunEntryRequestSchema.parse(request);
  if (JSON.stringify(parsed.profile_ref) !== JSON.stringify(profile.profile_ref) || JSON.stringify(parsed.entry_world) !== JSON.stringify(world.entry_world) ||
      !world.eligible_profiles.some((p) => p.profile_id === profile.profile_ref.profile_id && p.profile_version === profile.profile_ref.profile_version) ||
      parsed.overrides.some((o) => {const r = profile.override_rules.find((r) => r.parameter === o.parameter); return !r || o.value < r.minimum || o.value > r.maximum;})) {
    throw new Error("Invalid explicit Run choices");
  }
  return parsed;
}
export function assertNativeResponse(attempt: FrozenNativeEntry, response: NativeRunEntryResponse): void {
  const request = nativeRunEntryRequestSchema.parse(JSON.parse(attempt.serializedBody));
  const context = response.run_context;
  const values = {...attempt.profile.defaults};
  for (const override of request.overrides) values[override.parameter] = override.value;
  if (response.scenario_id !== attempt.world.scenario_id || response.scenario_content_version !== attempt.world.scenario_content_version ||
      context.player_character.player_character_id.value !== request.player_character_id || context.player_character.record_revision.value !== request.expected_record_revision ||
      JSON.stringify(context.profile_ref) !== JSON.stringify(request.profile_ref) || JSON.stringify(context.entry_world) !== JSON.stringify(request.entry_world) ||
      JSON.stringify(context.presentation) !== JSON.stringify(request.presentation) || objectiveNames.some((n) => context.objectives[n] !== values[n])) {
    throw new ApiClientError("Native response does not bind the request", {kind:"invalid-response", status:200, reason:"CONTRACT_MISMATCH"});
  }
}
export function assertNativeView(view: PlayerSessionView, expected: PublicNativeRunContext | undefined): void {
  if (expected !== undefined && JSON.stringify(view.run_context) !== JSON.stringify(expected)) {
    throw new ApiClientError("Native View context changed", {kind:"invalid-response", status:200, reason:"CONTRACT_MISMATCH"});
  }
}
export function nativeFailureIsUncertain(tainted: boolean, error: unknown): boolean {
  if (tainted || !(error instanceof ApiClientError) || error.kind !== "api") return true;
  const known: Record<string, [number,string]> = {
    PLAYER_CHARACTER_NOT_FOUND:[404,"Player character was not found"], IDEMPOTENCY_CONFLICT:[409,"Idempotency key was reused"],
    PLAYER_CHARACTER_STALE:[409,"Player character revision is stale"], PLAYER_CHARACTER_NOT_ELIGIBLE:[409,"Player character is not eligible for Run entry"],
    RUN_ENTRY_CONFLICT:[409,"Run entry conflicts with current state"], REQUEST_VALIDATION_FAILED:[422,"Request validation failed"],
    INVALID_RUN_PROTOCOL:[422,"Run settings are not available"], INVALID_ENTRY_WORLD:[422,"Entry world is not available"],
    INVALID_SCENARIO_DEFINITION:[422,"Scenario definition is not available"], NATIVE_RUN_ENTRY_NOT_AVAILABLE:[503,"Native Run entry is not available"],
  };
  const pair = known[error.errorCode ?? ""];
  return !pair || pair[0] !== error.status || pair[1] !== error.message;
}
