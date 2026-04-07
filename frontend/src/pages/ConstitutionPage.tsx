import { useEffect, useState } from "react";
import { fetchConstitution, updateConstitution, fetchConstitutionHistory } from "../api/constitution";

export default function ConstitutionPage() {
  const [content, setContent] = useState("");
  const [version, setVersion] = useState(0);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [history, setHistory] = useState<any[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    fetchConstitution().then((d) => {
      setContent(d.content);
      setVersion(d.version);
    });
  }, []);

  const handleSave = async () => {
    const result = await updateConstitution(draft);
    setContent(draft);
    setVersion(result.version);
    setEditing(false);
  };

  const loadHistory = async () => {
    const h = await fetchConstitutionHistory();
    setHistory(h);
    setShowHistory(true);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Constitution</h1>
          <div className="text-xs" style={{ color: "var(--color-muted)" }}>
            Version {version} · "These laws are absolute — the Many-Faced God demands it."
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadHistory}
            className="text-sm px-3 py-1.5 rounded-lg border hover:bg-gray-50"
            style={{ borderColor: "var(--color-border)" }}
          >
            History
          </button>
          {!editing ? (
            <button
              onClick={() => { setDraft(content); setEditing(true); }}
              className="text-sm px-3 py-1.5 rounded-lg text-white"
              style={{ background: "var(--color-primary)" }}
            >
              Edit
            </button>
          ) : (
            <div className="flex gap-2">
              <button onClick={handleSave} className="text-sm px-3 py-1.5 rounded-lg text-white" style={{ background: "var(--color-accent)" }}>Save</button>
              <button onClick={() => setEditing(false)} className="text-sm px-3 py-1.5 rounded-lg border" style={{ borderColor: "var(--color-border)" }}>Cancel</button>
            </div>
          )}
        </div>
      </div>

      <div className="panel-surface">
        {editing ? (
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="w-full min-h-[400px] text-sm p-4 rounded-lg border font-mono"
            style={{ borderColor: "var(--color-border)", background: "var(--color-bg-page)" }}
          />
        ) : (
          <pre className="text-sm whitespace-pre-wrap p-4 rounded-lg" style={{ background: "var(--color-bg-page)" }}>
            {content || "No constitution yet. Bootstrap an agent first."}
          </pre>
        )}
      </div>

      {showHistory && (
        <div className="panel-surface">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold">Version History</h2>
            <button onClick={() => setShowHistory(false)} className="text-xs" style={{ color: "var(--color-muted)" }}>Close</button>
          </div>
          <div className="space-y-2">
            {history.map((h) => (
              <div key={h.version} className="record-card">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm">Version {h.version}</span>
                  <span className="text-xs" style={{ color: "var(--color-muted)" }}>{h.editor_id} · {new Date(h.timestamp).toLocaleString()}</span>
                </div>
                <pre className="text-xs mt-2 whitespace-pre-wrap max-h-32 overflow-hidden" style={{ color: "var(--color-muted)" }}>
                  {h.content.slice(0, 200)}...
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
