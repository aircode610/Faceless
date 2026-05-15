import { useEffect, useState, useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import { Check, X, CheckCircle, MessageSquare, Send, AlertTriangle } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { fetchRunDetail, submitSuggestionFeedback } from "../api/runs";
import type { RunDetail, EvolutionSuggestion } from "../api/types";
import TraceTimeline from "../components/TraceTimeline";
import PriorityBadge from "../components/PriorityBadge";
import EvolutionTypeBadge from "../components/EvolutionTypeBadge";
import InfoTip from "../components/InfoTip";
import { timeAgo } from "../utils/format";

type Tab = "result" | "timeline" | "skills" | "analysis";

function SuggestionCard({ sug, onFeedbackSaved }: { sug: EvolutionSuggestion; onFeedbackSaved: () => void }) {
  const [feedback, setFeedback] = useState(sug.user_feedback || "");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(!!sug.user_feedback);

  const handleSubmit = async () => {
    if (!feedback.trim()) return;
    setSaving(true);
    try {
      await submitSuggestionFeedback(sug.id, feedback);
      setSaved(true);
      setEditing(false);
      onFeedbackSaved();
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  };

  const targetSkills = (() => {
    try { return JSON.parse(sug.target_skill_ids || "[]"); }
    catch { return []; }
  })();

  return (
    <div className="record-card border-l-4" style={{ borderLeftColor: sug.type === "fix" ? "#3b82f6" : sug.type === "derived" ? "#14b8a6" : "#22c55e" }}>
      <div className="flex items-center gap-2 flex-wrap">
        <PriorityBadge priority={sug.priority} />
        <EvolutionTypeBadge type={sug.type} />
        {targetSkills.map((sid: string) => (
          <Link key={sid} to={`/skills/${sid}`} className="text-xs font-mono hover:underline" style={{ color: "var(--color-primary)" }}>
            {sid.split("__")[0]}
          </Link>
        ))}
      </div>

      {/* What needs to change */}
      <div className="mt-2 text-sm" style={{ color: "var(--color-ink)" }}>
        {sug.direction}
      </div>

      {/* Why — the evidence */}
      {sug.reason && (
        <div className="mt-2 text-xs p-2.5 rounded-lg" style={{ background: "var(--color-bg-page)", color: "var(--color-muted)" }}>
          <span className="font-semibold" style={{ color: "var(--color-ink)" }}>Evidence: </span>
          {sug.reason}
        </div>
      )}

      {/* Feedback input */}
      <div className="mt-3">
        {saved && !editing ? (
          <div className="flex items-start gap-2 p-2.5 rounded-lg bg-blue-50">
            <MessageSquare className="w-3.5 h-3.5 text-blue-600 mt-0.5 shrink-0" />
            <div className="flex-1">
              <div className="text-xs text-blue-700">{feedback}</div>
              <button
                onClick={() => setEditing(true)}
                className="text-[10px] text-blue-500 hover:underline mt-1"
              >
                Edit feedback
              </button>
            </div>
          </div>
        ) : (
          <div className="flex gap-2">
            <input
              type="text"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
              placeholder="Add your feedback for this evolution..."
              className="flex-1 text-xs px-3 py-2 rounded-lg border focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
              style={{ borderColor: "var(--color-border)" }}
            />
            <button
              onClick={handleSubmit}
              disabled={saving || !feedback.trim()}
              className="px-3 py-2 rounded-lg text-xs font-medium text-white flex items-center gap-1 disabled:opacity-50"
              style={{ background: "var(--color-primary)" }}
            >
              <Send className="w-3 h-3" /> {saving ? "..." : "Save"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<RunDetail | null>(null);
  const [tab, setTab] = useState<Tab>("result");

  const reload = () => {
    if (runId) fetchRunDetail(runId).then(setRun);
  };

  useEffect(() => { reload(); }, [runId]);

  const resultMessage = useMemo(() => {
    if (!run) return null;
    for (let i = run.conversation.length - 1; i >= 0; i--) {
      const msg = run.conversation[i];
      if (msg.role === "assistant" && msg.content) {
        return msg.content;
      }
    }
    return null;
  }, [run]);

  // Separate failed tool calls
  const failedTools = useMemo(() => {
    if (!run) return [];
    return run.trajectory.filter((t) => !t.success);
  }, [run]);

  // Skills that weren't applied
  const unappliedSkills = useMemo(() => {
    if (!run) return [];
    return run.skill_judgments.filter((j) => !j.skill_applied);
  }, [run]);

  if (!run) return <div className="text-center py-12" style={{ color: "var(--color-muted)" }}>Loading...</div>;

  const tabClass = (t: Tab) =>
    `px-3 py-1.5 text-sm rounded-lg cursor-pointer transition-colors ${
      tab === t ? "text-[var(--color-primary)] bg-orange-50 font-medium" : "text-[var(--color-muted)] hover:text-[var(--color-ink)]"
    }`;

  const hasFindings = run.evolution_suggestions.length > 0 || failedTools.length > 0 || unappliedSkills.length > 0;

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
        <button onClick={() => setTab("result")} className={tabClass("result")}>
          Result
        </button>
        <button onClick={() => setTab("timeline")} className={tabClass("timeline")}>Trace</button>
        <button onClick={() => setTab("skills")} className={tabClass("skills")}>Skills Used</button>
        <button onClick={() => setTab("analysis")} className={tabClass("analysis")}>Analysis</button>
      </div>

      {/* Tab Content */}
      {tab === "result" && (
        <div className="grid grid-cols-5 gap-6">
          {/* Left: result + stats */}
          <div className={`${hasFindings ? "col-span-3" : "col-span-5"} space-y-4`}>
            <div className="panel-surface space-y-4">
              {/* Status banner */}
              <div className={`flex items-center gap-2 p-3 rounded-lg text-sm ${
                run.llm_task_completed ? "bg-green-50 text-green-700" : "bg-yellow-50 text-yellow-700"
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
                  <div className="text-xs" style={{ color: "var(--color-muted)" }}>Iterations <InfoTip text="Number of think-act cycles the agent went through." size={12} /></div>
                </div>
                <div className="text-center p-3 rounded-lg" style={{ background: "var(--color-bg-page)" }}>
                  <div className="text-lg font-semibold" style={{ color: "var(--color-ink)" }}>{run.trajectory.length}</div>
                  <div className="text-xs" style={{ color: "var(--color-muted)" }}>Tool Calls <InfoTip text="External tools the agent invoked during this run." size={12} /></div>
                </div>
                <div className="text-center p-3 rounded-lg" style={{ background: "var(--color-bg-page)" }}>
                  <div className="text-lg font-semibold" style={{ color: "var(--color-ink)" }}>{run.skill_judgments.length}</div>
                  <div className="text-xs" style={{ color: "var(--color-muted)" }}>Skills Used <InfoTip text="Skills injected into the agent's prompt for this task." size={12} /></div>
                </div>
              </div>
            </div>
          </div>

          {/* Right: findings & feedback */}
          {hasFindings && (
            <div className="col-span-2 space-y-4">
              {/* Issues detected */}
              {(failedTools.length > 0 || unappliedSkills.length > 0) && (
                <div className="panel-surface">
                  <h3 className="text-sm font-semibold mb-3 flex items-center gap-1.5">
                    <AlertTriangle className="w-4 h-4" style={{ color: "var(--color-danger)" }} />
                    Issues Detected
                    <InfoTip text="Problems found during this run: tool failures and skills that were selected but not followed by the agent." />
                  </h3>
                  <div className="space-y-2">
                    {failedTools.map((t, i) => (
                      <div key={`tool-${i}`} className="text-xs p-2 rounded-lg flex items-center gap-2 bg-red-50">
                        <X className="w-3 h-3 text-red-500 shrink-0" />
                        <span className="font-medium text-red-700">{t.tool}</span>
                        <span className="text-red-500">failed at iter {t.iter} ({t.duration_ms}ms)</span>
                      </div>
                    ))}
                    {unappliedSkills.map((j) => (
                      <div key={j.skill_id} className="text-xs p-2 rounded-lg flex items-start gap-2 bg-yellow-50">
                        <AlertTriangle className="w-3 h-3 text-yellow-600 mt-0.5 shrink-0" />
                        <div>
                          <Link to={`/skills/${j.skill_id}`} className="font-medium text-yellow-700 hover:underline">
                            {j.skill_id.split("__")[0]}
                          </Link>
                          <span className="text-yellow-600"> — selected but not applied</span>
                          {j.note && <div className="text-yellow-500 mt-0.5">{j.note}</div>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Proposed changes with feedback */}
              {run.evolution_suggestions.length > 0 && (
                <div className="panel-surface">
                  <h3 className="text-sm font-semibold mb-3 flex items-center gap-1.5">
                    Proposed Changes
                    <span className="text-xs font-normal px-1.5 py-0.5 rounded-full bg-orange-100 text-orange-700">
                      {run.evolution_suggestions.length}
                    </span>
                    <InfoTip text="The system analyzed this run and proposed these skill improvements. Add your feedback to guide the evolution — it will be included in the LLM prompt when the change is generated." />
                  </h3>
                  <div className="space-y-3">
                    {run.evolution_suggestions.map((sug) => (
                      <SuggestionCard
                        key={sug.id}
                        sug={sug}
                        onFeedbackSaved={reload}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {tab !== "result" && (
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
                  <h3 className="text-sm font-semibold mb-2">
                    Evolution Suggestions
                    <InfoTip text="Improvements proposed after analyzing this run. FIX = repair, DERIVED = enhance, CAPTURED = new skill." />
                  </h3>
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
                        {e.reason && (
                          <div className="text-xs mt-1 italic" style={{ color: "var(--color-muted)" }}>{e.reason}</div>
                        )}
                        {e.user_feedback && (
                          <div className="text-xs mt-1 p-2 rounded bg-blue-50 text-blue-700">
                            <MessageSquare className="w-3 h-3 inline mr-1" />
                            {e.user_feedback}
                          </div>
                        )}
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
      )}
    </div>
  );
}
