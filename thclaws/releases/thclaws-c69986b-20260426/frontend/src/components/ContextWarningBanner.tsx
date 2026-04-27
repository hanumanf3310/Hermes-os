import { useEffect, useState } from "react";
import { send, subscribe } from "../hooks/useIPC";

// Pops up when the shared session's JSONL file crosses the fork
// threshold. Two actions: kick off the /fork flow (LLM-summary seed
// into a fresh session) or dismiss for the rest of this session.
// Fires at most once per session — the backend only emits a single
// ContextWarning ViewEvent per session.
export function ContextWarningBanner() {
  const [warning, setWarning] = useState<{ fileSizeMb: number } | null>(null);

  useEffect(() => {
    const unsub = subscribe((msg) => {
      if (msg.type === "chat_context_warning") {
        setWarning({
          fileSizeMb:
            typeof msg.file_size_mb === "number"
              ? (msg.file_size_mb as number)
              : 0,
        });
      } else if (
        msg.type === "chat_history_replaced" ||
        msg.type === "new_session_ack"
      ) {
        // Session changed → drop the stale warning.
        setWarning(null);
      }
    });
    return unsub;
  }, []);

  if (!warning) return null;

  return (
    <div
      className="fixed z-40 flex items-center gap-2 px-3 py-2 rounded border shadow-lg text-xs"
      style={{
        top: 44,
        right: 12,
        maxWidth: 440,
        background: "var(--bg-primary)",
        // Red tint on the banner border + shadow to signal "attention
        // needed" rather than a normal info toast — this only fires
        // when the session file is big enough that compaction alone
        // isn't keeping up and a fork is genuinely recommended.
        borderColor: "var(--danger, #e06c75)",
        borderWidth: 1.5,
        color: "var(--text-primary)",
        boxShadow: "0 4px 16px rgba(224, 108, 117, 0.35)",
      }}
      role="alert"
    >
      <span
        className="w-2 h-2 rounded-full shrink-0"
        style={{ background: "var(--danger, #e06c75)" }}
        aria-hidden
      />
      <span className="flex-1">
        Session file is {warning.fileSizeMb.toFixed(1)} MB. Continue in a fresh
        session with a summary of the history?
      </span>
      <button
        className="text-xs px-2 py-1 rounded"
        style={{
          background: "var(--danger, #e06c75)",
          color: "#ffffff",
        }}
        onClick={() => {
          send({ type: "shell_input", text: "/fork" });
          setWarning(null);
        }}
        title="Save the current session, start a new one seeded with an LLM-summarized view of the prior history"
      >
        Fork with summary
      </button>
      <button
        className="text-xs px-2 py-1 rounded hover:bg-white/5"
        style={{ color: "var(--text-secondary)" }}
        onClick={() => setWarning(null)}
        title="Keep typing in the current session"
      >
        Dismiss
      </button>
    </div>
  );
}
