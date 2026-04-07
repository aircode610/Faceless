export interface DiffLine {
  type: "add" | "del" | "context" | "header";
  content: string;
  oldLine?: number;
  newLine?: number;
}

export function parseDiff(diff: string): DiffLine[] {
  if (!diff) return [];
  const lines = diff.split("\n");
  const result: DiffLine[] = [];
  let oldLine = 0;
  let newLine = 0;

  for (const line of lines) {
    if (line.startsWith("@@")) {
      const match = line.match(/@@ -(\d+)/);
      if (match) {
        oldLine = parseInt(match[1]) - 1;
        newLine = parseInt(match[1]) - 1;
      }
      result.push({ type: "header", content: line });
    } else if (line.startsWith("+")) {
      newLine++;
      result.push({ type: "add", content: line.slice(1), newLine });
    } else if (line.startsWith("-")) {
      oldLine++;
      result.push({ type: "del", content: line.slice(1), oldLine });
    } else {
      oldLine++;
      newLine++;
      result.push({ type: "context", content: line.startsWith(" ") ? line.slice(1) : line, oldLine, newLine });
    }
  }
  return result;
}
