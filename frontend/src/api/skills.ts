import api from "./client";
import type { Skill, SkillDetail } from "./types";

export const fetchSkills = (params?: Record<string, string>) =>
  api.get<{ items: Skill[]; count: number }>("/skills", { params }).then((r) => r.data);

export const fetchSkillDetail = (id: string) =>
  api.get<SkillDetail>(`/skills/${id}`).then((r) => r.data);

export const fetchSkillLineage = (id: string) =>
  api.get(`/skills/${id}/lineage`).then((r) => r.data);

export const updateSkillContent = (id: string, content: string) =>
  api.put<Skill>(`/skills/${id}/content`, { content }).then((r) => r.data);

export const submitSkillFeedback = (id: string, feedback: string) =>
  api.post<{ original: string; revised: string }>(`/skills/${id}/feedback`, { feedback }).then((r) => r.data);
