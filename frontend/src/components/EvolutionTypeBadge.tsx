const COLORS: Record<string, string> = {
  fix: "bg-blue-100 text-blue-700 border-blue-200",
  derived: "bg-teal-100 text-teal-700 border-teal-200",
  captured: "bg-green-100 text-green-700 border-green-200",
  BOOTSTRAP: "bg-purple-100 text-purple-700 border-purple-200",
  FIXED: "bg-blue-100 text-blue-700 border-blue-200",
  DERIVED: "bg-teal-100 text-teal-700 border-teal-200",
  CAPTURED: "bg-green-100 text-green-700 border-green-200",
  ROLLBACK: "bg-amber-100 text-amber-700 border-amber-200",
};

export default function EvolutionTypeBadge({ type }: { type: string }) {
  const cls = COLORS[type] || "bg-gray-100 text-gray-600 border-gray-200";
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${cls}`}>
      {type.toUpperCase()}
    </span>
  );
}
