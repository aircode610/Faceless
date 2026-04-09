import { useEffect, useRef, useState } from "react";
import type { Job } from "../api/agent";
import { Check, X, Loader2, CheckCircle, XCircle, Circle, MinusCircle, Bot, Info } from "lucide-react";

const LEVEL_COLORS: Record<string, string> = {
  info: "text-gray-600",
  llm: "text-purple-600",
  done: "text-green-700",
  error: "text-red-600",
};

function StepIcon({ status }: { status: string }) {
  if (status === "done")    return <CheckCircle className="w-3.5 h-3.5 text-green-600" />;
  if (status === "running") return <Loader2 className="w-3.5 h-3.5 animate-spin text-orange-500" />;
  if (status === "error")   return <XCircle className="w-3.5 h-3.5 text-red-500" />;
  if (status === "skipped") return <MinusCircle className="w-3.5 h-3.5 text-gray-400" />;
  return <Circle className="w-3.5 h-3.5 text-gray-300" />;
}

function LevelIcon({ level }: { level: string }) {
  if (level === "info")  return <Info className="w-3 h-3" />;
  if (level === "llm")   return <Bot className="w-3 h-3" />;
  if (level === "done")  return <Check className="w-3 h-3" />;
  if (level === "error") return <X className="w-3 h-3" />;
  return <span className="w-3 h-3 flex items-center justify-center">·</span>;
}

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
          {job.status === "done"  && <CheckCircle className="w-5 h-5 text-green-600" />}
          {job.status === "error" && <XCircle className="w-5 h-5 text-red-600" />}
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
            <span className="w-5 flex items-center justify-center">
              <StepIcon status={step.status} />
            </span>
            <span className={
              step.status === "done"    ? "text-green-700"
              : step.status === "running" ? "text-orange-700 font-medium"
              : step.status === "error"   ? "text-red-600"
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
                  <span className={`shrink-0 flex items-center ${LEVEL_COLORS[entry.level] || ""}`}>
                    <LevelIcon level={entry.level} />
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
