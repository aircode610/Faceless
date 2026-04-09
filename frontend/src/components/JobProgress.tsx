import { useEffect, useRef, useState } from "react";
import type { Job } from "../api/agent";

const STEP_ICONS: Record<string, string> = {
  done: "✅",
  running: "⏳",
  pending: "○",
  error: "❌",
  skipped: "⊘",
};

const LEVEL_COLORS: Record<string, string> = {
  info: "text-gray-600",
  llm: "text-purple-600",
  done: "text-green-700",
  error: "text-red-600",
};

const LEVEL_ICONS: Record<string, string> = {
  info: "ℹ",
  llm: "🤖",
  done: "✓",
  error: "✗",
};

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("en-US", { hour12: false });
  } catch {
    return "";
  }
}

export default function JobProgress({ job }: { job: Job }) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  const elapsed = job.finished_at
    ? ((new Date(job.finished_at).getTime() - new Date(job.started_at).getTime()) / 1000).toFixed(1)
    : ((Date.now() - new Date(job.started_at).getTime()) / 1000).toFixed(0);

  const log = job.log || [];

  // Auto-scroll the log to the bottom when new entries arrive
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [log.length]);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {job.status === "running" && (
            <div className="w-3 h-3 rounded-full bg-orange-400 animate-pulse" />
          )}
          {job.status === "done" && <span className="text-green-600 text-lg">✅</span>}
          {job.status === "error" && <span className="text-red-600 text-lg">❌</span>}
          <span className="font-semibold text-sm capitalize">{job.type}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full ${
            job.status === "running" ? "bg-orange-100 text-orange-700"
            : job.status === "done" ? "bg-green-100 text-green-700"
            : "bg-red-100 text-red-700"
          }`}>
            {job.status}
          </span>
        </div>
        <span className="text-xs font-mono" style={{ color: "var(--color-muted)" }}>
          {elapsed}s
        </span>
      </div>

      {/* Steps */}
      <div className="space-y-1.5 pl-1">
        {job.steps.map((step, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            <span className="w-5 text-center text-xs">
              {step.status === "running" ? (
                <span className="inline-block animate-spin">⏳</span>
              ) : (
                STEP_ICONS[step.status] || "○"
              )}
            </span>
            <span className={
              step.status === "done" ? "text-green-700"
              : step.status === "running" ? "text-orange-700 font-medium"
              : step.status === "error" ? "text-red-600"
              : ""
            } style={step.status === "pending" ? { color: "var(--color-muted)" } : {}}>
              {step.name}
            </span>
          </div>
        ))}
      </div>

      {/* Event log / trace */}
      {log.length > 0 && (
        <div className="border-t pt-3" style={{ borderColor: "var(--color-border)" }}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold" style={{ color: "var(--color-muted)" }}>
              Live Trace ({log.length})
            </span>
          </div>
          <div
            className="rounded-lg p-3 font-mono text-[11px] max-h-80 overflow-y-auto space-y-1"
            style={{ background: "var(--color-bg-page)", borderColor: "var(--color-border)" }}
          >
            {log.map((entry, i) => {
              const isExpandable = !!entry.detail;
              const isExpanded = expandedIdx === i;
              return (
                <div
                  key={i}
                  className={`flex items-start gap-2 ${isExpandable ? "cursor-pointer hover:bg-white rounded px-1 -mx-1" : ""}`}
                  onClick={() => isExpandable && setExpandedIdx(isExpanded ? null : i)}
                >
                  <span className="opacity-50 shrink-0">{formatTime(entry.ts)}</span>
                  <span className={`shrink-0 ${LEVEL_COLORS[entry.level] || ""}`}>
                    {LEVEL_ICONS[entry.level] || "·"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className={LEVEL_COLORS[entry.level] || ""}>
                      {entry.message}
                      {isExpandable && (
                        <span className="ml-1 opacity-50 text-[9px]">
                          [{isExpanded ? "hide" : "expand"}]
                        </span>
                      )}
                    </div>
                    {isExpandable && isExpanded && (
                      <pre className="mt-1 whitespace-pre-wrap text-[10px] opacity-80 p-2 rounded"
                           style={{ background: "var(--color-surface)" }}>
                        {entry.detail}
                      </pre>
                    )}
                  </div>
                </div>
              );
            })}
            <div ref={logEndRef} />
          </div>
        </div>
      )}

      {/* Error */}
      {job.error && (
        <div className="text-sm p-3 rounded-lg bg-red-50 text-red-700 border border-red-200">
          {job.error}
        </div>
      )}
    </div>
  );
}
