import { useEffect, useState, useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import { Check, X, CheckCircle } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { fetchRunDetail } from "../api/runs";
import type { RunDetail } from "../api/types";
import TraceTimeline from "../components/TraceTimeline";
import PriorityBadge from "../components/PriorityBadge";
import { timeAgo } from "../utils/format";

type Tab = "result" | "timeline" | "skills" | "analysis";

export default function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<RunDetail | null>(null);
  const [tab, setTab] = useState<Tab>("result");

  useEffect(() => {
    if (runId) fetchRunDetail(runId).then(setRun);
  }, [runId]);

  // Extract the final assistant message (the agent's answer)
  const resultMessage = useMemo(() => {
    if (!run) return null;
    // Walk backwards through the conversation to find the last assistant message
    for (let i = run.conversation.length - 1; i >= 0; i--) {
      const msg = run.conversation[i];
      if (msg.role === "assistant" && msg.content) {
        return msg.content;
      }
    }
    return null;
  }, [run]);

  if (!run) return <div className="text-center py-12" style={{ color: "var(--color-muted)" }}>Loading...</div>;

  const tabClass = (t: Tab) =>
    `px-3 py-1.5 text-sm rounded-lg cursor-pointer transition-colors ${
      tab === t ? "text-[var(--color-primary)] bg-orange-50 font-medium" : "text-[var(--color-muted)] hover:text-[var(--color-ink)]"
    }`;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">{run.task_description}</h1>
        <div className="flex items-center gap-3 mt-1 text-xs" style={{ color: "var(--color-muted)" }}>
          <span className={`px-2 py-0.5 rounded-full text-xs ${
            run.execution_status === "success" ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"
          }`}>{run.execution_status}</span>
          <span>{run.iterations} iterations</span>
          <span>{timeAgo(run.created_at)}</span>
          <span>Run ID: {run.id}</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1">
        <button onClick={() => setTab("result")} className={tabClass("result")}>Result</button>
        <button onClick={() => setTab("timeline")} className={tabClass("timeline")}>Trace</button>
        <button onClick={() => setTab("skills")} className={tabClass("skills")}>Skills Used</button>
        <button onClick={() => setTab("analysis")} className={tabClass("analysis")}>Analysis</button>
      </div>

      {/* Tab Content */}
      <div className="panel-surface">
        {tab === "result" && (
          <div className="space-y-4">
            {/* Status banner */}
            <div className={`flex items-center gap-2 p-3 rounded-lg text-sm ${
              run.llm_task_completed
                ? "bg-green-50 text-green-700"
                : "bg-yellow-50 text-yellow-700"
            }`}>
              {run.llm_task_completed
                ? <><CheckCircle className="w-4 h-4 shrink-0" /> The agent completed this task successfully.</>
                : <><X className="w-4 h-4 shrink-0" /> The agent did not complete this task.</>
              }
            </div>

            {/* Final answer */}
            {resultMessage ? (
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: "var(--color-muted)" }}>
                  Agent's Final Response
                </h3>
                <div
                  className="p-4 rounded-lg text-sm leading-relaxed prose prose-sm max-w-none
                             prose-headings:text-[var(--color-ink)] prose-p:text-[var(--color-ink)]
                             prose-strong:text-[var(--color-ink)] prose-code:text-[var(--color-primary)]
                             prose-code:bg-orange-50 prose-code:px-1 prose-code:py-0.5 prose-code:rounded
                             prose-pre:bg-gray-900 prose-pre:text-gray-100
                             prose-a:text-[var(--color-primary)] prose-li:text-[var(--color-ink)]"
                  style={{ background: "var(--color-bg-page)" }}
                >
                  <ReactMarkdown>{resultMessage.replace(/<COMPLETE>/g, "").trim()}</ReactMarkdown>
                </div>
              </div>
            ) : (
              <div className="text-sm py-4" style={{ color: "var(--color-muted)" }}>
                No response recorded for this run.
              </div>
            )}

            {/* Quick stats */}
            <div className="grid grid-cols-3 gap-3 pt-2">
              <div className="text-center p-3 rounded-lg" style={{ background: "var(--color-bg-page)" }}>
                <div className="text-lg font-semibold" style={{ color: "var(--color-ink)" }}>{run.iterations}</div>
                <div className="text-xs" style={{ color: "var(--color-muted)" }}>Iterations</div>
              </div>
              <div className="text-center p-3 rounded-lg" style={{ background: "var(--color-bg-page)" }}>
                <div className="text-lg font-semibold" style={{ color: "var(--color-ink)" }}>{run.trajectory.length}</div>
                <div className="text-xs" style={{ color: "var(--color-muted)" }}>Tool Calls</div>
              </div>
              <div className="text-center p-3 rounded-lg" style={{ background: "var(--color-bg-page)" }}>
                <div className="text-lg font-semibold" style={{ color: "var(--color-ink)" }}>{run.skill_judgments.length}</div>
                <div className="text-xs" style={{ color: "var(--color-muted)" }}>Skills Used</div>
              </div>
            </div>
          </div>
        )}

        {tab === "timeline" && (
          <TraceTimeline conversation={run.conversation} />
        )}

        {tab === "skills" && (
          <div className="space-y-3">
            {run.skill_judgments.length === 0 ? (
              <div className="text-sm" style={{ color: "var(--color-muted)" }}>No skill judgments recorded</div>
            ) : (
              run.skill_judgments.map((j) => (
                <div key={j.skill_id} className={`record-card ${!j.skill_applied ? "border-l-4 border-l-yellow-400" : "border-l-4 border-l-green-400"}`}>
                  <div className="flex items-center gap-2">
                    <Link to={`/skills/${j.skill_id}`} className="font-medium text-sm hover:underline">
                      {j.skill_id.split("__")[0]}
                    </Link>
                    <span className={j.skill_applied ? "text-green-600 text-xs" : "text-yellow-600 text-xs"}>
                      {j.skill_applied ? <><Check className="w-3 h-3 inline mr-0.5" />Applied</> : <><X className="w-3 h-3 inline mr-0.5" />Not applied</>}
                    </span>
                  </div>
                  {j.note && <div className="text-xs mt-1" style={{ color: "var(--color-muted)" }}>{j.note}</div>}
                </div>
              ))
            )}
          </div>
        )}

        {tab === "analysis" && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <span className={`text-sm font-medium ${run.llm_task_completed ? "text-green-600" : "text-yellow-600"}`}>
                {run.llm_task_completed ? <><CheckCircle className="w-4 h-4 inline mr-1" />Task Completed</> : "Task Incomplete"}
              </span>
            </div>

            {run.evolution_suggestions.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold mb-2">Evolution Suggestions</h3>
                <div className="space-y-2">
                  {run.evolution_suggestions.map((e) => (
                    <div key={e.id} className="record-card">
                      <div className="flex items-center gap-2">
                        <PriorityBadge priority={e.priority} />
                        <span className="text-xs font-medium uppercase">{e.type}</span>
                        {e.pattern_key && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 font-mono">{e.pattern_key}</span>
                        )}
                      </div>
                      <div className="text-sm mt-1">{e.direction}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {run.trajectory.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold mb-2">Tool Calls</h3>
                <div className="space-y-1">
                  {run.trajectory.map((t, i) => (
                    <div key={i} className="text-xs flex items-center gap-2 py-1">
                      <span className="font-mono" style={{ color: "var(--color-muted)" }}>iter {t.iter}</span>
                      <span className="font-medium">{t.tool}</span>
                      <span className={t.success ? "text-green-600" : "text-red-600"}>
                        {t.success ? <Check className="w-3 h-3 inline" /> : <X className="w-3 h-3 inline" />} {t.duration_ms}ms
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
