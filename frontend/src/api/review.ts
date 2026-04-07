import api from "./client";
import type { ReviewItem, FeatureRequest } from "./types";

export const fetchQueue = () =>
  api.get<ReviewItem[]>("/review/queue").then((r) => r.data);

export const fetchReviewDetail = (id: string) =>
  api.get<ReviewItem>(`/review/${id}`).then((r) => r.data);

export const approveSkill = (id: string, body: { reviewer_id?: string; reason?: string; edited_content?: string }) =>
  api.post(`/review/${id}/approve`, body).then((r) => r.data);

export const rejectSkill = (id: string, body: { reviewer_id?: string; reason: string }) =>
  api.post(`/review/${id}/reject`, body).then((r) => r.data);

export const fetchFeatures = () =>
  api.get<FeatureRequest[]>("/review/features").then((r) => r.data);

export const acceptFeature = (id: string) =>
  api.post(`/review/features/${id}/accept`).then((r) => r.data);

export const deferFeature = (id: string) =>
  api.post(`/review/features/${id}/defer`).then((r) => r.data);

export const dismissFeature = (id: string, reason: string) =>
  api.post(`/review/features/${id}/dismiss`, { reason }).then((r) => r.data);
