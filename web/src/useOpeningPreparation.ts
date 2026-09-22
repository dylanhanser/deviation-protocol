import { useEffect, useRef, useState } from "react";
import type { PublicApiClient } from "./api/client";
import type { OpeningPreparation } from "./api/schemas";
import type { FrozenNativeEntry } from "./runSetup";

export function useOpeningPreparation(client:PublicApiClient, characterId:string, enabled:boolean) {
  const [refresh,setRefresh] = useState(0);
  const [state,setState] = useState<{client:PublicApiClient;characterId:string;record:OpeningPreparation|null;error:string|null;loading:boolean}|null>(null);
  const generation=useRef(0);
  const scope=useRef({client,characterId,enabled});
  useEffect(() => {
    scope.current={client,characterId,enabled};
    const version=++generation.current;
    const controller=new AbortController();
    if (enabled && characterId) {
      client.getOpeningPreparation(characterId,controller.signal).then(record => {
        if (!controller.signal.aborted && version === generation.current) setState({client,characterId,record,error:null,loading:false});
      }).catch(() => {
        if (!controller.signal.aborted && version === generation.current) setState({client,characterId,record:null,error:"未能读取开局准备，请重试。",loading:false});
      });
    }
    return () => {controller.abort(); generation.current = version + 1;};
  },[client,characterId,enabled,refresh]);
  const current=state?.client === client && state.characterId === characterId ? state : null;
  async function prepare(attempt:FrozenNativeEntry, signal:AbortSignal) {
    const version=++generation.current;
    const record=await client.prepareOpening(attempt,signal);
    if (signal.aborted || version !== generation.current || scope.current.client !== client || scope.current.characterId !== characterId) return;
    setState({client,characterId,record,error:null,loading:false});
  }
  return {record:current?.record ?? null,error:current?.error ?? null,loading:enabled && !!characterId && current === null,
    prepare,retry:() => setRefresh(value => value+1)};
}

