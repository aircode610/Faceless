import api from "./client";
import type { OverviewData } from "./types";

export const fetchOverview = () => api.get<OverviewData>("/overview").then((r) => r.data);
