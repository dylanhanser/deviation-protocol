import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import App from "./App";
import { SessionReading } from "./SessionReading";
import { PublicApiClient } from "./api/client";
import { writeSessionRecoveryRecord } from "./sessionRecovery";
import { activeViewFixture, endedViewFixture, scenarioCatalogFixture, eligiblePlayerCharactersFixture, runOptionsFixture } from "./test/fixtures";

describe("reading an authoritative public view", () => {
  it("keeps paragraph boundaries and literal markup without rendering links or HTML", () => {
    const view = structuredClone(activeViewFixture);
    view.recent_narrative_texts = ["第一段。\r\n\r\n第二段。\n下一行。\n\n<img src=x onerror=alert(1)> [打开](https://example.test)"];
    const { container } = render(<SessionReading view={view} staleKind={null} />);
    const prose = screen.getByRole("region", { name: "当前公开正文" });
    expect(prose.querySelectorAll("p")).toHaveLength(3);
    expect(prose.textContent).toContain("第二段。\n下一行。");
    expect(prose.textContent).toContain("<img src=x onerror=alert(1)>");
    expect(container.querySelector("img, a, script")).toBeNull();
  });

  it("shows the latest accepted segment once and preserves chronological earlier segments", () => {
    const view = structuredClone(activeViewFixture);
    view.recent_narrative_texts = ["最早的脚步。", "走过庭院。", "门后传来回声。"];
    render(<SessionReading view={view} staleKind={null} />);
    expect(screen.getAllByText("门后传来回声。")).toHaveLength(1);
    const toggle = screen.getByText("回看此前正文（2 段）");
    expect(toggle.closest("details")).not.toHaveAttribute("open");
    expect(screen.getByText("最早的脚步。")).not.toBeVisible();
    fireEvent.click(toggle);
    expect(screen.getByText("最早的脚步。")).toBeVisible();
    const history = screen.getByRole("region", { name: "近期已接受正文" });
    expect(within(history).getAllByRole("listitem").map((li) => li.textContent)).toEqual(["最早的脚步。", "走过庭院。"]);
    expect(history.textContent).not.toContain("门后传来回声。");
  });

  it("retains equal text at distinct chronological positions rather than deduplicating events", () => {
    const view = structuredClone(activeViewFixture);
    view.recent_narrative_texts = ["钟响了。", "钟响了。", "脚步停下。"];
    render(<SessionReading view={view} staleKind={null} />);
    fireEvent.click(screen.getByText("回看此前正文（2 段）"));
    expect(screen.getAllByText("钟响了。")).toHaveLength(2);
  });

  it("distinguishes lagging memory from a truncated projection without inventing facts", () => {
    const view = structuredClone(activeViewFixture);
    view.player_memory = { ...view.player_memory, complete: false, sync_status: "REBUILD_REQUIRED", truncated: true, total_known_public_facts: 130 };
    const original = structuredClone(view);
    const { rerender } = render(<SessionReading view={view} staleKind={null} />);
    fireEvent.click(screen.getByText("角色与记忆"));
    expect(screen.getByText("记忆索引尚未同步完整；未显示的记录不代表没有发生。")).toBeVisible();
    expect(screen.getByText("当前只展示部分索引，以下分别为已展示数量和索引总数。")).toBeVisible();
    expect(screen.getByText("0 / 130")).toBeVisible();
    expect(view).toEqual(original);
    const synced = structuredClone(view);
    synced.player_memory = { ...view.player_memory, complete: true, sync_status: "CURRENT" };
    rerender(<SessionReading view={synced} staleKind={null} />);
    expect(screen.getByText("索引已同步")).toBeVisible();
    expect(screen.getByText(/当前只展示部分索引/)).toBeVisible();
    expect(screen.queryByText(/尚未同步完整/)).not.toBeInTheDocument();
  });

  it.each(["RESOLVED", "FAILED"] as const)("labels %s history as read-only and leaves resource and ending semantics intact", (ending) => {
    const view = endedViewFixture(ending);
    render(<SessionReading view={view} staleKind={null} readingIdentity="historical" />);
    expect(screen.getByText("历史访问（只读），不是当前进度。")).toBeVisible();
    expect(screen.queryByText("权威 View：当前")).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "历史资源与时钟" })).toHaveTextContent("8 / 10");
    expect(screen.getByRole("heading", { name: view.presentation.ending!.title })).toBeVisible();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByText("正常完成")).not.toBeInTheDocument();
  });

  it("keeps stale status prominent and does not fabricate prose when no accepted text exists", () => {
    const view = structuredClone(activeViewFixture);
    view.recent_narrative_texts = [];
    render(<SessionReading view={view} staleKind="transport-uncertain" />);
    expect(screen.getByText("权威 View：可能 stale（transport-uncertain）")).toBeVisible();
    expect(screen.getByText("当前尚无已接受的叙事正文。")).toBeVisible();
    expect(screen.queryByText("权威 View：当前")).not.toBeInTheDocument();
  });

  it("uses neutral resource wording for unconfirmed native identity while preserving the stale warning", () => {
    render(<SessionReading view={activeViewFixture} staleKind="transport-uncertain" readingIdentity="unconfirmed" />);
    expect(screen.getByText("访问关联尚未确认；此 View 不代表已确认的当前进度。")).toBeVisible();
    expect(screen.getByText("权威 View：可能 stale（transport-uncertain）")).toBeVisible();
    expect(screen.getByRole("region",{name:"所显示访问的资源与时钟"})).toHaveTextContent("8 / 10");
    expect(screen.queryByText("权威 View：当前")).not.toBeInTheDocument();
    expect(screen.queryByText("眼下的状况")).not.toBeInTheDocument();
    expect(screen.queryByText(/当前资源以上方显示为准/)).not.toBeInTheDocument();
  });

  it("places reading and existing choices before setup; disclosures perform no requests or storage writes", async () => {
    const client = new PublicApiClient({ baseUrl: "http://ui-api.test/" });
    writeSessionRecoveryRecord(activeViewFixture.metadata.session_id);
    vi.spyOn(client, "listScenarios").mockResolvedValue(scenarioCatalogFixture);
    vi.spyOn(client, "listEligiblePlayerCharacters").mockResolvedValue(eligiblePlayerCharactersFixture);
    vi.spyOn(client, "listRunEntryOptions").mockResolvedValue(runOptionsFixture);
    const read = vi.spyOn(client, "getSessionView").mockResolvedValue(structuredClone(activeViewFixture));
    const action = vi.spyOn(client, "submitAction");
    const entry = vi.spyOn(client, "enterNativeRun");
    render(<App client={client} />);
    await waitFor(() => expect(screen.getByText("权威 View：当前")).toBeVisible());
    const story = screen.getByRole("article");
    const choices = screen.getByRole("region", { name: "当前可执行行动" });
    const setup = screen.getByRole("region", { name: "进入方式" });
    expect(story.compareDocumentPosition(choices) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(choices.compareDocumentPosition(setup) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    const fetch = vi.spyOn(globalThis, "fetch");
    const save = vi.spyOn(Storage.prototype, "setItem");
    const remove = vi.spyOn(Storage.prototype, "removeItem");
    const readsBefore = read.mock.calls.length;
    for (const label of ["角色与记忆", "场景提示与技术信息"]) {
      fireEvent.click(screen.getByText(label));
      fireEvent.click(screen.getByText(label));
    }
    expect(fetch).not.toHaveBeenCalled();
    expect(save).not.toHaveBeenCalled();
    expect(remove).not.toHaveBeenCalled();
    expect(read).toHaveBeenCalledTimes(readsBefore);
    expect(action).not.toHaveBeenCalled();
    expect(entry).not.toHaveBeenCalled();
  });
});
