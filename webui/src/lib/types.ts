export type Role = "user" | "assistant" | "tool" | "system";

/** "trace" rows are tool-call breadcrumbs; "progress" rows are runtime
 * status notices that should not masquerade as tool activity. */
export type MessageKind = "message" | "trace" | "progress";

export interface MessageSource {
  kind: "workflow";
  id: string;
  name?: string;
  status?: string;
}

export interface UIMessage {
  id: string;
  role: Role;
  content: string;
  kind?: MessageKind;
  isStreaming?: boolean;
  createdAt: number;
  /** For trace rows: each individual hint line, so consecutive hints can
   * render as a single collapsible group. */
  traces?: string[];
  /** Optional answer choices for a pending ask_user question. */
  buttons?: string[][];
  /** Optional background workflow source metadata for WebUI badges. */
  source?: MessageSource;
}

export interface ChatSummary {
  /** Server-side session key, e.g. ``websocket:abcd-...``. */
  key: string;
  /** Local channel + chat_id parts derived from ``key`` for convenience. */
  channel: string;
  chatId: string;
  createdAt: string | null;
  updatedAt: string | null;
  preview: string;
}

export interface BootstrapResponse {
  token: string;
  ws_path: string;
  expires_in: number;
  model_name?: string | null;
}

export interface SettingsPayload {
  agent: {
    model: string;
    provider: string;
    resolved_provider: string | null;
    has_api_key: boolean;
  };
  providers: Array<{
    name: string;
    label: string;
  }>;
  runtime: {
    config_path: string;
  };
  requires_restart: boolean;
}

export interface SettingsUpdate {
  model?: string;
  provider?: string;
}

export type ConnectionStatus =
  | "idle"
  | "connecting"
  | "open"
  | "reconnecting"
  | "closed"
  | "error";

export type InboundEvent =
  | { event: "ready"; chat_id: string; client_id: string }
  | { event: "attached"; chat_id: string; request_id?: string }
  | {
      event: "message";
      chat_id: string;
      text: string;
      reply_to?: string;
      buttons?: string[][];
      /** Original prompt before the websocket text fallback appends buttons. */
      button_prompt?: string;
      /** Present when the frame is an agent breadcrumb (e.g. tool hint,
       * generic progress line) rather than a conversational reply. */
      kind?: "tool_hint" | "progress";
      /** True when this message is the final response for the active turn. */
      turn_complete?: boolean;
      /** Present when the message summarizes a background workflow. */
      source?: MessageSource;
    }
  | {
      event: "delta";
      chat_id: string;
      text: string;
      stream_id?: string;
    }
  | {
      event: "stream_end";
      chat_id: string;
      stream_id?: string;
    }
  | { event: "error"; chat_id?: string; detail?: string };

export type Outbound =
  | { type: "new_chat"; request_id?: string }
  | { type: "attach"; chat_id: string }
  | {
      type: "message";
      chat_id: string;
      content: string;
    };
