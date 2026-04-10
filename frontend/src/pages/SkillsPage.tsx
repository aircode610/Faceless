import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchSkills } from "../api/skills";
import type { Skill } from "../api/types";
import EvolutionTypeBadge from "../components/EvolutionTypeBadge";
import InfoTip from "../components/InfoTip";
import { pct } from "../utils/format";

const FILTERS = ["all", "active", "pending", "superseded", "rejected"];
const SORTS = ["score", "updated", "selections"];

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("score");
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchSkills({
      active_only: filter === "active" || filter === "all" ? "false" : "false",
      sort,
      query: search,
    }).then((r) => {
      let items = r.items;
      if (filter !== "all") {
        items = items.filter((s) => s.status === filter);
      }
      setSkills(items);
    });
  }, [sort, search, filter]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-semibold">Skills Library</h1>
        <InfoTip text="Skills are reusable instructions injected into the agent's prompt. They evolve over time: BOOTSTRAP (initial), FIX (repaired), DERIVED (enhanced), CAPTURED (new pattern discovered)." />
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex gap-1">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded-lg text-sm capitalize transition-colors ${
                filter === f
                  ? "text-[var(--color-primary)] bg-orange-50 font-medium"
                  : "text-[var(--color-muted)] hover:text-[var(--color-ink)]"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="text-sm px-2 py-1 rounded-lg border"
          style={{ borderColor: "var(--color-border)" }}
        >
          {SORTS.map((s) => (
            <option key={s} value={s}>Sort: {s}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Search skills..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="text-sm px-3 py-1.5 rounded-lg border flex-1 max-w-xs"
          style={{ borderColor: "var(--color-border)" }}
        />
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {skills.map((s) => (
          <Link to={`/skills/${s.skill_id}`} key={s.skill_id} className="record-card no-underline block">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-medium text-sm">{s.name}</span>
              <span className="text-xs px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600">
                v{s.generation + 1}
              </span>
            </div>
            <div className="flex gap-1.5 mb-2">
              <span className="text-xs px-1.5 py-0.5 rounded-full bg-indigo-50 text-indigo-600">{s.category}</span>
              <EvolutionTypeBadge type={s.lineage_origin} />
            </div>
            <div className="text-xs line-clamp-2 mb-3" style={{ color: "var(--color-muted)" }}>
              {s.description}
            </div>
            {/* Rate bar */}
            <div className="flex items-center gap-2">
              <div className="flex-1 h-2 rounded-full bg-gray-100 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: pct(s.effective_rate),
                    background: s.effective_rate > 0.6 ? "var(--color-accent)" : "var(--color-primary)",
                  }}
                />
              </div>
              <span className="text-xs font-medium w-10 text-right">{s.score}%</span>
            </div>
            <div className="text-xs mt-1" style={{ color: "var(--color-muted)" }}>
              {s.total_selections} selections
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
