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

export interface TestResult {
  status: 'not_run' | 'running' | 'passed' | 'failed' | 'timeout' | 'no_tests' | 'blocked' | 'error';
  exit_code?: number | null;
  stdout: string;
  stderr: string;
  duration_seconds: number;
  tests_total: number;
  tests_passed: number;
  tests_failed: number;
  tests_skipped: number;
  failure_summary?: string | null;
}

export interface FailureAnalysis {
  root_cause: string;
  affected_files: string[];
  explanation: string;
  proposed_fix: string;
  confidence: number;
}

export interface RepairAttempt {
  attempt_number: number;
  snapshot_id?: string | null;
  summary: string;
  changes: FileOperation[];
  validation: ValidationResult;
  test_result: TestResult;
  failure_analysis?: FailureAnalysis | null;
}

export interface MissionLogEntry {
  timestamp: string;
  level: 'info' | 'success' | 'warning' | 'error';
  stage: string;
  message: string;
}

export interface TaskImplementationResult {
  status: 'success' | 'verified' | 'completed' | 'failed';
  task_id: string;
  summary: string;
  files_changed: string[];
  changes: FileOperation[];
  validation: ValidationResult;
  snapshot_id?: string | null;
  test_result?: TestResult | null;
  repair_attempts?: RepairAttempt[];
  mission_logs?: MissionLogEntry[];
  verified?: boolean;
  security_checks?: Record<string, boolean>;
}

export interface DevelopmentTask {
  id?: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low' | string;
  depends_on?: string[];
  status?: 'pending' | 'inspecting' | 'implementing' | 'validating' | 'testing' | 'repairing' | 'completed' | 'verified' | 'failed' | string;
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
  package_metadata?: DeliveryPackageMetadata | null;
  publishing_history?: PublishingHistoryEntry[];
  mission_state?: MissionState | null;
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

export interface DeliveryPackageMetadata {
  project_id: string;
  project_name: string;
  package_filename: string;
  package_path: string;
  package_size_bytes: number;
  sha256_checksum: string;
  files_count: number;
  verification_status: 'verified' | 'completed' | 'unverified' | 'failed' | string;
  created_at: string;
  download_url: string;
}

export interface VerificationSummary {
  total_tasks: number;
  verified_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  pending_tasks: number;
  tests_discovered: number;
  tests_passed: number;
  tests_failed: number;
  pass_rate_percent: number;
  status: 'verified' | 'completed' | 'unverified' | 'failed' | string;
}

export interface MissionReport {
  project_id: string;
  project_name: string;
  idea: string;
  status: string;
  current_stage?: string | null;
  stages_summary: Record<string, any>;
  blueprint_summary?: Record<string, any> | null;
  verification_summary: VerificationSummary;
  security_audit: Record<string, boolean>;
  files_modified: string[];
  package_metadata?: DeliveryPackageMetadata | null;
  generated_at: string;
  recommended_next_steps: string[];
  tagline: string;
}

export interface RemoteConfig {
  name: string;
  fetch_url: string;
  push_url: string;
}

export interface GitFileChange {
  path: string;
  status: 'modified' | 'added' | 'deleted' | 'untracked' | 'renamed' | 'conflicted' | string;
  is_staged: boolean;
  has_secret_risk: boolean;
  risk_reason?: string | null;
}

export interface GitStatusResponse {
  git_installed: boolean;
  initialized: boolean;
  branch?: string | null;
  head_commit?: string | null;
  is_clean: boolean;
  is_detached: boolean;
  changes: GitFileChange[];
  remotes: RemoteConfig[];
  ahead_count: number;
  behind_count: number;
  diverged: boolean;
  error?: string | null;
}

export interface GitDiffResponse {
  diff: string;
  truncated: boolean;
  file_count: number;
}

export interface GitCommitResponse {
  success: boolean;
  commit_hash?: string | null;
  branch?: string | null;
  files_committed: string[];
  message: string;
}

export interface GitPushResponse {
  success: boolean;
  remote_name: string;
  branch_name: string;
  commit_hash?: string | null;
  message: string;
  error_detail?: string | null;
}

export interface PublishingHistoryEntry {
  id: string;
  project_id: string;
  commit_hash?: string | null;
  commit_message: string;
  branch: string;
  remote_name?: string | null;
  files_committed: string[];
  verification_status: string;
  push_status: 'committed_local' | 'pushed' | 'push_failed' | string;
  timestamp: string;
  error_detail?: string | null;
}

// --- Slice 7: Autonomous Multi-Task Mission Types ---

export type MissionStatus = 'ready' | 'running' | 'paused' | 'blocked' | 'failed' | 'cancelled' | 'completed';
export type TaskExecutionState = 'pending' | 'eligible' | 'running' | 'verified' | 'failed' | 'blocked' | 'skipped';

export interface TaskPlanItem {
  task_id: string;
  title: string;
  priority: string;
  depends_on: string[];
  state: TaskExecutionState;
  order_index: number;
  blocked_by: string[];
}

export interface ExecutionPlan {
  project_id: string;
  project_name: string;
  is_valid: boolean;
  total_tasks: number;
  execution_order: string[];
  tasks: TaskPlanItem[];
  has_cycles: boolean;
  missing_dependencies: Record<string, string[]>;
  validation_errors: string[];
}

export interface TaskProgressItem {
  task_id: string;
  title: string;
  status: string;
  depends_on: string[];
  verified: boolean;
  snapshot_id?: string | null;
  tests_passed: number;
  tests_total: number;
  repair_attempts_count: number;
  error_message?: string | null;
}

export interface MissionState {
  project_id: string;
  status: MissionStatus;
  current_task_id?: string | null;
  current_task_title?: string | null;
  execution_order: string[];
  completed_task_ids: string[];
  failed_task_ids: string[];
  blocked_task_ids: string[];
  skipped_task_ids: string[];
  tasks_progress: Record<string, TaskProgressItem>;
  active_worker_id?: string | null;
  error_message?: string | null;
  started_at?: string | null;
  updated_at?: string | null;
  completed_at?: string | null;
}

export interface MissionExecutionReport {
  project_id: string;
  project_name: string;
  status: MissionStatus;
  total_tasks: number;
  completed_count: number;
  failed_count: number;
  blocked_count: number;
  skipped_count: number;
  duration_seconds: number;
  tasks: TaskProgressItem[];
  started_at?: string | null;
  completed_at?: string | null;
  summary: string;
}


