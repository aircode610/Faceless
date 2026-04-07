export interface Skill {
  skill_id: string;
  name: string;
  description: string;
  category: string;
  is_active: boolean;
  status: string;
  generation: number;
  lineage_origin: string;
  parent_id: string | null;
  content: string;
  total_selections: number;
  total_applied: number;
  total_completions: number;
  total_fallbacks: number;
  applied_rate: number;
  completion_rate: number;
  effective_rate: number;
  fallback_rate: number;
  score: number;
  created_at: string;
  last_updated: string;
}

export interface SkillDetail extends Skill {
  lineage: Skill[];
  recent_judgments: SkillJudgment[];
}

export interface ReviewItem extends Skill {
  content_diff: string | null;
  parent_content_snapshot: string | null;
  priority: string;
  pattern_key: string | null;
  recurrence_count: number;
  direction: string;
  evolution_type: string;
}

export interface FeatureRequest {
  id: string;
  run_id: string;
  capability: string;
  user_context: string;
  complexity: string;
  priority: string;
  recurrence_count: number;
  status: string;
  created_at: string;
  last_seen: string;
}

export interface RunSummary {
  id: string;
  task_description: string;
  execution_status: string;
  iterations: number;
  selected_skill_ids: string[];
  llm_task_completed: boolean;
  created_at: string;
}

export interface ConversationLine {
  role: string;
  content: string;
  iter: number;
  name?: string;
  success?: boolean;
}

export interface TrajectoryEntry {
  iter: number;
  tool: string;
  args: Record<string, unknown>;
  success: boolean;
  duration_ms: number;
}

export interface SkillJudgment {
  run_id: string;
  skill_id: string;
  skill_applied: number;
  note: string;
}

export interface EvolutionSuggestion {
  id: string;
  type: string;
  direction: string;
  priority: string;
  pattern_key: string;
}

export interface RunDetail extends RunSummary {
  conversation: ConversationLine[];
  trajectory: TrajectoryEntry[];
  skill_judgments: SkillJudgment[];
  evolution_suggestions: EvolutionSuggestion[];
  recording_dir: string;
}

export interface OverviewData {
  total_skills: number;
  avg_score: number;
  total_runs: number;
  pending_approvals: number;
  pipeline: { name: string; description: string }[];
  top_skills: Skill[];
  recent_runs: RunSummary[];
}

export interface AuditEntry {
  id: string;
  skill_id: string;
  action: string;
  reviewer: string;
  timestamp: string;
  note: string;
}
