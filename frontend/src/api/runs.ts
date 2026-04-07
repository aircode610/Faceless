import api from "./client";
import type { RunSummary, RunDetail } from "./types";

export const fetchRuns = (params?: Record<string, string>) =>
  api.get<{ items: RunSummary[]; count: number }>("/runs", { params }).then((r) => r.data);

export const fetchRunDetail = (id: string) =>
  api.get<RunDetail>(`/runs/${id}`).then((r) => r.data);
