import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Check, X } from "lucide-react";
import { fetchSkillDetail } from "../api/skills";
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

  useEffect(() => {
    if (skillId) fetchSkillDetail(skillId).then(setSkill);
  }, [skillId]);

  if (!skill) return <div className="text-center py-12" style={{ color: "var(--color-muted)" }}>Loading...</div>;

  const metrics = [
    { label: "Applied Rate", value: skill.applied_rate, color: "var(--color-accent)" },
    { label: "Completion Rate", value: skill.completion_rate, color: "var(--color-primary)" },
    { label: "Effective Rate", value: skill.effective_rate, color: "#6366f1" },
    { label: "Fallback Rate", value: skill.fallback_rate, color: "var(--color-danger)" },
  ];

  return (
    <div className="space-y-6">
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

          {/* Content */}
          <div className="panel-surface">
            <h2 className="text-sm font-semibold mb-3">
              SKILL.md
              <InfoTip text="The full skill definition file. Contains instructions, procedures, and context that get injected into the agent's prompt when this skill is selected." />
            </h2>
            <pre className="text-xs whitespace-pre-wrap p-4 rounded-lg overflow-x-auto" style={{ background: "var(--color-bg-page)" }}>
              {skill.content}
            </pre>
          </div>
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
