import { parseDiff } from "../utils/diffParser";

interface Props {
  diff: string | null;
  oldContent?: string | null;
  newContent?: string | null;
}

export default function DiffViewer({ diff, oldContent, newContent }: Props) {
  // If we have a unified diff, render it
  if (diff) {
    const lines = parseDiff(diff);
    return (
      <div className="font-mono text-xs overflow-x-auto rounded-lg border" style={{ borderColor: "var(--color-border)" }}>
        {lines.map((line, i) => (
          <div
            key={i}
            className="px-3 py-0.5"
            style={{
              background:
                line.type === "add" ? "var(--color-diff-add)"
                : line.type === "del" ? "var(--color-diff-del)"
                : line.type === "header" ? "var(--color-bg-page)"
                : "transparent",
              color: line.type === "header" ? "var(--color-muted)" : undefined,
            }}
          >
            <span className="inline-block w-5 text-right mr-2 select-none" style={{ color: "var(--color-muted)" }}>
              {line.type === "add" ? "+" : line.type === "del" ? "-" : " "}
            </span>
            {line.content}
          </div>
        ))}
      </div>
    );
  }

  // Side-by-side if we have old + new content
  if (oldContent || newContent) {
    return (
      <div className="grid grid-cols-2 gap-2">
        <div>
          <div className="text-xs font-medium mb-1" style={{ color: "var(--color-muted)" }}>Previous</div>
          <pre className="text-xs p-3 rounded-lg overflow-x-auto whitespace-pre-wrap" style={{ background: "var(--color-bg-page)" }}>
            {oldContent || "(no previous version)"}
          </pre>
        </div>
        <div>
          <div className="text-xs font-medium mb-1" style={{ color: "var(--color-muted)" }}>Proposed</div>
          <pre className="text-xs p-3 rounded-lg overflow-x-auto whitespace-pre-wrap" style={{ background: "var(--color-bg-page)" }}>
            {newContent || ""}
          </pre>
        </div>
      </div>
    );
  }

  return <div className="text-sm" style={{ color: "var(--color-muted)" }}>No diff available</div>;
}
