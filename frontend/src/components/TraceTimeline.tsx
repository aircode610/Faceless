import type { ConversationLine } from "../api/types";

interface Props {
  conversation: ConversationLine[];
}

const ROLE_COLORS: Record<string, string> = {
  user: "text-gray-700",
  assistant: "text-blue-700",
  tool_call: "text-green-700",
  tool_result: "text-green-600",
};

const DOT_COLORS: Record<string, string> = {
  user: "bg-gray-400",
  assistant: "bg-blue-500",
  tool_call: "bg-green-500",
  tool_result: "bg-green-400",
};

export default function TraceTimeline({ conversation }: Props) {
  return (
    <div className="space-y-1">
      {conversation.map((line, i) => {
        const isComplete = line.role === "assistant" && line.content?.includes("<COMPLETE>");
        return (
          <div key={i} className="flex items-start gap-3 py-1.5">
            <div className="flex items-center gap-2 shrink-0 w-24">
              <div className={`w-2 h-2 rounded-full ${DOT_COLORS[line.role] || "bg-gray-300"}`} />
              <span className="text-xs font-mono" style={{ color: "var(--color-muted)" }}>
                iter {line.iter}
              </span>
            </div>
            <span className={`text-xs font-medium w-20 shrink-0 ${ROLE_COLORS[line.role] || ""}`}>
              [{line.role}]
            </span>
            <div className={`text-sm flex-1 ${isComplete ? "font-bold text-green-700" : ""}`}>
              {line.name && <span className="font-mono text-xs mr-1">{line.name}</span>}
              {typeof line.success === "boolean" && (
                <span className={line.success ? "text-green-600" : "text-red-600"}>
                  {line.success ? " ✓" : " ✗"}
                </span>
              )}
              <span className="text-gray-700 break-all">
                {(line.content || "").slice(0, 300)}
                {(line.content || "").length > 300 ? "..." : ""}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
