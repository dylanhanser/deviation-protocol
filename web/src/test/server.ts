import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { openingPreparedFixture } from "./openingFixtures";
import { nativeRunEntryRequestSchema } from "../api/schemas";

export const server = setupServer(
  http.get("*/v1/player-characters/:character/opening-preparation", () => HttpResponse.json(null)),
  http.get("*/v1/sessions/:session/opening-talents", () => HttpResponse.json([])),
  http.post("*/v1/opening-preparations", async ({request}) => HttpResponse.json(openingPreparedFixture(nativeRunEntryRequestSchema.parse(await request.json())))),
  http.get("*/v1/run-entry-options", () => HttpResponse.json({
  schema_version:"run-entry-options/v1", native_entry_available:false, profiles:[], entry_worlds:[],
  presentation_options:{world_tone:["grim","balanced","heroic"],reality_boundary:["lawful","deviant","chaotic"],relationship_overlay:["off","veiled","charged"]},
})));
