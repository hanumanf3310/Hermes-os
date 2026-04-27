import { useEffect, useState } from "react";
import { send, subscribe } from "../hooks/useIPC";

type PendingRequest = {
  id: number;
  tool_name: string;
  input: unknown;
  summary: string | null;
};

type Decision = "allow" | "allow_for_session" | "deny";

function summarizeInput(input: unknown): string {
  if (input === null || input === undefined) return "";
  if (typeof input === "string") return input;
  try {
    return JSON.stringify(input, null, 2);
  } catch {
    return String(input);
  }
}

export function ApprovalModal() {
  const [queue, setQueue] = useState<PendingRequest[]>([]);

  useEffect(() => {
    const unsub = subscribe((msg) => {
      if (msg.type === "approval_request" && typeof msg.id === "number") {
        const newId = msg.id as number;
        setQueue((prev) => {
          // Backend re-dispatches every 1 s until we respond; skip
          // if we already have this id in the queue so the modal
          // doesn't spawn duplicates after a webview reload or race.
          if (prev.some((r) => r.id === newId)) return prev;
          return [
            ...prev,
            {
              id: newId,
              tool_name: (msg.tool_name as string) ?? "?",
              input: msg.input,
              summary: (msg.summary as string | null) ?? null,
            },
          ];
        });
      }
    });
    return unsub;
  }, []);

  const current = queue[0];
  if (!current) return null;

  const respond = (decision: Decision) => {
    send({ type: "approval_response", id: current.id, decision });
    setQueue((prev) => prev.slice(1));
  };

  const preview = current.summary ?? summarizeInput(current.input);
  // MCP server spawn already persists the decision to the user-level
  // allowlist (~/.config/thclaws/mcp_allowlist.json) on Allow, so the
  // session-scoped option adds nothing. Hide it there.
  const showAllowForSession = current.tool_name !== "MCP server spawn";

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center"
      style={{ background: "var(--modal-backdrop, rgba(0,0,0,0.55))" }}
    >
      <div
        className="rounded-lg border shadow-xl w-[520px] max-w-[90vw]"
        style={{
          background: "var(--bg-primary)",
          borderColor: "var(--border)",
          color: "var(--text-primary)",
        }}
      >
        <div
          className="px-4 py-2 border-b text-sm font-semibold flex items-center gap-2"
          style={{ borderColor: "var(--border)" }}
        >
          <span style={{ color: "var(--accent)" }}>●</span>
          <span>Agent wants to run</span>
          <code className="px-1.5 py-0.5 rounded text-xs font-mono"
            style={{ background: "var(--bg-secondary)" }}>
            {current.tool_name}
          </code>
        </div>
        <pre
          className="px-4 py-3 text-xs font-mono whitespace-pre-wrap break-all max-h-[40vh] overflow-auto"
          style={{
            background: "var(--bg-secondary)",
            color: "var(--text-primary)",
          }}
        >
          {preview || "(no preview)"}
        </pre>
        <div
          className="px-4 py-3 border-t flex items-center justify-end gap-2"
          style={{ borderColor: "var(--border)" }}
        >
          <button
            onClick={() => respond("deny")}
            className="text-xs px-3 py-1.5 rounded hover:bg-white/5"
            style={{ color: "var(--text-secondary)" }}
          >
            Deny
          </button>
          {showAllowForSession && (
            <button
              onClick={() => respond("allow_for_session")}
              className="text-xs px-3 py-1.5 rounded hover:bg-white/5"
              style={{ color: "var(--text-primary)" }}
              title="Allow this and every subsequent tool call in this session"
            >
              Allow for session
            </button>
          )}
          <button
            onClick={() => respond("allow")}
            className="text-xs px-3 py-1.5 rounded"
            style={{
              background: "var(--accent)",
              color: "var(--accent-fg, #ffffff)",
            }}
            autoFocus
          >
            Allow
          </button>
        </div>
        {queue.length > 1 && (
          <div
            className="px-4 py-1.5 text-[10px] border-t"
            style={{
              borderColor: "var(--border)",
              color: "var(--text-secondary)",
              background: "var(--bg-secondary)",
            }}
          >
            +{queue.length - 1} more pending
          </div>
        )}
      </div>
    </div>
  );
}
