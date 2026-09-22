import { useEffect, useState } from "react";
import type { PublicApiClient } from "./api/client";
import type { OpeningPreparation } from "./api/schemas";
import { assertOpeningReference, readOpeningRecovery } from "./openingRecovery";

export function useOpeningRecovery(client:PublicApiClient, enabled:boolean) {
  const [retry,setRetry]=useState(0);
  const [state,setState]=useState<{client:PublicApiClient;retry:number;record:OpeningPreparation|null;error:string|null}|null>(null);
  useEffect(() => {
    if (!enabled) return;
    const controller=new AbortController();
    void (async () => {
      let record:OpeningPreparation|null=null,error:string|null=null;
      try {
        const read=readOpeningRecovery(client);
        if (!read.ok) throw new Error("Opening reference unavailable");
        if (read.value) {
          record=await client.getOpeningPreparation(read.value.character_id,controller.signal);
          assertOpeningReference(read.value,record);
        }
      } catch {record=null;error="开局恢复暂未核实，已保留恢复入口。请重读开局恢复；不会自动提交。";}
      if (!controller.signal.aborted) setState({client,retry,record,error});
    })();
    return () => controller.abort();
  },[client,enabled,retry]);
  const current=enabled && state?.client===client && state.retry===retry ? state : null;
  return {record:current?.record??null,error:current?.error??null,loading:enabled && !current,
    retry:() => setRetry(value=>value+1)};
}
