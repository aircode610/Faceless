const TYPES: Record<string, { cls: string; hint: string }> = {
  fix: {
    cls: "bg-blue-100 text-blue-700 border-blue-200",
    hint: "A broken or outdated skill was repaired in place",
  },
  derived: {
    cls: "bg-teal-100 text-teal-700 border-teal-200",
    hint: "An enhanced version was created from an existing skill",
  },
  captured: {
    cls: "bg-green-100 text-green-700 border-green-200",
    hint: "A brand-new skill was extracted from a novel pattern the agent discovered",
  },
  BOOTSTRAP: {
    cls: "bg-purple-100 text-purple-700 border-purple-200",
    hint: "Original skill created during agent setup",
  },
  FIXED: {
    cls: "bg-blue-100 text-blue-700 border-blue-200",
    hint: "A broken or outdated skill was repaired in place",
  },
  DERIVED: {
    cls: "bg-teal-100 text-teal-700 border-teal-200",
    hint: "An enhanced version was created from an existing skill",
  },
  CAPTURED: {
    cls: "bg-green-100 text-green-700 border-green-200",
    hint: "A brand-new skill was extracted from a novel pattern the agent discovered",
  },
  ROLLBACK: {
    cls: "bg-amber-100 text-amber-700 border-amber-200",
    hint: "Reverted to a previous version of this skill",
  },
};

export default function EvolutionTypeBadge({ type }: { type: string }) {
  const info = TYPES[type] || { cls: "bg-gray-100 text-gray-600 border-gray-200", hint: "" };
  return (
    <span
      title={info.hint}
      className={`px-2 py-0.5 rounded-full text-xs font-medium border cursor-help ${info.cls}`}
    >
      {type.toUpperCase()}
    </span>
  );
}
