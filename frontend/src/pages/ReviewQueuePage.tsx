import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Check, X, ArrowRight } from "lucide-react";
import { fetchQueue, approveSkill, rejectSkill, fetchFeatures, acceptFeature, deferFeature, dismissFeature } from "../api/review";
import type { ReviewItem, FeatureRequest } from "../api/types";
import PriorityBadge from "../components/PriorityBadge";
import EvolutionTypeBadge from "../components/EvolutionTypeBadge";
import DiffViewer from "../components/DiffViewer";
import { timeAgo } from "../utils/format";

export default function ReviewQueuePage() {
  const [queue, setQueue] = useState<ReviewItem[]>([]);
  const [features, setFeatures] = useState<FeatureRequest[]>([]);
  const [selected, setSelected] = useState<ReviewItem | null>(null);
  const [toast, setToast] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const [showReject, setShowReject] = useState(false);

  const load = () => {
    fetchQueue().then(setQueue);
    fetchFeatures().then(setFeatures);
  };

  useEffect(() => { load(); }, []);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
  };

  const handleApprove = async () => {
    if (!selected) return;
    await approveSkill(selected.skill_id, { reviewer_id: "dashboard" });
    showToast(`Approved: ${selected.name}`);
    setSelected(null);
    load();
  };

  const handleReject = async () => {
    if (!selected || !rejectReason) return;
    await rejectSkill(selected.skill_id, { reviewer_id: "dashboard", reason: rejectReason });
    showToast(`Rejected: ${selected.name}`);
    setSelected(null);
    setShowReject(false);
    setRejectReason("");
    load();
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Review Queue</h1>

      {toast && (
        <div className="fixed top-4 right-4 z-50 px-4 py-2 rounded-lg bg-green-100 text-green-800 text-sm shadow-lg">
          {toast}
        </div>
      )}

      <div className="grid grid-cols-5 gap-6">
        {/* Left: queue list */}
        <div className="col-span-2 space-y-4">
          {/* Evolution items */}
          <div className="space-y-2">
            <h2 className="text-sm font-semibold" style={{ color: "var(--color-muted)" }}>
              Pending Evolutions ({queue.length})
            </h2>
            {queue.map((item) => (
              <div
                key={item.skill_id}
                onClick={() => setSelected(item)}
                className={`record-card cursor-pointer ${selected?.skill_id === item.skill_id ? "border-[var(--color-primary)]" : ""}`}
                style={selected?.skill_id === item.skill_id ? { borderColor: "var(--color-primary)" } : {}}
              >
                <div className="flex items-center gap-1.5 flex-wrap">
                  <PriorityBadge priority={item.priority || "medium"} />
                  <EvolutionTypeBadge type={item.evolution_type || "fix"} />
                  <span className="font-medium text-sm">{item.name}</span>
                  <span className="text-xs flex items-center gap-0.5" style={{ color: "var(--color-muted)" }}>
                    v{item.generation}<ArrowRight className="w-3 h-3" />v{item.generation + 1}
                  </span>
                </div>
                {item.pattern_key && (
                  <div className="text-[10px] font-mono mt-1" style={{ color: "var(--color-muted)" }}>{item.pattern_key}</div>
                )}
                {item.reason && (
                  <div className="text-xs mt-1.5 italic line-clamp-2" style={{ color: "var(--color-muted)" }}>
                    "{item.reason}"
                  </div>
                )}
                <div className="flex items-center gap-2 mt-1 text-xs" style={{ color: "var(--color-muted)" }}>
                  {item.recurrence_count >= 2 && (
                    <span className="text-orange-600 font-medium">Seen {item.recurrence_count}× ▲</span>
                  )}
                  <span>{timeAgo(item.created_at)}</span>
                </div>
              </div>
            ))}
            {queue.length === 0 && (
              <div className="text-sm py-4" style={{ color: "var(--color-muted)" }}>
                No pending evolutions. Valar Dohaeris.
              </div>
            )}
          </div>

          {/* Feature requests */}
          <div className="space-y-2">
            <h2 className="text-sm font-semibold" style={{ color: "var(--color-muted)" }}>
              Feature Requests ({features.filter((f) => f.status === "pending").length})
            </h2>
            {features.filter((f) => f.status === "pending").map((feat) => (
              <div key={feat.id} className="record-card">
                <div className="text-sm font-medium">{feat.capability}</div>
                <div className="text-xs mt-1" style={{ color: "var(--color-muted)" }}>{feat.user_context}</div>
                <div className="flex items-center gap-2 mt-2 text-xs" style={{ color: "var(--color-muted)" }}>
                  <span className="px-1.5 py-0.5 rounded bg-gray-100">{feat.complexity}</span>
                  <span>{timeAgo(feat.created_at)}</span>
                </div>
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={() => acceptFeature(feat.id).then(load)}
                    className="text-xs px-2 py-1 rounded bg-green-100 text-green-700 hover:bg-green-200"
                  >Accept</button>
                  <button
                    onClick={() => deferFeature(feat.id).then(load)}
                    className="text-xs px-2 py-1 rounded bg-yellow-100 text-yellow-700 hover:bg-yellow-200"
                  >Defer</button>
                  <button
                    onClick={() => dismissFeature(feat.id, "Not needed").then(load)}
                    className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-600 hover:bg-gray-200"
                  >Dismiss</button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: detail panel */}
        <div className="col-span-3">
          {selected ? (
            <div className="panel-surface space-y-4">
              <div className="flex items-center gap-2">
                <PriorityBadge priority={selected.priority || "medium"} />
                <EvolutionTypeBadge type={selected.evolution_type || "fix"} />
                <span className="font-semibold">{selected.name}</span>
              </div>

              {/* Reason — WHY this evolution, grounded in trace evidence */}
              {selected.reason && (
                <div
                  className="p-3 rounded-lg border-l-4"
                  style={{
                    background: "#fef7f0",
                    borderLeftColor: "var(--color-primary)",
                  }}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-semibold uppercase tracking-wide"
                          style={{ color: "var(--color-primary)" }}>
                      Why this change?
                    </span>
                    {selected.source_run_id && (
                      <Link
                        to={`/runs/${selected.source_run_id}`}
                        className="text-[10px] px-1.5 py-0.5 rounded-full bg-white border hover:bg-gray-50"
                        style={{ borderColor: "var(--color-border)", color: "var(--color-muted)" }}
                      >
                        view source run <ArrowRight className="w-3 h-3 inline" />
                      </Link>
                    )}
                  </div>
                  <div className="text-sm leading-relaxed" style={{ color: "var(--color-ink)" }}>
                    {selected.reason}
                  </div>
                </div>
              )}

              {selected.direction && (
                <div className="text-sm p-3 rounded-lg" style={{ background: "var(--color-bg-page)" }}>
                  <span className="font-medium">Direction:</span> {selected.direction}
                </div>
              )}

              {/* Diff */}
              <div>
                <h3 className="text-sm font-semibold mb-2">Changes</h3>
                <DiffViewer
                  diff={selected.content_diff}
                  oldContent={selected.parent_content_snapshot}
                  newContent={selected.content}
                />
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-2 border-t" style={{ borderColor: "var(--color-border)" }}>
                <button
                  onClick={handleApprove}
                  className="px-4 py-2 rounded-lg text-sm font-medium text-white flex items-center gap-1.5"
                  style={{ background: "var(--color-accent)" }}
                >
                  <Check className="w-4 h-4" /> Approve
                </button>
                <button
                  onClick={() => setShowReject(true)}
                  className="px-4 py-2 rounded-lg text-sm font-medium text-white flex items-center gap-1.5"
                  style={{ background: "var(--color-danger)" }}
                >
                  <X className="w-4 h-4" /> Reject
                </button>
              </div>

              {showReject && (
                <div className="p-3 rounded-lg border" style={{ borderColor: "var(--color-danger)" }}>
                  <textarea
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Rejection reason..."
                    className="w-full text-sm p-2 rounded border mb-2"
                    style={{ borderColor: "var(--color-border)" }}
                    rows={2}
                  />
                  <div className="flex gap-2">
                    <button onClick={handleReject} className="text-xs px-3 py-1 rounded bg-red-100 text-red-700">Confirm Reject</button>
                    <button onClick={() => setShowReject(false)} className="text-xs px-3 py-1 rounded bg-gray-100 text-gray-600">Cancel</button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="panel-surface text-center py-12" style={{ color: "var(--color-muted)" }}>
              <img src="/faceless.svg" alt="" className="w-12 h-12 mx-auto mb-2 opacity-40" />
              <div className="text-sm">Select an item from the queue to review</div>
              <div className="text-xs mt-1">"A man must wait."</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
