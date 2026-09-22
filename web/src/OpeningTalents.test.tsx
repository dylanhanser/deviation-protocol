import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe,it,expect,vi } from "vitest";
import { OpeningTalentChoices, ConfirmedOpeningTalents } from "./OpeningTalents";
import { openingPreparedFixture, openingConfirmedFixture } from "./test/openingFixtures";
import { nativeEntryFixture, runOptionsFixture } from "./test/fixtures";
import { PublicApiClient } from "./api/client";
import { openingPreparationSchema } from "./api/schemas";

describe("opening talent selection",() => {
  it("requires exactly two, permits deselection, and makes confirmation explicit",() => {
    const confirm=vi.fn();
    render(<OpeningTalentChoices record={openingPreparedFixture()} disabled={false} onConfirm={confirm}/>);
    const boxes=screen.getAllByRole("checkbox");
    const button=screen.getByRole("button",{name:"确认天赋并开始"});
    expect(button).toBeDisabled();
    fireEvent.click(boxes[0]!);expect(button).toBeDisabled();
    fireEvent.click(boxes[1]!);expect(button).toBeEnabled();expect(boxes[2]).toBeDisabled();
    expect(confirm).not.toHaveBeenCalled();
    fireEvent.click(boxes[0]!);expect(button).toBeDisabled();expect(boxes[2]).toBeEnabled();
    fireEvent.click(boxes[2]!);fireEvent.click(button);
    expect(confirm).toHaveBeenCalledExactlyOnceWith(["T006","T026"]);
    expect(screen.getByText("卓越")).toBeVisible();expect(screen.getByText("取舍")).toBeVisible();
  });
  it("confirmed choices are immutable and markup stays text",() => {
    const record=openingPreparedFixture();
    record.state="CONFIRMED";record.selected_ids=["T001","T006"];
    record.candidates[0]!.description="<script>untrusted()</script>";
    render(<OpeningTalentChoices record={record} disabled={false} onConfirm={vi.fn()}/>);
    expect(screen.getAllByRole("checkbox").every(c => c.matches(":disabled"))).toBe(true);
    expect(screen.getByText("<script>untrusted()</script>")).toBeVisible();
    expect(document.querySelector("script")).toBeNull();
  });
  it.each(["future","duplicate","tier","selection","character"])("rejects an invalid server offer: %s",kind => {
    const record=structuredClone(openingPreparedFixture());
    if(kind==="future") (record.candidates[0] as {id:string}).id="T002";
    if(kind==="duplicate") record.candidates[1]=record.candidates[0]!;
    if(kind==="tier") record.candidates[0]!.tier="WEAK";
    if(kind==="selection") record.selected_ids=["T001"];
    if(kind==="character") record.character_id="another.character";
    expect(openingPreparationSchema.safeParse(record).success).toBe(false);
  });
  it("isolates late historical/other Session talent responses",async () => {
    const client=new PublicApiClient({baseUrl:"http://test/"});
    let resolve!: (value:ReturnType<typeof openingPreparedFixture>["candidates"])=>void;
    const late=new Promise<ReturnType<typeof openingPreparedFixture>["candidates"]>(r => {resolve=r;});
    vi.spyOn(client,"getOpeningTalents").mockReturnValueOnce(late).mockResolvedValueOnce([]);
    const rendered=render(<ConfirmedOpeningTalents client={client} sessionId="old"/>);
    rendered.rerender(<ConfirmedOpeningTalents client={client} sessionId="new"/>);
    await screen.findByText("本次旅程没有开局天赋。");
    resolve(openingPreparedFixture().candidates.slice(0,2));
    await waitFor(() => expect(screen.queryByText(/临机决断/)).not.toBeInTheDocument());
  });
  it.each(["matching","preparation","cards","choices","admission","result"])("validates confirmation against the issued offer: %s",async kind => {
    const opening=openingPreparedFixture();
    const reply=openingConfirmedFixture(nativeEntryFixture());
    if (kind==="preparation") reply.preparation_id="b".repeat(32);
    if (kind==="cards") reply.candidates[0]!.description="Changed server copy";
    if (kind==="choices") reply.selected_ids=["T001","T026"];
    if (kind==="admission") reply.admission.presentation.world_tone="grim";
    if (kind==="result") reply.result!.run_context.player_character.player_character_id.value="other.character";
    const fetchImplementation=vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(reply),{status:200,headers:{"Content-Type":"application/json"}}));
    const client=new PublicApiClient({baseUrl:"http://test/",fetchImplementation});
    const frozen=client.freezeNativeEntry(opening.admission,"confirm.test",runOptionsFixture.profiles[2]!,runOptionsFixture.entry_worlds[0]!);
    const result=client.confirmOpening(frozen,opening,["T001","T006"]);
    if (kind==="matching") await expect(result).resolves.toEqual(nativeEntryFixture());
    else await expect(result).rejects.toMatchObject({kind:"invalid-response",reason:"CONTRACT_MISMATCH"});
    expect(fetchImplementation).toHaveBeenCalledTimes(1);
  });
});
