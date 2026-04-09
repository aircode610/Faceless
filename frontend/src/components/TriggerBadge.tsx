const TRIGGER_INFO: Record<string, { label: string; hint: string; cls: string }> = {
  trigger1: {
    label: "Post-Execution",
    hint: "Suggested by the LLM after analyzing a task run",
    cls: "bg-indigo-50 text-indigo-700 border-indigo-200",
  },
  trigger2: {
    label: "Tool Degradation",
    hint: "A tool this skill depends on is failing frequently",
    cls: "bg-orange-50 text-orange-700 border-orange-200",
  },
  trigger3: {
    label: "Health Check",
    hint: "Periodic review flagged poor skill metrics (low completion or high fallback rate)",
    cls: "bg-rose-50 text-rose-700 border-rose-200",
  },
};

export default function TriggerBadge({ trigger }: { trigger: string }) {
  const info = TRIGGER_INFO[trigger] || TRIGGER_INFO.trigger1;
  return (
    <span
      title={info.hint}
      className={`px-2 py-0.5 rounded-full text-xs font-medium border cursor-help ${info.cls}`}
    >
      {info.label}
    </span>
  );
}
