import { 
  Project, 
  ProjectCreatePayload, 
  BlueprintResponse, 
  StageData,
  ScaffoldResponse,
  TaskImplementationResult
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
