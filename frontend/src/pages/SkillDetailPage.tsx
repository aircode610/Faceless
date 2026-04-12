import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Check, X, Pencil, Save, XCircle, MessageSquare, Loader2, RotateCcw } from "lucide-react";
import { fetchSkillDetail, updateSkillContent, submitSkillFeedback } from "../api/skills";
import type { SkillDetail } from "../api/types";
import EvolutionTypeBadge from "../components/EvolutionTypeBadge";
import InfoTip from "../components/InfoTip";
import { pct, timeAgo } from "../utils/format";

const METRIC_HINTS: Record<string, string> = {
  "Applied Rate":
    "How often the agent actually followed this skill's instructions when it was selected for a task. Low = the agent ignores it.",
  "Completion Rate":
    "Of the times the agent applied this skill, how often did the task complete successfully. Low = instructions may be wrong.",
  "Effective Rate":
    "Overall success: completions / selections. Combines how often it's applied with how often it works.",
  "Fallback Rate":
    "How often this skill was selected but NOT applied AND the task failed. High = skill may be broken or outdated.",
};

export default function SkillDetailPage() {
  const { skillId } = useParams<{ skillId: string }>();
  const [skill, setSkill] = useState<SkillDetail | null>(null);

  // Editor state
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [saving, setSaving] = useState(false);

  // Feedback state
  const [feedback, setFeedback] = useState("");
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [revisedContent, setRevisedContent] = useState<string | null>(null);

  // Toast
  const [toast, setToast] = useState("");

  const reload = () => {
    if (skillId) fetchSkillDetail(skillId).then(setSkill);
  };

  useEffect(() => { reload(); }, [skillId]);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
  };

  const handleStartEdit = () => {
    if (!skill) return;
    setEditContent(skill.content);
    setEditing(true);
    setRevisedContent(null);
  };

  const handleSave = async () => {
    if (!skill) return;
    setSaving(true);
    try {
      await updateSkillContent(skill.skill_id, editContent);
      setEditing(false);
      showToast("Skill updated successfully");
      reload();
    } catch {
      showToast("Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setEditing(false);
    setEditContent("");
  };

  const handleFeedback = async () => {
    if (!skill || !feedback.trim()) return;
    setFeedbackLoading(true);
    setRevisedContent(null);
    try {
      const result = await submitSkillFeedback(skill.skill_id, feedback);
      setRevisedContent(result.revised);
      setEditContent(result.revised);
      setEditing(true);
    } catch {
      showToast("Failed to generate revision");
    } finally {
      setFeedbackLoading(false);
    }
  };

  const handleAcceptRevision = async () => {
    if (!skill || !revisedContent) return;
    setSaving(true);
    try {
      await updateSkillContent(skill.skill_id, revisedContent);
      setEditing(false);
      setRevisedContent(null);
      setFeedback("");
      showToast("Revision applied");
      reload();
    } catch {
      showToast("Failed to save revision");
    } finally {
      setSaving(false);
    }
  };

  if (!skill) return <div className="text-center py-12" style={{ color: "var(--color-muted)" }}>Loading...</div>;

  const metrics = [
    { label: "Applied Rate", value: skill.applied_rate, color: "var(--color-accent)" },
    { label: "Completion Rate", value: skill.completion_rate, color: "var(--color-primary)" },
    { label: "Effective Rate", value: skill.effective_rate, color: "#6366f1" },
    { label: "Fallback Rate", value: skill.fallback_rate, color: "var(--color-danger)" },
  ];

  return (
    <div className="space-y-6">
      {toast && (
        <div className="fixed top-4 right-4 z-50 px-4 py-2 rounded-lg bg-green-100 text-green-800 text-sm shadow-lg">
          {toast}
        </div>
      )}

      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-semibold">{skill.name}</h1>
        <EvolutionTypeBadge type={skill.lineage_origin} />
        <span className="text-sm px-2 py-0.5 rounded-full bg-gray-100">v{skill.generation + 1}</span>
        <span className={`text-xs px-2 py-0.5 rounded-full ${
          skill.status === "active" ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"
        }`}>
          {skill.status}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Left column */}
        <div className="col-span-2 space-y-4">
          {/* Metrics */}
          <div className="panel-surface">
            <h2 className="text-sm font-semibold mb-3">
              Quality Metrics
              <InfoTip text="These metrics track how well this skill performs across task executions. They update automatically after each run." />
            </h2>
            <div className="space-y-3">
              {metrics.map((m) => (
                <div key={m.label} className="flex items-center gap-3">
                  <span className="text-xs w-36 flex items-center" style={{ color: "var(--color-muted)" }}>
                    {m.label}
                    <InfoTip text={METRIC_HINTS[m.label]} />
                  </span>
                  <div className="flex-1 h-2.5 rounded-full bg-gray-100 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: pct(m.value), background: m.color }}
                    />
                  </div>
                  <span className="text-xs font-medium w-10 text-right">{pct(m.value)}</span>
                </div>
              ))}
            </div>
            <div className="mt-3 text-xs" style={{ color: "var(--color-muted)" }}>
              {skill.total_selections} selections · {skill.total_applied} applied · {skill.total_completions} completions
            </div>
          </div>

          {/* Skill Content — View / Edit */}
          <div className="panel-surface">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold">
                SKILL.md
                <InfoTip text="The full skill definition file. Contains instructions, procedures, and context that get injected into the agent's prompt when this skill is selected." />
              </h2>
              {skill.status === "active" && !editing && (
                <button
                  onClick={handleStartEdit}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors hover:bg-gray-50"
                  style={{ borderColor: "var(--color-border)", color: "var(--color-muted)" }}
                >
                  <Pencil className="w-3.5 h-3.5" /> Edit
                </button>
              )}
              {editing && (
                <div className="flex gap-2">
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-white"
                    style={{ background: "var(--color-accent)" }}
                  >
                    {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                    Save
                  </button>
                  <button
                    onClick={handleCancelEdit}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border"
                    style={{ borderColor: "var(--color-border)", color: "var(--color-muted)" }}
                  >
                    <XCircle className="w-3.5 h-3.5" /> Cancel
                  </button>
                </div>
              )}
            </div>

            {editing ? (
              <textarea
                value={editContent}
                onChange={(e) => { setEditContent(e.target.value); setRevisedContent(null); }}
                className="w-full text-xs font-mono p-4 rounded-lg border focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] resize-y"
                style={{ background: "var(--color-bg-page)", borderColor: "var(--color-border)", minHeight: 400 }}
                spellCheck={false}
              />
            ) : (
              <pre className="text-xs whitespace-pre-wrap p-4 rounded-lg overflow-x-auto" style={{ background: "var(--color-bg-page)" }}>
                {skill.content}
              </pre>
            )}
          </div>

          {/* Feedback Section */}
          {skill.status === "active" && (
            <div className="panel-surface">
              <h2 className="text-sm font-semibold mb-2">
                <MessageSquare className="w-4 h-4 inline mr-1.5" style={{ color: "var(--color-primary)" }} />
                Improve with Feedback
                <InfoTip text="Describe what you want to change in plain English. An LLM will revise the skill based on your feedback. You can review and edit the result before saving." />
              </h2>
              <p className="text-xs mb-3" style={{ color: "var(--color-muted)" }}>
                Tell the system what to change — e.g. "Add a step for checking environment variables" or "Make the error handling more defensive". The LLM will rewrite the skill and show you the result for approval.
              </p>
              <div className="flex gap-2">
                <textarea
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  placeholder="What should change about this skill?"
                  className="flex-1 text-sm p-3 rounded-lg border focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] resize-none"
                  style={{ borderColor: "var(--color-border)" }}
                  rows={2}
                />
                <button
                  onClick={handleFeedback}
                  disabled={feedbackLoading || !feedback.trim()}
                  className="self-end px-4 py-2.5 rounded-lg text-sm font-medium text-white flex items-center gap-1.5 disabled:opacity-50"
                  style={{ background: "var(--color-primary)" }}
                >
                  {feedbackLoading
                    ? <><Loader2 className="w-4 h-4 animate-spin" /> Revising...</>
                    : <><RotateCcw className="w-4 h-4" /> Revise</>
                  }
                </button>
              </div>

              {/* Revision result */}
              {revisedContent && (
                <div className="mt-3 p-3 rounded-lg border-l-4" style={{ background: "#f0fdf4", borderLeftColor: "var(--color-accent)" }}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--color-accent)" }}>
                      Revised version ready
                    </span>
                    <div className="flex gap-2">
                      <button
                        onClick={handleAcceptRevision}
                        disabled={saving}
                        className="flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium text-white"
                        style={{ background: "var(--color-accent)" }}
                      >
                        {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
                        Accept & Save
                      </button>
                      <button
                        onClick={() => setRevisedContent(null)}
                        className="flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium border"
                        style={{ borderColor: "var(--color-border)", color: "var(--color-muted)" }}
                      >
                        <X className="w-3 h-3" /> Discard
                      </button>
                    </div>
                  </div>
                  <p className="text-xs mb-2" style={{ color: "var(--color-muted)" }}>
                    The revised content is loaded in the editor above. You can edit it further before saving, or accept it directly.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right column */}
        <div className="space-y-4">
          {/* Info */}
          <div className="panel-surface">
            <h2 className="text-sm font-semibold mb-2">Details</h2>
            <dl className="space-y-1 text-xs">
              <div className="flex justify-between">
                <dt className="flex items-center" style={{ color: "var(--color-muted)" }}>
                  Category
                </dt>
                <dd>{skill.category}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="flex items-center" style={{ color: "var(--color-muted)" }}>
                  Generation
                  <InfoTip text="How many times this skill has been evolved. Generation 0 is the original bootstrap version." size={12} />
                </dt>
                <dd>{skill.generation}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="flex items-center" style={{ color: "var(--color-muted)" }}>
                  Score
                  <InfoTip text="Overall quality score (0-100%) based on a weighted combination of applied rate, completion rate, and fallback rate." size={12} />
                </dt>
                <dd className="font-semibold">{skill.score}%</dd>
              </div>
              <div className="flex justify-between"><dt style={{ color: "var(--color-muted)" }}>Created</dt><dd>{timeAgo(skill.created_at)}</dd></div>
            </dl>
          </div>

          {/* Lineage */}
          <div className="panel-surface">
            <h2 className="text-sm font-semibold mb-2">
              Version History
              <InfoTip text="The evolution lineage of this skill. Each version was created by a FIX (repair), DERIVED (enhancement), or CAPTURED (new pattern) evolution." />
            </h2>
            <div className="space-y-2">
              {(skill.lineage || []).map((v) => (
                <div
                  key={v.skill_id}
                  className={`text-xs p-2 rounded-lg border ${
                    v.skill_id === skill.skill_id ? "border-[var(--color-primary)] bg-orange-50" : ""
                  }`}
                  style={{ borderColor: v.skill_id === skill.skill_id ? "var(--color-primary)" : "var(--color-border)" }}
                >
                  <div className="flex items-center gap-1">
                    <span className="font-medium">v{v.generation + 1}</span>
                    <EvolutionTypeBadge type={v.lineage_origin} />
                    <span className={`px-1.5 py-0.5 rounded-full text-[10px] ${
                      v.status === "active" ? "bg-green-100 text-green-700"
                      : v.status === "pending" ? "bg-yellow-100 text-yellow-700"
                      : v.status === "rejected" ? "bg-red-100 text-red-700"
                      : "bg-gray-100 text-gray-600"
                    }`}>{v.status}</span>
                  </div>
                  <div className="mt-1" style={{ color: "var(--color-muted)" }}>{timeAgo(v.created_at)}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Judgments */}
          <div className="panel-surface">
            <h2 className="text-sm font-semibold mb-2">
              Recent Judgments
              <InfoTip text="After each task run, the system evaluates whether the agent actually followed this skill's instructions. 'Applied' means it did; 'Not applied' means it was selected but ignored." />
            </h2>
            {(skill.recent_judgments || []).length === 0 ? (
              <div className="text-xs" style={{ color: "var(--color-muted)" }}>No judgments yet</div>
            ) : (
              <div className="space-y-1.5">
                {skill.recent_judgments.map((j, i) => (
                  <div key={i} className="text-xs p-2 rounded-lg" style={{ background: "var(--color-bg-page)" }}>
                    <span className={j.skill_applied ? "text-green-600" : "text-red-600"}>
                      {j.skill_applied ? <><Check className="w-3 h-3 inline mr-0.5" />Applied</> : <><X className="w-3 h-3 inline mr-0.5" />Not applied</>}
                    </span>
                    {j.note && <span className="ml-2" style={{ color: "var(--color-muted)" }}>{j.note}</span>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
