import { act, renderHook, waitFor } from "@testing-library/react";
import { expect,it,vi } from "vitest";
import { PublicApiClient } from "./api/client";
import { useOpeningPreparation } from "./useOpeningPreparation";
import { openingPreparedFixture } from "./test/openingFixtures";

it("restores the identical pending offer after remount using GET only",async () => {
  const client=new PublicApiClient({baseUrl:"http://test/"});
  const record=openingPreparedFixture();
  const get=vi.spyOn(client,"getOpeningPreparation").mockResolvedValue(record);
  const post=vi.spyOn(client,"prepareOpening");
  const first=renderHook(() => useOpeningPreparation(client,record.character_id,true));
  await waitFor(() => expect(first.result.current.record).toEqual(record));
  first.unmount();
  const second=renderHook(() => useOpeningPreparation(client,record.character_id,true));
  await waitFor(() => expect(second.result.current.record).toEqual(record));
  expect(get).toHaveBeenCalledTimes(2);expect(post).not.toHaveBeenCalled();
});

it("a late old-client offer cannot replace the current character's offer",async () => {
  const oldClient=new PublicApiClient({baseUrl:"http://old/"});
  const newClient=new PublicApiClient({baseUrl:"http://new/"});
  const record=openingPreparedFixture();
  let resolve!:(value:typeof record)=>void;
  const pending=new Promise<typeof record>(r => {resolve=r;});
  vi.spyOn(oldClient,"getOpeningPreparation").mockReturnValue(pending);
  vi.spyOn(newClient,"getOpeningPreparation").mockResolvedValue(null);
  const hook=renderHook(({client}) => useOpeningPreparation(client,record.character_id,true),{initialProps:{client:oldClient}});
  hook.rerender({client:newClient});
  await waitFor(() => expect(hook.result.current.loading).toBe(false));
  await act(async () => {resolve(record);await pending;});
  expect(hook.result.current.record).toBeNull();
});

it("a failed read retains a visible error and an explicit GET retry",async () => {
  const client=new PublicApiClient({baseUrl:"http://test/"});
  const record=openingPreparedFixture();
  const get=vi.spyOn(client,"getOpeningPreparation").mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce(record);
  const hook=renderHook(() => useOpeningPreparation(client,record.character_id,true));
  await waitFor(() => expect(hook.result.current.error).toBeTruthy());
  expect(get).toHaveBeenCalledTimes(1);
  act(() => hook.result.current.retry());
  await waitFor(() => expect(hook.result.current.record).toEqual(record));
  expect(hook.result.current.error).toBeNull();
});
