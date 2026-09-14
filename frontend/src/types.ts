export interface TechStack {
  frontend: string;
  backend: string;
  database: string;
  ai: string;
}

export interface Architecture {
  description: string;
  components: string[];
}

export interface FileOperation {
  path: string;
  operation: 'create' | 'modify';
  content: string;
  before_content?: string | null;
}

export interface ValidationResult {
  status: 'passed' | 'failed';
  command: string;
  output: string;
  error?: string | null;
}

export interface TaskImplementationResult {
  status: 'success' | 'failed';
  task_id: string;
  summary: string;
  files_changed: string[];
  changes: FileOperation[];
  validation: ValidationResult;
  snapshot_id?: string | null;
}

export interface DevelopmentTask {
  id?: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low' | string;
  status?: 'pending' | 'implementing' | 'completed' | 'failed' | string;
  implementation_result?: TaskImplementationResult | null;
}

export interface Blueprint {
  summary: string;
  requirements: string[];
  tech_stack: TechStack;
  architecture: Architecture;
  development_tasks: DevelopmentTask[];
  next_steps: string[];
}

export interface StageData {
  name: string;
  label: string;
  status: 'pending' | 'running' | 'waiting_approval' | 'approved' | 'modified' | 'skipped' | 'failed' | string;
  output?: Record<string, any> | null;
  user_modifications?: Record<string, any> | null;
  guidance?: string | null;
  updated_at: string;
}

export interface Project {
  id: string;
  name: string;
  idea: string;
  status: 'created' | 'generating' | 'waiting_approval' | 'completed' | 'failed' | string;
  current_stage?: string;
  stages?: Record<string, StageData>;
  blueprint?: Blueprint | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreatePayload {
  name: string;
  idea: string;
}

export interface BlueprintResponse {
  project_id: string;
  status: string;
  blueprint: Blueprint;
}

export interface StageActionPayload {
  guidance?: string;
  modifications?: Record<string, any>;
}

export interface ScaffoldResponse {
  project_id: string;
  project_dir: string;
  files_created: string[];
  message: string;
}
