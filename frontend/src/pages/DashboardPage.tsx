import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchOverview } from "../api/overview";
import type { OverviewData } from "../api/types";
import MetricCard from "../components/MetricCard";
import EvolutionTypeBadge from "../components/EvolutionTypeBadge";
import { timeAgo } from "../utils/format";

export default function DashboardPage() {
  const [data, setData] = useState<OverviewData | null>(null);

  useEffect(() => {
    fetchOverview().then(setData);
  }, []);

  if (!data) return <div className="text-center py-12" style={{ color: "var(--color-muted)" }}>Loading...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <span className="text-sm" style={{ color: "var(--color-muted)" }}>
          "Valar Morghulis" — The Many-Faced God sees all
        </span>
      </div>

      {/* Metrics */}
      <div className="metrics-row">
        <MetricCard label="Active Skills" value={data.total_skills} />
        <MetricCard label="Avg Score" value={`${data.avg_score}%`} />
        <MetricCard label="Total Runs" value={data.total_runs} />
        <MetricCard label="Pending Approvals" value={data.pending_approvals} />
      </div>

      {/* Pipeline */}
      <div className="panel-surface">
        <h2 className="text-lg font-semibold mb-4">Pipeline</h2>
        <div className="flex items-center gap-2 overflow-x-auto">
          {data.pipeline.map((stage, i) => (
            <div key={stage.name} className="flex items-center gap-2">
              <div className="record-card text-center min-w-[130px]">
                <div className="font-medium text-sm">{stage.name}</div>
                <div className="text-xs mt-1" style={{ color: "var(--color-muted)" }}>{stage.description}</div>
              </div>
              {i < data.pipeline.length - 1 && (
                <span style={{ color: "var(--color-muted)" }}>→</span>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Top Skills */}
        <div className="panel-surface">
          <h2 className="text-lg font-semibold mb-3">Top Skills</h2>
          <div className="space-y-2">
            {data.top_skills.map((s) => (
              <Link to={`/skills/${s.skill_id}`} key={s.skill_id} className="record-card flex items-center justify-between no-underline">
                <div>
                  <span className="font-medium text-sm">{s.name}</span>
                  <EvolutionTypeBadge type={s.lineage_origin} />
                </div>
                <div className="text-sm font-semibold" style={{ color: "var(--color-primary)" }}>
                  {s.score}%
                </div>
              </Link>
            ))}
            {data.top_skills.length === 0 && (
              <div className="text-sm" style={{ color: "var(--color-muted)" }}>No skills yet</div>
            )}
          </div>
        </div>

        {/* Recent Runs */}
        <div className="panel-surface">
          <h2 className="text-lg font-semibold mb-3">Recent Runs</h2>
          <div className="space-y-2">
            {data.recent_runs.map((r: any) => (
              <Link to={`/runs/${r.id}`} key={r.id} className="record-card block no-underline">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium truncate max-w-[300px]">{r.task_description}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    r.execution_status === "success" ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"
                  }`}>
                    {r.execution_status}
                  </span>
                </div>
                <div className="text-xs mt-1" style={{ color: "var(--color-muted)" }}>
                  {r.iterations} iterations · {timeAgo(r.created_at)}
                </div>
              </Link>
            ))}
            {data.recent_runs.length === 0 && (
              <div className="text-sm" style={{ color: "var(--color-muted)" }}>No runs yet</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
