import api from "./client";

export interface MCP {
  name: string;
  description: string;
  credentials_available?: boolean;
}

export interface JobLogEntry {
  ts: string;
  level: "info" | "llm" | "done" | "error";
  message: string;
  detail: string | null;
}

export interface Job {
  id: string;
  type: "bootstrap" | "run";
  status: "running" | "done" | "error";
  started_at: string;
  finished_at: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
  steps: { name: string; status: string }[];
  log?: JobLogEntry[];
  // bootstrap-specific
  description?: string;
  // run-specific
  task?: string;
}

export const getAgentStatus = () =>
  api.get<{ bootstrapped: boolean; config: Record<string, unknown> | null }>("/agent/status").then((r) => r.data);

export const getDefaultMCPs = () =>
  api.get<MCP[]>("/agent/mcps").then((r) => r.data);

export const startBootstrap = (description: string, mcps: MCP[]) =>
  api.post<{ job_id: string }>("/agent/bootstrap", { description, mcps }).then((r) => r.data);

export const startRun = (task: string) =>
  api.post<{ job_id: string }>("/agent/run", { task }).then((r) => r.data);

export const pollJob = (jobId: string) =>
  api.get<Job>(`/agent/jobs/${jobId}`).then((r) => r.data);
