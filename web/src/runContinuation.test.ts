import { expect, it } from "vitest";
import { assertContinuationStatus, assertConfirmedSuccessor, freezeRunContinuation } from "./runContinuation";
import { nativeRunContinuationStatusSchema, nativeRunContinuationResultSchema, type NativeRunContinuationStatus } from "./api/schemas";
import { endedViewFixture, nativeEntryFixture } from "./test/fixtures";

const ended=endedViewFixture("FAILED");
const view = {...ended,metadata:{...ended.metadata,content_version:"death-certificate-1.1.0"},
  narrative_frame:{...ended.narrative_frame,scenario_id:"death_certificate"},run_context:nativeEntryFixture().run_context};
const status: NativeRunContinuationStatus = {schema_version:"native-run-continuation-status/v1",
  session_id:view.metadata.session_id,run_id:view.run_context.run_id,run_state_version:3,
  session_state_version:view.metadata.state_version,lifecycle_status:"active",can_continue:true,
  current_session_id:view.metadata.session_id,visit:null,predecessor:null,successor:null,arrival:null};
const visit = {visit_id:"visit.two",visit_ordinal:2,world_id:"world.undelivered_receipt",world_version:1,
  region_id:"region.undelivered_receipt.dispatch_hall",region_version:1};
const predecessor = {session_id:"previous",session_state_version:8,scenario_id:"death_certificate",
  scenario_content_version:"death-certificate-1.1.0",visit:{...visit,visit_id:"visit.one",visit_ordinal:1,
    world_id:"world.death_certificate",region_id:"region.death_certificate.facility"}};

it("freezes matched explicit continuation intent and rejects changed authority",()=>{
  const request=freezeRunContinuation(view,status,"continue.once");
  expect(Object.isFrozen(request)).toBe(true);
  expect(request.url).toBe(`v1/sessions/${status.session_id}/run-continuation`);
  expect(request.serializedBody).toBe(JSON.stringify({expected_run_state_version:3,expected_session_state_version:status.session_state_version}));
  expect(()=>freezeRunContinuation(view,{...status,can_continue:false},"continue.once")).toThrow();
  for(const field of ["session_id","run_id","session_state_version"] as const)
    expect(()=>assertContinuationStatus(view,{...status,[field]:field==="session_state_version"?999:"foreign"})).toThrow();
});
it("requires a nullable predecessor and the exact visit/revision family",()=>{
  const {predecessor: omitted,...missing}=status;
  expect(omitted).toBeNull();
  expect(nativeRunContinuationStatusSchema.safeParse(missing).success).toBe(false);
  expect(nativeRunContinuationStatusSchema.safeParse(status).success).toBe(true);
  expect(nativeRunContinuationStatusSchema.safeParse({...status,run_state_version:4}).success).toBe(false);
  const second={...status,can_continue:false,visit,predecessor,run_state_version:4,arrival:{previous_ending_status:"FAILED",
    previous_ending_title:"记录成为现实",entry_notice:"上一世界以失败结果结束。你带着原有状态抵达发运大厅，当前队列已经消耗四格期限。"}};
  expect(nativeRunContinuationStatusSchema.safeParse(second).success).toBe(true);
  expect(nativeRunContinuationStatusSchema.safeParse({...second,predecessor:null}).success).toBe(false);
  expect(nativeRunContinuationStatusSchema.safeParse({...second,lifecycle_status:"terminated"}).success).toBe(false);
  expect(nativeRunContinuationStatusSchema.safeParse({...second,lifecycle_status:"terminated",run_state_version:5}).success).toBe(true);
  expect(nativeRunContinuationStatusSchema.safeParse({...second,visit:{...visit,world_version:2}}).success).toBe(false);
});
it.each([null,true,"3",-1,1.5,Number.MAX_SAFE_INTEGER+1])("rejects malformed revision %s",value=>{
  expect(nativeRunContinuationStatusSchema.safeParse({...status,run_state_version:value}).success).toBe(false);
});

it("binds every confirmed immutable successor association while allowing current versions to advance",()=>{
  const result=nativeRunContinuationResultSchema.parse({schema_version:"native-run-continuation-result/v1",
    source_session_id:view.metadata.session_id,source_session_state_version:view.metadata.state_version,
    run_id:view.run_context.run_id,resulting_run_state_version:4,session_id:"destination",initial_session_state_version:0,
    scenario_id:"undelivered_receipt",scenario_content_version:"undelivered-receipt-1.0.0",run_context:view.run_context,visit});
  const destination={...view,metadata:{...view.metadata,session_id:result.session_id,content_version:result.scenario_content_version,state_version:7},
    narrative_frame:{...view.narrative_frame,scenario_id:result.scenario_id}};
  const current=nativeRunContinuationStatusSchema.parse({...status,session_id:result.session_id,current_session_id:result.session_id,
    session_state_version:7,run_state_version:5,lifecycle_status:"terminated",can_continue:false,visit,
    predecessor:{...predecessor,session_id:view.metadata.session_id,session_state_version:view.metadata.state_version},
    arrival:{previous_ending_status:"FAILED",previous_ending_title:"记录成为现实",
      entry_notice:"上一世界以失败结果结束。你带着原有状态抵达发运大厅，当前队列已经消耗四格期限。"}});
  const confirmed={source:view,result};
  expect(()=>assertConfirmedSuccessor(confirmed,destination,current)).not.toThrow();
  for(const key of Object.keys(result.visit) as (keyof typeof result.visit)[]) {
    const changed={...current,visit:{...current.visit!,[key]:typeof result.visit[key]==="number"?99:"unrelated.valid.visit"}};
    if(key==="visit_id")expect(nativeRunContinuationStatusSchema.safeParse(changed).success).toBe(true);
    expect(()=>assertConfirmedSuccessor(confirmed,destination,changed)).toThrow();
  }
  for(const key of ["session_id","session_state_version","scenario_id","scenario_content_version"] as const) {
    const changed={...current,predecessor:{...current.predecessor!,[key]:key==="session_state_version"?999:"unrelated.valid.identity"}};
    if(key==="session_id" || key==="session_state_version")expect(nativeRunContinuationStatusSchema.safeParse(changed).success).toBe(true);
    expect(()=>assertConfirmedSuccessor(confirmed,destination,changed)).toThrow();
  }
  for(const changed of [
    {...destination,metadata:{...destination.metadata,session_id:"foreign"}},
    {...destination,metadata:{...destination.metadata,content_version:"foreign.1"}},
    {...destination,narrative_frame:{...destination.narrative_frame,scenario_id:"foreign"}},
    {...destination,run_context:{...destination.run_context,run_id:"foreign.run"}},
    {...destination,run_context:{...destination.run_context,objectives:{...destination.run_context.objectives,social_trust:0}}},
  ])expect(()=>assertConfirmedSuccessor(confirmed,changed,current)).toThrow();
  expect(confirmed.result.visit.visit_id).toBe("visit.two");
});
