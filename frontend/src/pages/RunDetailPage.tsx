import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchRunDetail } from "../api/runs";
import type { RunDetail } from "../api/types";
import TraceTimeline from "../components/TraceTimeline";
import PriorityBadge from "../components/PriorityBadge";
import { timeAgo } from "../utils/format";

type Tab = "timeline" | "skills" | "analysis";

export default function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<RunDetail | null>(null);
  const [tab, setTab] = useState<Tab>("timeline");

  useEffect(() => {
    if (runId) fetchRunDetail(runId).then(setRun);
  }, [runId]);

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
        <button onClick={() => setTab("timeline")} className={tabClass("timeline")}>Timeline</button>
        <button onClick={() => setTab("skills")} className={tabClass("skills")}>Skills Used</button>
        <button onClick={() => setTab("analysis")} className={tabClass("analysis")}>Analysis</button>
      </div>

      {/* Tab Content */}
      <div className="panel-surface">
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
                      {j.skill_applied ? "✓ Applied" : "✗ Not applied"}
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
                Task {run.llm_task_completed ? "Completed ✓" : "Incomplete"}
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
                        {t.success ? "✓" : "✗"} {t.duration_ms}ms
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
