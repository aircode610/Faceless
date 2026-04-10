import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getAgentStatus, startRun, pollJob } from "../api/agent";
import type { Job } from "../api/agent";
import JobProgress from "../components/JobProgress";
import { Play, Loader2, Bot, ArrowRight, CheckCircle, AlertTriangle, CheckCircle2, XCircle } from "lucide-react";

export default function RunTaskPage() {
  const [task, setTask] = useState("");
  const [bootstrapped, setBootstrapped] = useState<boolean | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");
  const [history, setHistory] = useState<Job[]>([]);

  useEffect(() => {
    getAgentStatus().then((s) => setBootstrapped(s.bootstrapped));
  }, []);

  // Poll job
  useEffect(() => {
    if (!job || job.status !== "running") return;
    const interval = setInterval(() => {
      pollJob(job.id).then(setJob);
    }, 2000);
    return () => clearInterval(interval);
  }, [job]);

  const handleSubmit = async () => {
    if (!task.trim()) return;
    setError("");
    try {
      const { job_id } = await startRun(task);
      const newJob: Job = {
        id: job_id, type: "run", status: "running",
        started_at: new Date().toISOString(), finished_at: null,
        result: null, error: null, steps: [], task,
      };
      setJob(newJob);
      // Poll
      const poll = setInterval(async () => {
        const updated = await pollJob(job_id);
        setJob(updated);
        if (updated.status !== "running") {
          clearInterval(poll);
          setHistory((h) => [updated, ...h]);
        }
      }, 2000);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || "Failed to start task");
    }
  };

  if (bootstrapped === null) {
    return <div className="text-center py-12" style={{ color: "var(--color-muted)" }}>Loading...</div>;
  }

  if (!bootstrapped) {
    return (
      <div className="max-w-2xl mx-auto text-center space-y-4 py-12">
        <img src="/faceless.svg" alt="Faceless" className="w-20 h-20 mx-auto" />
        <h1 className="text-2xl font-semibold">No Agent Yet</h1>
        <p style={{ color: "var(--color-muted)" }}>
          A man must first receive his face before he can serve.
        </p>
        <Link
          to="/create"
          className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg text-white text-sm font-medium"
          style={{ background: "var(--color-primary)" }}
        >
          <Bot className="w-4 h-4" /> Create an Agent
        </Link>
      </div>
    );
  }

  const result = job?.result as Record<string, any> | null;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold">Run a Task</h1>
        <span className="text-sm" style={{ color: "var(--color-muted)" }}>
          "A man gives a task. The Faceless Men deliver."
        </span>
      </div>

      {/* Input */}
      <div className="panel-surface space-y-3">
        <label className="block text-sm font-medium">Task Description</label>
        <textarea
          value={task}
          onChange={(e) => setTask(e.target.value)}
          placeholder="Describe what you want the agent to do..."
          className="w-full text-sm p-3 rounded-lg border min-h-[100px] resize-y"
          style={{ borderColor: "var(--color-border)" }}
          disabled={job?.status === "running"}
        />

        {error && (
          <div className="text-sm p-3 rounded-lg bg-red-50 text-red-700 border border-red-200">
            {error}
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={!task.trim() || job?.status === "running"}
          className="w-full py-3 rounded-lg text-white text-sm font-medium transition-opacity disabled:opacity-40 flex items-center justify-center gap-2"
          style={{ background: "var(--color-primary)" }}
        >
          {job?.status === "running"
            ? <><Loader2 className="w-4 h-4 animate-spin" /> Running...</>
            : <><Play className="w-4 h-4" /> Execute Task</>}
        </button>
      </div>

      {/* Progress */}
      {job && (
        <div className="panel-surface space-y-4">
          <JobProgress job={job} />

          {job.status === "done" && result && (
            <div className="space-y-3 pt-3 border-t" style={{ borderColor: "var(--color-border)" }}>
              {/* Summary */}
              <div className="flex items-center gap-2">
                {result.task_completed
                  ? <><CheckCircle className="w-4 h-4 text-green-600" /><span className="text-green-600 text-sm font-medium">Task Completed</span></>
                  : <><AlertTriangle className="w-4 h-4 text-yellow-600" /><span className="text-yellow-600 text-sm font-medium">Task Incomplete</span></>}
              </div>
              {result.execution_note && (
                <p className="text-sm" style={{ color: "var(--color-muted)" }}>
                  {result.execution_note}
                </p>
              )}

              {/* Stats */}
              <div className="grid grid-cols-4 gap-3">
                <div className="text-center p-2 rounded-lg" style={{ background: "var(--color-bg-page)" }}>
                  <div className="text-lg font-semibold">{(result.selected_skills || []).length}</div>
                  <div className="text-[10px]" style={{ color: "var(--color-muted)" }}>Skills Used</div>
                </div>
                <div className="text-center p-2 rounded-lg" style={{ background: "var(--color-bg-page)" }}>
                  <div className="text-lg font-semibold">{result.evolution_suggestions || 0}</div>
                  <div className="text-[10px]" style={{ color: "var(--color-muted)" }}>Suggestions</div>
                </div>
                <div className="text-center p-2 rounded-lg" style={{ background: "var(--color-bg-page)" }}>
                  <div className="text-lg font-semibold text-green-600">{result.evolutions_succeeded || 0}</div>
                  <div className="text-[10px]" style={{ color: "var(--color-muted)" }}>Evolved</div>
                </div>
                <div className="text-center p-2 rounded-lg" style={{ background: "var(--color-bg-page)" }}>
                  <div className="text-lg font-semibold">{result.feature_requests || 0}</div>
                  <div className="text-[10px]" style={{ color: "var(--color-muted)" }}>Feature Req.</div>
                </div>
              </div>

              {/* Evolution details */}
              {(result.evolution_details || []).length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold mb-1.5" style={{ color: "var(--color-muted)" }}>
                    Evolutions
                  </h3>
                  <div className="space-y-1">
                    {(result.evolution_details as any[]).map((e: any, i: number) => (
                      <div key={i} className="text-xs flex items-center gap-2 p-2 rounded-lg"
                        style={{ background: "var(--color-bg-page)" }}>
                        {e.succeeded
                          ? <CheckCircle2 className="w-3.5 h-3.5 text-green-600 shrink-0" />
                          : <XCircle className="w-3.5 h-3.5 text-red-500 shrink-0" />}
                        <span className="uppercase font-medium text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600">
                          {e.type}
                        </span>
                        <span className="flex-1 truncate">{e.change_summary || e.error_reason}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2">
                <Link
                  to={`/runs/${result.run_id}`}
                  className="flex-1 text-center py-2 rounded-lg text-white text-sm font-medium flex items-center justify-center gap-2"
                  style={{ background: "var(--color-accent)" }}
                >
                  View Run Details <ArrowRight className="w-4 h-4" />
                </Link>
                {(result.evolutions_succeeded || 0) > 0 && (
                  <Link
                    to="/review"
                    className="flex-1 text-center py-2 rounded-lg text-white text-sm font-medium flex items-center justify-center gap-2"
                    style={{ background: "var(--color-primary)" }}
                  >
                    Review Evolutions <ArrowRight className="w-4 h-4" />
                  </Link>
                )}
                <button
                  onClick={() => { setJob(null); setTask(""); }}
                  className="px-4 py-2 rounded-lg border text-sm"
                  style={{ borderColor: "var(--color-border)" }}
                >
                  New Task
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Recent runs from this session */}
      {history.length > 1 && (
        <div className="panel-surface">
          <h3 className="text-sm font-semibold mb-2">Session History</h3>
          <div className="space-y-1">
            {history.slice(1).map((h) => (
              <Link
                key={h.id}
                to={`/runs/${(h.result as any)?.run_id || ""}`}
                className="block text-xs p-2 rounded-lg hover:bg-gray-50"
                style={{ color: "var(--color-muted)" }}
              >
                {h.task} — {h.status}
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
