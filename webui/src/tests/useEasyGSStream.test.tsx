import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { useEasyGSStream } from "@/hooks/useEasyGSStream";
import type { InboundEvent } from "@/lib/types";
import { ClientProvider } from "@/providers/ClientProvider";

function fakeClient() {
  const handlers = new Map<string, Set<(ev: InboundEvent) => void>>();
  return {
    client: {
      status: "open" as const,
      defaultChatId: null as string | null,
      onStatus: () => () => {},
      onError: () => () => {},
      onChat(chatId: string, h: (ev: InboundEvent) => void) {
        let set = handlers.get(chatId);
        if (!set) {
          set = new Set();
          handlers.set(chatId, set);
        }
        set.add(h);
        return () => set!.delete(h);
      },
      sendMessage: vi.fn(),
      newChat: vi.fn(),
      attach: vi.fn(),
      connect: vi.fn(),
      close: vi.fn(),
      updateUrl: vi.fn(),
    },
    emit(chatId: string, ev: InboundEvent) {
      const set = handlers.get(chatId);
      set?.forEach((h) => h(ev));
    },
  };
}

function wrap(client: ReturnType<typeof fakeClient>["client"]) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <ClientProvider
        client={client as unknown as import("@/lib/easygs-client").EasyGSClient}
        token="tok"
      >
        {children}
      </ClientProvider>
    );
  };
}

describe("useEasyGSStream", () => {
  it("collapses consecutive tool_hint frames into one trace row", () => {
    const fake = fakeClient();
    const { result } = renderHook(() => useEasyGSStream("chat-t", []), {
      wrapper: wrap(fake.client),
    });

    act(() => {
      fake.emit("chat-t", {
        event: "message",
        chat_id: "chat-t",
        text: 'weather("get")',
        kind: "tool_hint",
      });
      fake.emit("chat-t", {
        event: "message",
        chat_id: "chat-t",
        text: 'search "hk weather"',
        kind: "tool_hint",
      });
    });

    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].kind).toBe("trace");
    expect(result.current.messages[0].role).toBe("tool");
    expect(result.current.messages[0].traces).toEqual([
      'weather("get")',
      'search "hk weather"',
    ]);

    act(() => {
      fake.emit("chat-t", {
        event: "message",
        chat_id: "chat-t",
        text: "## Summary",
      });
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[1].role).toBe("assistant");
    expect(result.current.messages[1].kind).toBeUndefined();
  });

  it("keeps progress frames separate from tool traces", () => {
    const fake = fakeClient();
    const { result } = renderHook(() => useEasyGSStream("chat-p", []), {
      wrapper: wrap(fake.client),
    });

    act(() => {
      fake.emit("chat-p", {
        event: "message",
        chat_id: "chat-p",
        text: "Queued for later processing.",
        kind: "progress",
      });
    });

    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0]).toMatchObject({
      role: "assistant",
      kind: "progress",
      content: "Queued for later processing.",
    });
  });

  it("keeps assistant buttons on complete messages", () => {
    const fake = fakeClient();
    const { result } = renderHook(() => useEasyGSStream("chat-q", []), {
      wrapper: wrap(fake.client),
    });

    act(() => {
      fake.emit("chat-q", {
        event: "message",
        chat_id: "chat-q",
        text: "How should I continue?\n\n1. Short answer\n2. Detailed answer",
        button_prompt: "How should I continue?",
        buttons: [["Short answer", "Detailed answer"]],
      });
    });

    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].content).toBe("How should I continue?");
    expect(result.current.messages[0].buttons).toEqual([
      ["Short answer", "Detailed answer"],
    ]);
  });

  it("keeps background source metadata on assistant messages", () => {
    const fake = fakeClient();
    const { result } = renderHook(() => useEasyGSStream("chat-s", []), {
      wrapper: wrap(fake.client),
    });

    act(() => {
      fake.emit("chat-s", {
        event: "message",
        chat_id: "chat-s",
        text: "Workflow finished.",
        source: {
          kind: "workflow",
          id: "wf_12345678",
          name: "vcf_qc_pca",
          status: "succeeded",
        },
      });
    });

    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].source).toEqual({
      kind: "workflow",
      id: "wf_12345678",
      name: "vcf_qc_pca",
      status: "succeeded",
    });
  });

  it("keeps the processing indicator until the turn completes", () => {
    const fake = fakeClient();
    const { result } = renderHook(() => useEasyGSStream("chat-w", []), {
      wrapper: wrap(fake.client),
    });

    act(() => {
      result.current.send("Run an analysis");
    });

    expect(result.current.isAwaitingResponse).toBe(true);

    act(() => {
      fake.emit("chat-w", {
        event: "message",
        chat_id: "chat-w",
        text: "I will start by checking the inputs.",
      });
    });

    expect(result.current.isAwaitingResponse).toBe(true);

    act(() => {
      fake.emit("chat-w", {
        event: "message",
        chat_id: "chat-w",
        text: "Done.",
        turn_complete: true,
      });
    });

    expect(result.current.isAwaitingResponse).toBe(false);
  });
});
