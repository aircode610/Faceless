import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchRuns } from "../api/runs";
import type { RunSummary } from "../api/types";
import { timeAgo } from "../utils/format";

export default function RunsPage() {
  const [runs, setRuns] = useState<RunSummary[]>([]);

  useEffect(() => {
    fetchRuns().then((r) => setRuns(r.items));
  }, []);

  const statusColor = (s: string) =>
    s === "success" ? "bg-green-100 text-green-700"
    : s === "error" ? "bg-red-100 text-red-700"
    : "bg-yellow-100 text-yellow-700";

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Execution Traces</h1>
      <div className="space-y-2">
        {runs.map((r) => (
          <Link to={`/runs/${r.id}`} key={r.id} className="record-card flex items-center justify-between no-underline block">
            <div className="flex-1">
              <div className="font-medium text-sm truncate max-w-[500px]">{r.task_description}</div>
              <div className="flex items-center gap-2 mt-1 text-xs" style={{ color: "var(--color-muted)" }}>
                <span>{timeAgo(r.created_at)}</span>
                <span>·</span>
                <span>{r.iterations} iterations</span>
                <span>·</span>
                <span>{r.selected_skill_ids.length} skills</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {r.selected_skill_ids.map((sid) => (
                <span key={sid} className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-600 max-w-[120px] truncate">
                  {sid.split("__")[0]}
                </span>
              ))}
              <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(r.execution_status)}`}>
                {r.execution_status}
              </span>
            </div>
          </Link>
        ))}
        {runs.length === 0 && (
          <div className="text-center py-8" style={{ color: "var(--color-muted)" }}>
            No runs yet. Run a task with: <code>python main.py run -t "your task"</code>
          </div>
        )}
      </div>
    </div>
  );
}
