import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getAgentStatus, getDefaultMCPs, startBootstrap, pollJob } from "../api/agent";
import type { MCP, Job } from "../api/agent";
import JobProgress from "../components/JobProgress";
import { Bot, Check, AlertTriangle, Play, ArrowRight } from "lucide-react";

export default function CreateAgentPage() {
  const navigate = useNavigate();
  const [description, setDescription] = useState("");
  const [mcps, setMcps] = useState<(MCP & { selected: boolean })[]>([]);
  const [loading, setLoading] = useState(true);
  const [alreadyExists, setAlreadyExists] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getAgentStatus(), getDefaultMCPs()]).then(([status, defaults]) => {
      setAlreadyExists(status.bootstrapped);
      setMcps(defaults.map((m) => ({ ...m, selected: true })));
      setLoading(false);
    });
  }, []);

  // Poll job status
  useEffect(() => {
    if (!job || job.status !== "running") return;
    const interval = setInterval(() => {
      pollJob(job.id).then(setJob);
    }, 2000);
    return () => clearInterval(interval);
  }, [job]);

  const handleSubmit = async () => {
    if (!description.trim()) return;
    setError("");
    try {
      const selected = mcps.filter((m) => m.selected).map(({ name, description }) => ({ name, description }));
      const { job_id } = await startBootstrap(description, selected);
      setJob({ id: job_id, type: "bootstrap", status: "running", started_at: new Date().toISOString(), finished_at: null, result: null, error: null, steps: [], description });
      // Start polling
      const poll = setInterval(async () => {
        const updated = await pollJob(job_id);
        setJob(updated);
        if (updated.status !== "running") {
          clearInterval(poll);
        }
      }, 2000);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || "Bootstrap failed");
    }
  };

  const toggleMcp = (name: string) => {
    setMcps((prev) => prev.map((m) => m.name === name ? { ...m, selected: !m.selected } : m));
  };

  if (loading) {
    return <div className="text-center py-12" style={{ color: "var(--color-muted)" }}>Loading...</div>;
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="text-center space-y-2">
        <img src="/faceless.svg" alt="Faceless" className="w-20 h-20 mx-auto" />
        <h1 className="text-2xl font-semibold">The House of Black and White</h1>
        <p className="text-sm" style={{ color: "var(--color-muted)" }}>
          "A man must say his name." — Describe your agent and it shall be given a face.
        </p>
      </div>

      {alreadyExists && !job && (
        <div className="panel-surface text-center space-y-3">
          <p className="text-sm">An agent already exists. Creating a new one will <strong>replace</strong> it.</p>
          <div className="flex justify-center gap-3">
            <button
              onClick={() => navigate("/dashboard")}
              className="text-sm px-4 py-2 rounded-lg border"
              style={{ borderColor: "var(--color-border)" }}
            >
              Go to Dashboard
            </button>
            <button
              onClick={() => setAlreadyExists(false)}
              className="text-sm px-4 py-2 rounded-lg text-white"
              style={{ background: "var(--color-primary)" }}
            >
              Create New Agent
            </button>
          </div>
        </div>
      )}

      {(!alreadyExists || job) && (
        <>
          {/* Form */}
          {(!job || job.status === "error") && (
            <div className="panel-surface space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1.5">Agent Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Review GitHub pull requests for security issues and test coverage gaps"
                  className="w-full text-sm p-3 rounded-lg border min-h-[100px] resize-y"
                  style={{ borderColor: "var(--color-border)" }}
                />
                <p className="text-xs mt-1" style={{ color: "var(--color-muted)" }}>
                  Describe what your agent should do. Be specific — this determines which tools and skills it gets.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1.5">Available Tools (MCPs)</label>
                <p className="text-xs mb-2" style={{ color: "var(--color-muted)" }}>
                  The agent will select only the tools it needs. Toggle off any you don't want available.
                </p>
                <div className="grid grid-cols-2 gap-2">
                  {mcps.map((m) => (
                    <button
                      key={m.name}
                      onClick={() => toggleMcp(m.name)}
                      className={`text-left p-3 rounded-lg border text-sm transition-colors ${
                        m.selected ? "border-[var(--color-primary)] bg-orange-50" : "opacity-50"
                      }`}
                      style={{ borderColor: m.selected ? "var(--color-primary)" : "var(--color-border)" }}
                    >
                      <div className="flex items-center gap-2">
                        <span className={`w-4 h-4 rounded border flex items-center justify-center ${
                          m.selected ? "bg-[var(--color-primary)] text-white border-[var(--color-primary)]" : ""
                        }`} style={!m.selected ? { borderColor: "var(--color-border-dark)" } : {}}>
                          {m.selected && <Check className="w-3 h-3" />}
                        </span>
                        <span className="font-medium">{m.name}</span>
                        {m.credentials_available === true && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 flex items-center gap-0.5">
                            <Check className="w-2.5 h-2.5" /> credentials
                          </span>
                        )}
                        {m.credentials_available === false && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-yellow-100 text-yellow-700 flex items-center gap-0.5">
                            <AlertTriangle className="w-2.5 h-2.5" /> missing env var
                          </span>
                        )}
                      </div>
                      <div className="text-xs mt-1 pl-6" style={{ color: "var(--color-muted)" }}>
                        {m.description}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {error && (
                <div className="text-sm p-3 rounded-lg bg-red-50 text-red-700 border border-red-200">
                  {error}
                </div>
              )}

              <button
                onClick={handleSubmit}
                disabled={!description.trim()}
                className="w-full py-3 rounded-lg text-white text-sm font-medium transition-opacity disabled:opacity-40 flex items-center justify-center gap-2"
                style={{ background: "var(--color-primary)" }}
              >
                <Bot className="w-4 h-4" /> Begin the Ritual — Create Agent
              </button>
            </div>
          )}

          {/* Progress */}
          {job && (
            <div className="panel-surface space-y-4">
              <JobProgress job={job} />

              {/* Success result */}
              {job.status === "done" && job.result && (
                <div className="space-y-3 pt-3 border-t" style={{ borderColor: "var(--color-border)" }}>
                  <div className="text-sm font-medium text-green-700">
                    A new servant of the Many-Faced God is born.
                  </div>
                  <dl className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <dt style={{ color: "var(--color-muted)" }}>Agent Name</dt>
                      <dd className="font-medium">{(job.result as any).agent_name}</dd>
                    </div>
                    <div>
                      <dt style={{ color: "var(--color-muted)" }}>Selected MCPs</dt>
                      <dd className="font-medium">{((job.result as any).selected_mcps || []).join(", ")}</dd>
                    </div>
                    <div className="col-span-2">
                      <dt style={{ color: "var(--color-muted)" }}>Skills Created</dt>
                      <dd className="font-medium">
                        {((job.result as any).skills || []).join(", ")}
                      </dd>
                    </div>
                  </dl>
                  <div className="flex gap-2">
                    <button
                      onClick={() => navigate("/dashboard")}
                      className="flex-1 py-2 rounded-lg text-white text-sm font-medium flex items-center justify-center gap-2"
                      style={{ background: "var(--color-accent)" }}
                    >
                      Go to Dashboard <ArrowRight className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => navigate("/run")}
                      className="flex-1 py-2 rounded-lg text-white text-sm font-medium flex items-center justify-center gap-2"
                      style={{ background: "var(--color-primary)" }}
                    >
                      <Play className="w-4 h-4" /> Run a Task
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
