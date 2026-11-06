import { 
  Project, 
  ProjectCreatePayload, 
  BlueprintResponse, 
  StageData,
  ScaffoldResponse,
  TaskImplementationResult,
  DeliveryPackageMetadata,
  MissionReport,
  GitStatusResponse,
  GitDiffResponse,
  GitCommitResponse,
  GitPushResponse,
  RemoteConfig,
  PublishingHistoryEntry,
  ExecutionPlan,
  MissionState,
  MissionExecutionReport,
  ParallelExecutionPlan,
  ParallelMissionState,
  ParallelMissionReport,
  ProjectStackDetection,
  DeploymentReadinessReport,
  DeploymentPlan,
  DeploymentRecord,
  DeploymentState,
  DeploymentPlatform
} from '../types';

const BASE_URL = '/api';

export class RogersApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = 'RogersApiError';
    this.status = status;
  }
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });
  } catch {
    throw new RogersApiError(
      'Unable to connect to ROGERS backend service. Please check if the server is running.',
      0
    );
  }

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errorData = await response.json();
      if (typeof errorData.detail === 'string') {
        errorDetail = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        errorDetail = errorData.detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ');
      }
    } catch {
      // fallback
    }
    throw new RogersApiError(errorDetail, response.status);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

/** Creates a new project with given name and idea description. */
export async function createProject(payload: ProjectCreatePayload): Promise<Project> {
  return request<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/** Triggers blueprint orchestration for an existing project (Slice 1 compatibility). */
export async function generateBlueprint(projectId: string): Promise<BlueprintResponse> {
  return request<BlueprintResponse>(`/projects/${projectId}/blueprint`, {
    method: 'POST',
  });
}

/** Fetches project details. */
export async function getProject(projectId: string): Promise<Project> {
  return request<Project>(`/projects/${projectId}`);
}

/** Fetches all projects. */
export async function listProjects(): Promise<Project[]> {
  return request<Project[]>('/projects');
}

/** Deletes a project. */
export async function deleteProject(projectId: string): Promise<void> {
  return request<void>(`/projects/${projectId}`, {
    method: 'DELETE',
  });
}

/** Runs or regenerates a specific stage with optional guidance. */
export async function runStage(
  projectId: string, 
  stageName: string, 
  guidance?: string
): Promise<StageData> {
  return request<StageData>(`/projects/${projectId}/stages/${stageName}/run`, {
    method: 'POST',
    body: JSON.stringify({ guidance }),
  });
}

/** Approves a stage and advances to the next. */
export async function approveStage(projectId: string, stageName: string): Promise<StageData> {
  return request<StageData>(`/projects/${projectId}/stages/${stageName}/approve`, {
    method: 'POST',
  });
}

/** Submits human modifications to a stage output. */
export async function modifyStage(
  projectId: string, 
  stageName: string, 
  modifications: Record<string, any>
): Promise<StageData> {
  return request<StageData>(`/projects/${projectId}/stages/${stageName}/modify`, {
    method: 'POST',
    body: JSON.stringify({ modifications }),
  });
}

/** Runs all stages automatically end-to-end. */
export async function runAllStages(projectId: string): Promise<Project> {
  return request<Project>(`/projects/${projectId}/run-all`, {
    method: 'POST',
  });
}

/** Generates physical project scaffolding files on disk. */
export async function scaffoldProject(projectId: string): Promise<ScaffoldResponse> {
  return request<ScaffoldResponse>(`/projects/${projectId}/scaffold`, {
    method: 'POST',
  });
}

/** Executes code implementation for a specific development task. */
export async function implementTask(
  projectId: string,
  taskId: string
): Promise<TaskImplementationResult> {
  return request<TaskImplementationResult>(`/projects/${projectId}/tasks/${taskId}/implement`, {
    method: 'POST',
  });
}

/** Restores previous file versions from a task snapshot. */
export async function restoreTask(
  projectId: string,
  taskId: string
): Promise<{ message: string; status: string }> {
  return request<{ message: string; status: string }>(`/projects/${projectId}/tasks/${taskId}/restore`, {
    method: 'POST',
  });
}

/** Packages the scaffolded and verified project into a clean delivery archive. */
export async function createDeliveryPackage(projectId: string): Promise<DeliveryPackageMetadata> {
  return request<DeliveryPackageMetadata>(`/projects/${projectId}/package`, {
    method: 'POST',
  });
}

/** Retrieves the comprehensive final mission report for a project. */
export async function getMissionReport(projectId: string): Promise<MissionReport> {
  return request<MissionReport>(`/projects/${projectId}/mission-report`);
}

/** Returns the direct download URL for the project delivery package. */
export function getDownloadPackageUrl(projectId: string): string {
  return `${BASE_URL}/projects/${projectId}/package/download`;
}

/** Fetches current Git status for the generated project. */
export async function getGitStatus(projectId: string): Promise<GitStatusResponse> {
  return request<GitStatusResponse>(`/projects/${projectId}/git/status`);
}

/** Initializes a Git repository in the generated project. */
export async function initGitRepo(projectId: string, defaultBranch: string = 'main'): Promise<GitStatusResponse> {
  return request<GitStatusResponse>(`/projects/${projectId}/git/init`, {
    method: 'POST',
    body: JSON.stringify({ default_branch: defaultBranch }),
  });
}

/** Retrieves bounded Git diff of changes. */
export async function getGitDiff(projectId: string): Promise<GitDiffResponse> {
  return request<GitDiffResponse>(`/projects/${projectId}/git/diff`);
}

/** Commits explicitly approved files with a message. */
export async function commitGitChanges(
  projectId: string,
  message: string,
  approvedFiles: string[]
): Promise<GitCommitResponse> {
  return request<GitCommitResponse>(`/projects/${projectId}/git/commit`, {
    method: 'POST',
    body: JSON.stringify({ message, approved_files: approvedFiles }),
  });
}

/** Adds or updates a Git remote for the project. */
export async function addGitRemote(projectId: string, name: string, url: string): Promise<RemoteConfig> {
  return request<RemoteConfig>(`/projects/${projectId}/git/remote`, {
    method: 'POST',
    body: JSON.stringify({ name, url }),
  });
}

/** Pushes verified commits to the configured remote. */
export async function pushGitCommit(
  projectId: string,
  remoteName: string = 'origin',
  branchName?: string,
  autoPublish: boolean = false
): Promise<GitPushResponse> {
  return request<GitPushResponse>(`/projects/${projectId}/git/push`, {
    method: 'POST',
    body: JSON.stringify({
      remote_name: remoteName,
      branch_name: branchName,
      auto_publish: autoPublish,
    }),
  });
}

/** Fetches the publishing audit history for the project. */
export async function getPublishingHistory(projectId: string): Promise<PublishingHistoryEntry[]> {
  return request<PublishingHistoryEntry[]>(`/projects/${projectId}/git/publishing-history`);
}

// --- Slice 7: Autonomous Multi-Task Mission API ---

/** Previews and validates the task dependency execution plan. */
export async function getMissionPlan(projectId: string): Promise<ExecutionPlan> {
  return request<ExecutionPlan>(`/projects/${projectId}/mission/plan`);
}

/** Fetches the live or persisted mission status and task-level progress. */
export async function getMissionStatus(projectId: string): Promise<MissionState> {
  return request<MissionState>(`/projects/${projectId}/mission/status`);
}

/** Starts multi-task execution for the project. */
export async function startMission(projectId: string): Promise<MissionState> {
  return request<MissionState>(`/projects/${projectId}/mission/start`, {
    method: 'POST',
  });
}

/** Safely pauses active mission execution at the task boundary. */
export async function pauseMission(projectId: string): Promise<MissionState> {
  return request<MissionState>(`/projects/${projectId}/mission/pause`, {
    method: 'POST',
  });
}

/** Resumes execution from last completed task checkpoint. */
export async function resumeMission(projectId: string): Promise<MissionState> {
  return request<MissionState>(`/projects/${projectId}/mission/resume`, {
    method: 'POST',
  });
}

/** Cancels mission execution. */
export async function cancelMission(projectId: string): Promise<MissionState> {
  return request<MissionState>(`/projects/${projectId}/mission/cancel`, {
    method: 'POST',
  });
}

/** Retrieves comprehensive final multi-task mission report. */
export async function getMissionExecutionReport(projectId: string): Promise<MissionExecutionReport> {
  return request<MissionExecutionReport>(`/projects/${projectId}/mission/report`);
}

// --- Slice 8: Multi-Agent Parallel Execution API ---

/** Previews parallel execution batches and task distribution. */
export async function getParallelPlan(projectId: string): Promise<ParallelExecutionPlan> {
  return request<ParallelExecutionPlan>(`/projects/${projectId}/parallel/plan`);
}

/** Fetches live parallel multi-agent state, active agents, and locked files. */
export async function getParallelStatus(projectId: string): Promise<ParallelMissionState> {
  return request<ParallelMissionState>(`/projects/${projectId}/parallel/status`);
}

/** Starts parallel multi-agent mission with configurable concurrency. */
export async function startParallelMission(projectId: string, maxConcurrentAgents: number = 3): Promise<ParallelMissionState> {
  return request<ParallelMissionState>(`/projects/${projectId}/parallel/start`, {
    method: 'POST',
    body: JSON.stringify({ action: 'start', max_concurrent_agents: maxConcurrentAgents }),
  });
}

/** Safely pauses parallel mission agents. */
export async function pauseParallelMission(projectId: string): Promise<ParallelMissionState> {
  return request<ParallelMissionState>(`/projects/${projectId}/parallel/pause`, {
    method: 'POST',
  });
}

/** Resumes paused parallel multi-agent mission. */
export async function resumeParallelMission(projectId: string): Promise<ParallelMissionState> {
  return request<ParallelMissionState>(`/projects/${projectId}/parallel/resume`, {
    method: 'POST',
  });
}

/** Cancels active parallel multi-agent mission. */
export async function cancelParallelMission(projectId: string): Promise<ParallelMissionState> {
  return request<ParallelMissionState>(`/projects/${projectId}/parallel/cancel`, {
    method: 'POST',
  });
}

/** Fetches comprehensive final parallel mission report. */
export async function getParallelReport(projectId: string): Promise<ParallelMissionReport> {
  return request<ParallelMissionReport>(`/projects/${projectId}/parallel/report`);
}


// ============================================================
// SLICE 9: INTELLIGENT DEPLOYMENT AUTOMATION API
// ============================================================

/** Detects the technology stack of a project's generated workspace. */
export async function detectDeploymentStack(projectId: string): Promise<ProjectStackDetection> {
  return request<ProjectStackDetection>(`/projects/${projectId}/deployment/detect`);
}

/** Evaluates deployment readiness: secrets, structure, testing, and git status. */
export async function assessDeploymentReadiness(projectId: string): Promise<DeploymentReadinessReport> {
  return request<DeploymentReadinessReport>(`/projects/${projectId}/deployment/readiness`);
}

/** Generates a deployment plan for the specified platform. */
export async function generateDeploymentPlan(
  projectId: string,
  platform: DeploymentPlatform = 'docker',
  targetPort?: number,
  healthCheckPath?: string,
  envVars?: Record<string, string>
): Promise<DeploymentPlan> {
  return request<DeploymentPlan>(`/projects/${projectId}/deployment/plan`, {
    method: 'POST',
    body: JSON.stringify({
      platform,
      target_port: targetPort,
      health_check_path: healthCheckPath,
      env_vars: envVars
    })
  });
}

/** Mandatory human approval gate: approves a generated deployment plan. */
export async function approveDeploymentPlan(
  projectId: string,
  approvedBy: string = 'Commander',
  notes?: string
): Promise<DeploymentPlan> {
  return request<DeploymentPlan>(`/projects/${projectId}/deployment/plan/approve`, {
    method: 'POST',
    body: JSON.stringify({ approved_by: approvedBy, notes })
  });
}

/** Executes a deployment after plan approval. */
export async function executeDeployment(
  projectId: string,
  simulateOnly: boolean = false
): Promise<DeploymentRecord> {
  return request<DeploymentRecord>(`/projects/${projectId}/deployment/deploy`, {
    method: 'POST',
    body: JSON.stringify({ simulate_only: simulateOnly })
  });
}

/** Retrieves current deployment status, plan, and readiness state. */
export async function getDeploymentStatus(projectId: string): Promise<DeploymentState> {
  return request<DeploymentState>(`/projects/${projectId}/deployment/status`);
}

/** Triggers a rollback to a previous deployment snapshot. */
export async function rollbackDeployment(
  projectId: string,
  targetDeploymentId?: string
): Promise<DeploymentRecord> {
  return request<DeploymentRecord>(`/projects/${projectId}/deployment/rollback`, {
    method: 'POST',
    body: JSON.stringify({ target_deployment_id: targetDeploymentId })
  });
}

/** Returns the full chronological deployment audit history. */
export async function getDeploymentHistory(projectId: string): Promise<DeploymentRecord[]> {
  return request<DeploymentRecord[]>(`/projects/${projectId}/deployment/history`);
}
