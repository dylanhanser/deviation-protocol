import { expect, it } from "vitest";
import { assertConfirmedCurrent, assertConfirmedDestination, assertJourney, assertJourneyRunStatus, freezeJourneyTransition } from "./runJourney";
import { ARCHIVE_NOTICE, nativeRunStatusSchema, nativeRunJourneySchema, nativeRunRevisitResultSchema, playerSessionViewSchema, type NativeJourneyAssociation } from "./api/schemas";
import { endedViewFixture, nativeViewFixture } from "./test/fixtures";

const source = nativeViewFixture(endedViewFixture());
source.metadata.session_id = "second";
source.metadata.content_version = "undelivered-receipt-1.0.0";
source.narrative_frame.scenario_id = "undelivered_receipt";
Object.assign(source.player_state,{session_id:source.metadata.session_id,content_version:source.metadata.content_version});
function association(ordinal: 1 | 2 | 3): NativeJourneyAssociation {
  return {session_id:["first","second","third"][ordinal-1]!, session_state_version:7,
    scenario_id:["death_certificate","undelivered_receipt","receipt_archive"][ordinal-1]!,
    scenario_content_version:["death-certificate-1.1.0","undelivered-receipt-1.0.0","receipt-archive-1.0.0"][ordinal-1]!,
    visit:{visit_id:`visit.${ordinal}`,visit_ordinal:ordinal,world_id:ordinal===1 ? "world.death_certificate" : "world.undelivered_receipt",
      world_version:1,region_id:["region.death_certificate.facility","region.undelivered_receipt.dispatch_hall","region.undelivered_receipt.verification_archive"][ordinal-1]!,region_version:1}};
}
const before=nativeRunJourneySchema.parse({schema_version:"native-run-journey/v1",session_id:"second",run_id:source.run_context!.run_id,
  run_context:source.run_context,run_state_version:4,lifecycle_status:"active",path:association(2),current:association(2),
  predecessor:association(1),successor:null,next_transition:{kind:"regional_revisit",world_title:"未送达的回执",region_title:"核验档案室",notice:ARCHIVE_NOTICE},
  arrival:{previous_ending_status:"RESOLVED",previous_ending_title:"规程已中断",entry_notice:"上一世界已形成明确结果。你带着原有状态抵达发运大厅，当前队列从零开始计时。"}});
const result=nativeRunRevisitResultSchema.parse({schema_version:"native-run-revisit-result/v1",source_session_id:"second",source_session_state_version:7,
  run_id:source.run_context!.run_id,resulting_run_state_version:5,session_id:"third",initial_session_state_version:0,
  scenario_id:"receipt_archive",scenario_content_version:"receipt-archive-1.0.0",run_context:source.run_context,visit:association(3).visit});
const destination={...structuredClone(source),metadata:{...source.metadata,session_id:"third",content_version:result.scenario_content_version},
  player_state:{...source.player_state,session_id:"third",content_version:result.scenario_content_version},
  narrative_frame:{...source.narrative_frame,scenario_id:result.scenario_id}};
const after=nativeRunJourneySchema.parse({...before,session_id:"third",run_state_version:6,lifecycle_status:"terminated",path:association(3),current:association(3),
  predecessor:association(2),next_transition:null,arrival:{previous_ending_status:"RESOLVED",previous_ending_title:"回执待核，发运暂缓",entry_notice:ARCHIVE_NOTICE}});

it("freezes the entire confirmed regional authority without retaining mutable aliases",()=>{
  const mutable=structuredClone(before), frozen=freezeJourneyTransition(source,mutable,"regional.once");
  mutable.path.visit!.visit_id="changed";
  expect(frozen.authority.path.visit!.visit_id).toBe("visit.2");
  expect(Object.isFrozen(frozen.authority.path.visit)).toBe(true);
  expect(frozen.url).toBe("v1/sessions/second/run-revisit");
  expect(JSON.parse(frozen.serializedBody)).toEqual({expected_run_state_version:4,expected_session_state_version:7});
});

it.each(["session", "visit", "source", "run", "context"])("rejects schema-valid recovered %s before target adoption",(field)=>{
  const recovered=structuredClone({...before,run_state_version:5 as const,current:association(3),successor:association(3),next_transition:null});
  if(field==="session") {recovered.current.session_id="other.third";recovered.successor!.session_id="other.third";}
  if(field==="visit") {recovered.current.visit!.visit_id="other.visit";recovered.successor!.visit!.visit_id="other.visit";}
  if(field==="source") recovered.path.visit!.visit_id="other.source";
  if(field==="run") {recovered.run_id="other.run";recovered.run_context.run_id="other.run";}
  if(field==="context") recovered.run_context.presentation.world_tone="grim";
  expect(nativeRunJourneySchema.safeParse(recovered).success).toBe(true);
  expect(()=>assertConfirmedCurrent({source,sourceAssociation:before.path,result},recovered)).toThrow();
});

