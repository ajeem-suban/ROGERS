import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status

from ..models import (
    Project, 
    ProjectCreate, 
    BlueprintResponse, 
    StageData, 
    StageActionPayload,
    ScaffoldResponse
)
from ..implementation.models import TaskImplementationResult
from ..implementation.service import (
    TaskImplementationService, 
    PathSecurityError, 
    TaskImplementationError, 
    restore_snapshot
)
from ..storage import ProjectStorage
from ..orchestrator import BlueprintOrchestrator, OrchestratorError
from ..scaffolder import ProjectScaffolder, GENERATED_BASE_DIR, slugify

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate):
    name = payload.name.strip()
    idea = payload.idea.strip()

    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project name cannot be empty.")
    if not idea:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project idea cannot be empty.")

    project = Project(
        id=str(uuid.uuid4()),
        name=name,
        idea=idea,
        status="created"
    )
    # Initialize default 5 stages
    orchestrator = BlueprintOrchestrator()
    orchestrator.initialize_project_stages(project)
    ProjectStorage.save(project)
    return project


@router.get("", response_model=List[Project])
async def list_projects():
    return ProjectStorage.get_all()


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str):
    project = ProjectStorage.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")
    return project


# Slice 1 compatibility endpoint
@router.post("/{project_id}/blueprint", response_model=BlueprintResponse)
async def generate_blueprint(project_id: str):
    project = ProjectStorage.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

    orchestrator = BlueprintOrchestrator()
    try:
        blueprint = await orchestrator.generate_project_blueprint(project)
        return BlueprintResponse(
            project_id=project.id,
            status=project.status,
            blueprint=blueprint
        )
    except OrchestratorError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Slice 2 Multi-Stage Endpoints
@router.post("/{project_id}/stages/{stage_name}/run", response_model=StageData)
async def run_stage(project_id: str, stage_name: str, payload: Optional[StageActionPayload] = None):
    project = ProjectStorage.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

    guidance = payload.guidance if payload else None
    orchestrator = BlueprintOrchestrator()
    try:
        stage = await orchestrator.run_stage(project, stage_name, guidance=guidance, auto_approve=False)
        return stage
    except OrchestratorError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{project_id}/stages/{stage_name}/approve", response_model=StageData)
async def approve_stage(project_id: str, stage_name: str):
    project = ProjectStorage.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

    orchestrator = BlueprintOrchestrator()
    try:
        stage = await orchestrator.approve_stage(project, stage_name, advance=True)
        return stage
    except OrchestratorError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{project_id}/stages/{stage_name}/modify", response_model=StageData)
async def modify_stage(project_id: str, stage_name: str, payload: StageActionPayload):
    project = ProjectStorage.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

    if not payload.modifications:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Modifications payload is required.")

    orchestrator = BlueprintOrchestrator()
    try:
        stage = await orchestrator.modify_stage(project, stage_name, payload.modifications)
        return stage
    except OrchestratorError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{project_id}/run-all", response_model=Project)
async def run_all_stages(project_id: str):
    project = ProjectStorage.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

    orchestrator = BlueprintOrchestrator()
    try:
        updated_project = await orchestrator.run_all_stages(project)
        return updated_project
    except OrchestratorError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{project_id}/scaffold", response_model=ScaffoldResponse)
async def scaffold_project(project_id: str):
    project = ProjectStorage.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

    if not project.blueprint:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Project must have an approved blueprint before scaffolding can be generated."
        )

    try:
        project_dir, files = ProjectScaffolder.scaffold(project)
        return ScaffoldResponse(
            project_id=project.id,
            project_dir=project_dir,
            files_created=files,
            message=f"Successfully generated {len(files)} files in {project_dir}"
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str):
    deleted = ProjectStorage.delete(project_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")
    return None


@router.post("/{project_id}/tasks/{task_id}/implement", response_model=TaskImplementationResult)
async def implement_task(project_id: str, task_id: str):
    project = ProjectStorage.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

    service = TaskImplementationService()
    try:
        result = await service.implement_task(project, task_id)
        return result
    except PathSecurityError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except TaskImplementationError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{project_id}/tasks/{task_id}/restore")
async def restore_task(project_id: str, task_id: str):
    project = ProjectStorage.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

    target_task = None
    if project.blueprint and project.blueprint.development_tasks:
        for t in project.blueprint.development_tasks:
            if t.id == task_id or t.title.lower() == task_id.lower():
                target_task = t
                break

    if not target_task or not target_task.implementation_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No implementation result or snapshot found for this task.")

    snapshot_id = target_task.implementation_result.snapshot_id
    if not snapshot_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No snapshot ID available for restore.")

    project_dir = GENERATED_BASE_DIR / slugify(project.name)
    success = restore_snapshot(project_dir, snapshot_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to restore snapshot backup.")

    target_task.status = "pending"
    target_task.implementation_result = None
    ProjectStorage.save(project)
    return {"message": "Files successfully restored from snapshot backup.", "status": "restored"}
