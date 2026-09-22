import { z } from "zod";
import type { PublicApiClient } from "./api/client";
import type { OpeningPreparation } from "./api/schemas";
import { getSessionStorage, storageFailure, type SessionRecoveryStorageResult } from "./sessionRecovery";

const referenceSchema = z.strictObject({version:z.literal(1),
  character_id:z.string().min(1).max(128).regex(/^[A-Za-z0-9][A-Za-z0-9_.:-]*$/),
  preparation_id:z.string().regex(/^[0-9a-f]{32}$/)});
export type OpeningRecoveryReference = z.infer<typeof referenceSchema>;

// Same tab-local storage as Session recovery, additionally partitioned by API endpoint.
// No credentials, selections, admission payload or server result is stored here.
export function openingRecoveryKey(client:PublicApiClient):string {
  return `deviation-protocol.web-opening-recovery:${client.recoveryScope}`;
}

export function readOpeningRecovery(client:PublicApiClient):SessionRecoveryStorageResult<OpeningRecoveryReference|null> {
  const storage=getSessionStorage();
  if (!storage.ok) return storage;
  let raw:string|null;
  try {raw=storage.value.getItem(openingRecoveryKey(client));}
  catch (cause) {return storageFailure("get",cause);}
  if (raw===null) return {ok:true,value:null};
  try {return {ok:true,value:referenceSchema.parse(JSON.parse(raw))};}
  catch (cause) {return storageFailure("get",cause);}
}

export function writeOpeningRecovery(client:PublicApiClient, record:OpeningPreparation):SessionRecoveryStorageResult<OpeningRecoveryReference> {
  const reference=referenceSchema.parse({version:1,character_id:record.character_id,preparation_id:record.preparation_id});
  const prior=readOpeningRecovery(client);
  if (!prior.ok) return prior;
  if (prior.value && JSON.stringify(prior.value)!==JSON.stringify(reference)) return storageFailure("set",new Error("Unresolved opening reference"));
  const storage=getSessionStorage();
  if (!storage.ok) return storage;
  try {
    storage.value.setItem(openingRecoveryKey(client),JSON.stringify(reference));
    if (storage.value.getItem(openingRecoveryKey(client))!==JSON.stringify(reference)) throw new Error("Opening reference was not retained");
    return {ok:true,value:reference};
  } catch (cause) {return storageFailure("set",cause);}
}

export function clearOpeningRecovery(client:PublicApiClient):SessionRecoveryStorageResult<void> {
  const storage=getSessionStorage();
  if (!storage.ok) return storage;
  try {if (storage.value.getItem(openingRecoveryKey(client))===null) return {ok:true,value:undefined};}
  catch (cause) {return storageFailure("get",cause);}
  try {storage.value.removeItem(openingRecoveryKey(client));return {ok:true,value:undefined};}
  catch (cause) {return storageFailure("remove",cause);}
}

export function assertOpeningReference(reference:OpeningRecoveryReference, record:OpeningPreparation|null):asserts record is OpeningPreparation {
  if (!record || record.character_id!==reference.character_id || record.preparation_id!==reference.preparation_id)
    throw new Error("Opening recovery association changed");
}
