import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ThreadComposer } from "@/components/thread/ThreadComposer";

describe("ThreadComposer text input", () => {
  it("sends trimmed text with Enter", () => {
    const onSend = vi.fn();
    render(<ThreadComposer onSend={onSend} />);

    const textarea = screen.getByLabelText(/message input/i);
    fireEvent.change(textarea, { target: { value: "  hello EasyGS  " } });
    fireEvent.keyDown(textarea, { key: "Enter" });

    expect(onSend).toHaveBeenCalledWith("hello EasyGS");
    expect(textarea).toHaveValue("");
  });

  it("keeps Shift+Enter as multiline input", () => {
    const onSend = vi.fn();
    render(<ThreadComposer onSend={onSend} />);

    const textarea = screen.getByLabelText(/message input/i);
    fireEvent.change(textarea, { target: { value: "line one" } });
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });

    expect(onSend).not.toHaveBeenCalled();
  });

  it("does not expose media upload controls", () => {
    const onSend = vi.fn();
    const { container } = render(<ThreadComposer onSend={onSend} />);

    expect(container.querySelector('input[type="file"]')).toBeNull();
    expect(screen.queryByLabelText(/attach image/i)).toBeNull();
  });
});
