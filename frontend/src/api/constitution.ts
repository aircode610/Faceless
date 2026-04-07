import api from "./client";

export const fetchConstitution = () =>
  api.get<{ content: string; version: number }>("/constitution").then((r) => r.data);

export const updateConstitution = (content: string, editor_id = "editor") =>
  api.put("/constitution", { content, editor_id }).then((r) => r.data);

export const fetchConstitutionHistory = () =>
  api.get<{ version: number; editor_id: string; timestamp: string; content: string }[]>(
    "/constitution/history"
  ).then((r) => r.data);
