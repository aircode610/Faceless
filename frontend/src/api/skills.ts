import api from "./client";
import type { Skill, SkillDetail } from "./types";

export const fetchSkills = (params?: Record<string, string>) =>
  api.get<{ items: Skill[]; count: number }>("/skills", { params }).then((r) => r.data);

export const fetchSkillDetail = (id: string) =>
  api.get<SkillDetail>(`/skills/${id}`).then((r) => r.data);

export const fetchSkillLineage = (id: string) =>
  api.get(`/skills/${id}/lineage`).then((r) => r.data);
