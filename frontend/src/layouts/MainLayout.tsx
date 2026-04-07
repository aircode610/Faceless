import { NavLink, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";
import { fetchQueue } from "../api/review";

export default function MainLayout() {
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    const load = () => fetchQueue().then((q) => setPendingCount(q.length)).catch(() => {});
    load();
    const interval = setInterval(load, 30_000);
    return () => clearInterval(interval);
  }, []);

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? "text-[var(--color-primary)] bg-orange-50"
        : "text-[var(--color-muted)] hover:text-[var(--color-ink)]"
    }`;

  return (
    <div className="min-h-screen" style={{ background: "var(--color-bg-page)" }}>
      {/* Nav */}
      <nav
        className="sticky top-0 z-50 border-b px-6 py-3 flex items-center gap-6"
        style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
      >
        <NavLink to="/dashboard" className="flex items-center gap-2 mr-4">
          <span className="text-lg">🎭</span>
          <span className="font-semibold text-sm">Faceless</span>
        </NavLink>

        <NavLink to="/dashboard" className={linkClass}>Dashboard</NavLink>
        <NavLink to="/skills" className={linkClass}>Skills</NavLink>
        <NavLink to="/runs" className={linkClass}>Runs</NavLink>
        <NavLink to="/review" className={linkClass}>
          Review
          {pendingCount > 0 && (
            <span className="ml-1.5 px-1.5 py-0.5 text-xs rounded-full bg-red-100 text-red-600 font-bold">
              {pendingCount}
            </span>
          )}
        </NavLink>
        <NavLink to="/constitution" className={linkClass}>Constitution</NavLink>
      </nav>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-6 py-6">
        <Outlet />
      </main>
    </div>
  );
}
