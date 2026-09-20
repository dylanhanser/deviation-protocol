import {expect,it} from "vitest";
import {completionJourneyFixture} from "./test/fixtures";
import {nativeRunJourneySchema,nativeRunCompletionStatusSchema,nativeRunStatusSchema} from "./api/schemas";
import {assertCompletionHistory,assertCompletionAuthorities,freezeRunCompletion,assertCompletionSubmission,assertCompletionReconciliation,assertConfirmedCompletion} from "./runCompletion";

it("freezes the complete consent identity and rejects changed submission authorities",()=>{
  const f=completionJourneyFixture();assertCompletionAuthorities(f.view,f);
  const attempt=freezeRunCompletion(f.view,f,"once");
  expect(attempt.serializedBody).toBe('{"expected_run_state_version":5,"expected_session_state_version":2}');
  expect(Object.isFrozen(attempt.authority.completion.current.visit)).toBe(true);
  const other=structuredClone(f);other.view.metadata.state_version++;
  expect(()=>assertCompletionSubmission(attempt,other.view,other)).toThrow();
  expect(attempt.source.metadata.state_version).toBe(2);
});

it.each(["terminal","path","content","context","same-revision"])("rejects independently schema-valid completion mismatch %s",mode=>{
  const f=completionJourneyFixture();
  if(mode==="terminal")Object.assign(f.completion,{run_state_version:6,lifecycle_status:"terminated",can_complete:false,reason:"run_terminal",offer:null});
  if(mode==="path"){f.completion.session_id="other";f.completion.path={...f.completion.path,session_id:"other"};f.completion.current={...f.completion.current,session_id:"other"};}
  if(mode==="content"){f.completion.path={...f.completion.path,session_state_version:3};f.completion.current={...f.completion.current,session_state_version:3};}
  if(mode==="context"){f.completion.run_context=structuredClone(f.completion.run_context);f.completion.run_context.run_id="other.run";f.completion.run_id="other.run";}
  if(mode==="same-revision")Object.assign(f.status,{lifecycle_status:"terminated",can_exit:false});
  nativeRunCompletionStatusSchema.parse(f.completion);nativeRunStatusSchema.parse(f.status);nativeRunJourneySchema.parse(f.journey);
  expect(()=>assertCompletionAuthorities(f.view,f)).toThrow();
});

it("retained POST rejects a matching pair of contradictory completed GET records",()=>{
  const f=completionJourneyFixture(),attempt=freezeRunCompletion(f.view,f,"once");
  const completion={completion_id:"a".repeat(64),outcome:"unresolved_record_preserved" as const,title:"待核事项保留，核验旅程已结案" as const,
    notice:"本次旅程已正常完成。发运暂缓继续有效，送达仍未得到证明；旧记录与资源保持原状。" as const,
    canon_outcome:{dispatch:"held" as const,delivery:"unproven" as const,record:"sealed" as const,verification:"closed_unresolved" as const}};
  const result={schema_version:"native-run-completion-result/v1" as const,source_session_id:"third",source_session_state_version:2,run_id:f.journey.run_id,
    resulting_run_state_version:6 as const,lifecycle_status:"completed" as const,run_context:f.journey.run_context,visit:f.journey.current.visit!,completion};
  const authority={journey:nativeRunJourneySchema.parse({...f.journey,schema_version:"native-run-journey/v2",lifecycle_status:"completed",run_state_version:6,completion}),
    status:nativeRunStatusSchema.parse({...f.status,schema_version:"native-run-status/v2",lifecycle_status:"completed",run_state_version:6,can_exit:false}),
    completion:nativeRunCompletionStatusSchema.parse({...f.completion,lifecycle_status:"completed",run_state_version:6,can_complete:false,reason:"run_terminal",offer:null,completion})};
  assertConfirmedCompletion({attempt,result},f.view,authority);
  assertCompletionReconciliation(attempt,f.view,authority);
  assertCompletionHistory({attempt,result},authority.journey);
  authority.completion.completion={...completion,completion_id:"b".repeat(64)};
  if(authority.journey.schema_version==="native-run-journey/v2")authority.journey.completion=authority.completion.completion;
  assertCompletionAuthorities(f.view,authority);
  expect(()=>assertConfirmedCompletion({attempt,result},f.view,authority)).toThrow();
  expect(()=>assertCompletionHistory({attempt,result},authority.journey)).toThrow();
});

it.each(["source","visit","context","terminated"])("uncertain reconciliation retains frozen expectations for coherent received %s",mode=>{
  const f=completionJourneyFixture(),attempt=freezeRunCompletion(f.view,f,"frozen");
  assertCompletionReconciliation(attempt,f.view,f);
  const other=structuredClone(f);
  if(mode==="source") {
    other.view.metadata.session_id="replacement";other.view.player_state.session_id="replacement";
    other.journey.session_id="replacement";other.status.session_id="replacement";other.completion.session_id="replacement";
    for(const value of [other.journey.path,other.journey.current,other.completion.path,other.completion.current])value.session_id="replacement";
  }
  if(mode==="visit")for(const value of [other.journey.path,other.journey.current,other.completion.path,other.completion.current])value.visit!.visit_id="replacement.visit";
  if(mode==="context") {
    other.view.run_context!.run_id="replacement.run";other.journey.run_id="replacement.run";
    other.status.run_id="replacement.run";other.completion.run_id="replacement.run";
    other.journey.run_context.run_id="replacement.run";other.completion.run_context.run_id="replacement.run";
  }
  if(mode==="terminated") {
    Object.assign(other.journey,{run_state_version:6,lifecycle_status:"terminated"});
    Object.assign(other.status,{run_state_version:6,lifecycle_status:"terminated",can_exit:false});
    Object.assign(other.completion,{run_state_version:6,lifecycle_status:"terminated",can_complete:false,reason:"run_terminal",offer:null});
  }
  nativeRunJourneySchema.parse(other.journey);nativeRunStatusSchema.parse(other.status);nativeRunCompletionStatusSchema.parse(other.completion);
  assertCompletionAuthorities(other.view,other);
  expect(()=>assertCompletionReconciliation(attempt,other.view,other)).toThrow();
  expect(attempt.sessionId).toBe("third");expect(attempt.key).toBe("frozen");
});
