import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

export const server = setupServer(http.get("*/v1/run-entry-options", () => HttpResponse.json({
  schema_version:"run-entry-options/v1", native_entry_available:false, profiles:[], entry_worlds:[],
  presentation_options:{world_tone:["grim","balanced","heroic"],reality_boundary:["lawful","deviant","chaotic"],relationship_overlay:["off","veiled","charged"]},
})));