it("rejects internally valid destination content contradictions and accepts advanced matching reads",()=>{
  const confirmed={source,sourceAssociation:before.path,result};
  expect(playerSessionViewSchema.safeParse(destination).success).toBe(true);
  expect(()=>assertConfirmedDestination(confirmed,destination,after)).not.toThrow();
  const changed=playerSessionViewSchema.parse(destination);
  changed.metadata.content_version="other-content-1.0.0";
  changed.player_state.content_version=changed.metadata.content_version;
  expect(playerSessionViewSchema.safeParse(changed).success).toBe(true);
  expect(()=>assertConfirmedDestination(confirmed,changed,after)).toThrow();
});

it.each([1,2,3] as const)("distinguishes active/ended current and historical Views in native family %s",(ordinal)=>{
  for(const terminated of [false,true]) for(const ended of [false,true]) {
    const view=nativeViewFixture(ended ? endedViewFixture() : undefined);
    const current=association(ordinal);
    current.session_state_version=view.metadata.state_version;
    if(ordinal===1)current.visit=null;
    Object.assign(view.metadata,{session_id:current.session_id,content_version:current.scenario_content_version});
    Object.assign(view.player_state,{session_id:current.session_id,content_version:current.scenario_content_version});
    view.narrative_frame.scenario_id=current.scenario_id;
    const journey={...before,session_id:current.session_id,path:current,current,
      run_state_version:ordinal+2+(terminated?1:0),lifecycle_status:terminated?"terminated":"active",
      predecessor:ordinal===1?null:association((ordinal-1) as 1|2),successor:null,next_transition:null,
      arrival:ordinal===1?null:ordinal===2?before.arrival:after.arrival};
    expect(playerSessionViewSchema.safeParse(view).success).toBe(true);
    const parsed=nativeRunJourneySchema.parse(journey);
    if(terminated && !ended)expect(()=>assertJourney(view,parsed)).toThrow();
    else {
      expect(()=>assertJourney(view,parsed)).not.toThrow();
      const status=nativeRunStatusSchema.parse({schema_version:"native-run-status/v1",session_id:current.session_id,
        run_id:parsed.run_id,session_state_version:current.session_state_version,run_state_version:parsed.run_state_version,
        lifecycle_status:parsed.lifecycle_status,can_exit:ended&&!terminated});
      expect(()=>assertJourneyRunStatus(view,parsed,status)).not.toThrow();
    }
  }
  if(ordinal>1) {
    const historical=structuredClone(source);
    const path=association(1);
    Object.assign(historical.metadata,{session_id:path.session_id,content_version:path.scenario_content_version});
    Object.assign(historical.player_state,{session_id:path.session_id,content_version:path.scenario_content_version});
    historical.narrative_frame.scenario_id=path.scenario_id;
    const journey=nativeRunJourneySchema.parse({...before,session_id:path.session_id,path,current:association(ordinal),
      run_state_version:ordinal+2,predecessor:null,successor:association(2),next_transition:null,arrival:null});
    expect(playerSessionViewSchema.safeParse(historical).success).toBe(true);
    expect(()=>assertJourney(historical,journey)).not.toThrow();
    const active=nativeViewFixture();
    Object.assign(active.metadata,{session_id:path.session_id,state_version:path.session_state_version,content_version:path.scenario_content_version});
    Object.assign(active.player_state,{session_id:path.session_id,state_version:path.session_state_version,content_version:path.scenario_content_version});
    expect(playerSessionViewSchema.safeParse(active).success).toBe(true);
    expect(()=>assertJourney(active,journey)).toThrow();
  }
});

it("requires an ended source for an otherwise schema-valid transition offer",()=>{
  const active=nativeViewFixture();
  Object.assign(active.metadata,source.metadata,{phase:active.metadata.phase});
  Object.assign(active.player_state,{session_id:active.metadata.session_id,state_version:active.metadata.state_version,content_version:active.metadata.content_version});
  active.narrative_frame.scenario_id=source.narrative_frame.scenario_id;
  expect(playerSessionViewSchema.safeParse(active).success).toBe(true);
  expect(()=>assertJourney(active,before)).toThrow();
});
it("accepts progressed authority and rejects every contradictory confirmed visit field",()=>{
  const confirmed={source,sourceAssociation:before.path,result};
  expect(()=>assertConfirmedDestination(confirmed,destination,after)).not.toThrow();
  for(const key of Object.keys(result.visit) as (keyof typeof result.visit)[]) {
    const changed=structuredClone(after);
    Object.assign(changed.path.visit!,{[key]:typeof result.visit[key]==="number" ? 99 : "contradictory.identity"});
    changed.current=structuredClone(changed.path);
    if(key==="visit_id")expect(nativeRunJourneySchema.safeParse(changed).success).toBe(true);
    expect(()=>assertConfirmedDestination(confirmed,destination,changed)).toThrow();
  }
  for(const key of ["session_id","session_state_version"] as const) {
    const changed=structuredClone(after);
    Object.assign(changed.predecessor!,{[key]:key==="session_id" ? "different.second" : 99});
    expect(nativeRunJourneySchema.safeParse(changed).success).toBe(true);
    expect(()=>assertConfirmedDestination(confirmed,destination,changed)).toThrow();
  }
});
