import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MessageBubble } from "@/components/MessageBubble";
import type { UIMessage } from "@/lib/types";

describe("MessageBubble", () => {
  it("renders user messages as right-aligned pills", () => {
    const message: UIMessage = {
      id: "u1",
      role: "user",
      content: "hello",
      createdAt: Date.now(),
    };

    const { container } = render(<MessageBubble message={message} />);
    const row = container.firstElementChild;
    const pill = screen.getByText("hello");

    expect(row).toHaveClass("ml-auto", "flex");
    expect(pill).toHaveClass("ml-auto", "w-fit", "rounded-[18px]");
  });

  it("renders trace messages as collapsible tool groups", () => {
    const message: UIMessage = {
      id: "t1",
      role: "tool",
      kind: "trace",
      content: 'search "hk weather"',
      traces: ['weather("get")', 'search "hk weather"'],
      createdAt: Date.now(),
    };

    render(<MessageBubble message={message} />);
    const toggle = screen.getByRole("button", { name: /used 2 tools/i });

    expect(screen.getByText('weather("get")')).toBeInTheDocument();
    expect(screen.getByText('search "hk weather"')).toBeInTheDocument();

    fireEvent.click(toggle);
    expect(screen.queryByText('weather("get")')).not.toBeInTheDocument();
  });

  it("renders progress messages as collapsible status groups", () => {
    const message: UIMessage = {
      id: "p1",
      role: "assistant",
      kind: "progress",
      content: "Queued for later processing.",
      createdAt: Date.now(),
    };

    render(<MessageBubble message={message} />);

    const toggle = screen.getByRole("button", { name: /information/i });
    expect(screen.getByText("Queued for later processing.")).toBeInTheDocument();
    expect(screen.queryByText(/using a tool/i)).not.toBeInTheDocument();

    fireEvent.click(toggle);
    expect(screen.queryByText("Queued for later processing.")).not.toBeInTheDocument();
  });

  it("renders background source badges", () => {
    const message: UIMessage = {
      id: "a1",
      role: "assistant",
      content: "Workflow finished.",
      source: {
        kind: "workflow",
        id: "wf_12345678",
        name: "vcf_qc_pca",
        status: "succeeded",
      },
      createdAt: Date.now(),
    };

    render(<MessageBubble message={message} />);

    expect(screen.getByText("Workflow")).toBeInTheDocument();
    expect(screen.getByText("wf_12345678")).toBeInTheDocument();
    expect(screen.getByText("succeeded")).toBeInTheDocument();
  });

});
