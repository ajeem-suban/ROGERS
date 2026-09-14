import re
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from .models import (
    Project, 
    Blueprint, 
    StageData, 
    TechStack, 
    Architecture, 
    DevelopmentTask
)
from .providers.base import AIProvider
from .providers.factory import get_ai_provider
from .storage import ProjectStorage

logger = logging.getLogger("rogers.orchestrator")

STAGE_SEQUENCE = [
    ("research", "Research & Domain Analysis"),
    ("requirements", "Requirements Engineering"),
    ("architecture", "System Architecture"),
    ("tech_stack", "Technology Stack"),
    ("development", "Development Roadmap & Tasks"),
]


class OrchestratorError(Exception):
    pass


class BlueprintOrchestrator:
    def __init__(self, provider: Optional[AIProvider] = None):
        self.provider = provider or get_ai_provider()

    def initialize_project_stages(self, project: Project) -> Project:
        """Ensures all 5 stages exist in the project stage dictionary."""
        if not project.stages:
            stages_dict = {}
            for stage_name, label in STAGE_SEQUENCE:
                stages_dict[stage_name] = StageData(
                    name=stage_name,
                    label=label,
                    status="pending"
                )
            project.stages = stages_dict
            if not project.current_stage:
                project.current_stage = "research"
            ProjectStorage.save(project)
        return project

    def _build_context(self, project: Project, target_stage: str) -> Dict[str, Any]:
        """Gathers project idea, stage outputs, and human modifications across all stages."""
        context = {
            "project_name": project.name,
            "project_idea": project.idea,
            "previous_stages": {}
        }
        for s_name, _ in STAGE_SEQUENCE:
            if s_name == target_stage:
                continue
            stage_data = project.stages.get(s_name)
            if stage_data and (stage_data.output or stage_data.user_modifications):
                effective_output = stage_data.user_modifications or stage_data.output
                context["previous_stages"][s_name] = effective_output
        return context

    async def run_stage(
        self, 
        project: Project, 
        stage_name: str, 
        guidance: Optional[str] = None,
        auto_approve: bool = False
    ) -> StageData:
        """Executes an individual stage with context awareness and user guidance."""
        self.initialize_project_stages(project)

        if stage_name not in project.stages:
            raise OrchestratorError(f"Invalid stage '{stage_name}'. Valid stages: {[s[0] for s in STAGE_SEQUENCE]}")

        stage = project.stages[stage_name]
        stage.status = "running"
        if guidance:
            stage.guidance = guidance
        stage.updated_at = datetime.now(timezone.utc).isoformat()
        project.current_stage = stage_name
        ProjectStorage.save(project)

        context = self._build_context(project, stage_name)
        logger.info(f"Running stage '{stage_name}' for project '{project.name}' with provider {self.provider.name}")

        try:
            # Generate tailored stage output based on context & guidance
            output = await self._synthesize_stage_output(project, stage_name, context, guidance)
            stage.output = output
            stage.status = "approved" if auto_approve else "waiting_approval"
            stage.updated_at = datetime.now(timezone.utc).isoformat()
            
            # If development stage is completed, assemble the full blueprint
            if stage_name == "development" or auto_approve:
                self._sync_blueprint_from_stages(project)

            ProjectStorage.save(project)
            return stage

        except Exception as e:
            logger.error(f"Stage '{stage_name}' failed for project '{project.id}': {e}", exc_info=True)
            stage.status = "failed"
            stage.updated_at = datetime.now(timezone.utc).isoformat()
            ProjectStorage.save(project)
            raise OrchestratorError(f"Stage '{stage_name}' execution failed: {str(e)}") from e

    async def approve_stage(self, project: Project, stage_name: str, advance: bool = True) -> StageData:
        """Approves a stage and optionally advances to the next stage."""
        self.initialize_project_stages(project)
        if stage_name not in project.stages:
            raise OrchestratorError(f"Stage '{stage_name}' not found.")

        stage = project.stages[stage_name]
        stage.status = "approved"
        stage.updated_at = datetime.now(timezone.utc).isoformat()

        # Find next stage
        stage_names = [s[0] for s in STAGE_SEQUENCE]
        idx = stage_names.index(stage_name)
        if idx < len(stage_names) - 1 and advance:
            project.current_stage = stage_names[idx + 1]
        elif idx == len(stage_names) - 1:
            project.status = "completed"
            self._sync_blueprint_from_stages(project)

        ProjectStorage.save(project)
        return stage

    async def modify_stage(self, project: Project, stage_name: str, modifications: Dict[str, Any]) -> StageData:
        """Stores human-in-the-loop modifications to a stage output."""
        self.initialize_project_stages(project)
        if stage_name not in project.stages:
            raise OrchestratorError(f"Stage '{stage_name}' not found.")

        stage = project.stages[stage_name]
        stage.user_modifications = modifications
        # Merge modifications into output
        if stage.output:
            stage.output.update(modifications)
        else:
            stage.output = modifications

        stage.status = "modified"
        stage.updated_at = datetime.now(timezone.utc).isoformat()
        self._sync_blueprint_from_stages(project)
        ProjectStorage.save(project)
        return stage

    async def run_all_stages(self, project: Project) -> Project:
        """Runs all stages sequentially from first to last with automatic approvals."""
        self.initialize_project_stages(project)
        project.status = "generating"
        ProjectStorage.save(project)

        for s_name, _ in STAGE_SEQUENCE:
            await self.run_stage(project, s_name, auto_approve=True)

        project.status = "completed"
        self._sync_blueprint_from_stages(project)
        ProjectStorage.save(project)
        return project

    def _sync_blueprint_from_stages(self, project: Project) -> None:
        """Assembles a unified Blueprint object from individual stage outputs."""
        research = (project.stages.get("research") and (project.stages["research"].user_modifications or project.stages["research"].output)) or {}
        reqs = (project.stages.get("requirements") and (project.stages["requirements"].user_modifications or project.stages["requirements"].output)) or {}
        arch = (project.stages.get("architecture") and (project.stages["architecture"].user_modifications or project.stages["architecture"].output)) or {}
        stack = (project.stages.get("tech_stack") and (project.stages["tech_stack"].user_modifications or project.stages["tech_stack"].output)) or {}
        dev = (project.stages.get("development") and (project.stages["development"].user_modifications or project.stages["development"].output)) or {}

        summary = research.get("summary") or f"{project.name} technical implementation plan."
        requirements_list = reqs.get("functional_requirements") or reqs.get("requirements") or []
        
        tech_stack_data = TechStack(
            frontend=stack.get("frontend", "React + TypeScript + Vite + Tailwind"),
            backend=stack.get("backend", "FastAPI + Python"),
            database=stack.get("database", "PostgreSQL + Redis"),
            ai=stack.get("ai", "Llama 3 / Mistral")
        )

        arch_data = Architecture(
            description=arch.get("description", "Layered service architecture."),
            components=arch.get("components", ["Frontend", "Backend API", "Database"])
        )

        dev_tasks: List[DevelopmentTask] = []
        raw_tasks = dev.get("tasks") or dev.get("development_tasks") or []
        for i, t in enumerate(raw_tasks):
            if isinstance(t, dict):
                title = t.get("title", "Task")
                clean_title = re.sub(r"[^a-zA-Z0-9]", "_", title.lower()).strip("_")[:30]
                task_id = t.get("id") or f"task_{i+1}_{clean_title}"
                dev_tasks.append(DevelopmentTask(
                    id=task_id,
                    title=title,
                    description=t.get("description", "Details"),
                    priority=t.get("priority", "medium"),
                    status=t.get("status", "pending")
                ))

        next_steps = dev.get("next_steps") or [
            "Review architecture decisions and initialize project repository.",
            "Set up development environment with Docker Compose.",
            "Begin sprint 1 core entity and API implementation."
        ]

        project.blueprint = Blueprint(
            summary=summary,
            requirements=requirements_list,
            tech_stack=tech_stack_data,
            architecture=arch_data,
            development_tasks=dev_tasks,
            next_steps=next_steps
        )

    async def _synthesize_stage_output(
        self, 
        project: Project, 
        stage_name: str, 
        context: Dict[str, Any], 
        guidance: Optional[str]
    ) -> Dict[str, Any]:
        """Generates realistic structured output for a specific stage using context and guidance."""
        # Use full blueprint generator as domain intelligence base
        base_bp = await self.provider.generate_blueprint(project.name, project.idea)

        # Apply any previous human modifications that impact this stage
        prev = context.get("previous_stages", {})
        prev_stack = prev.get("tech_stack", {})
        prev_arch = prev.get("architecture", {})

        if stage_name == "research":
            return {
                "summary": base_bp.summary + (f" Note: {guidance}" if guidance else ""),
                "domain_classification": "High-Performance Intelligent System",
                "key_challenges": [
                    "Data ingestion throughput and format normalization",
                    "Latency management under concurrent request volume",
                    "Accuracy and precision of domain-specific intelligence models",
                    "Secure role-based resource isolation"
                ],
                "recommended_approach": "Decoupled microservice/service-oriented architecture with asynchronous task queue."
            }

        elif stage_name == "requirements":
            reqs = list(base_bp.requirements)
            if guidance:
                reqs.append(f"Custom user requirement: {guidance}")
            return {
                "functional_requirements": reqs,
                "non_functional_requirements": [
                    "Sub-second API response latency for 95% of standard requests",
                    "Strict input sanitization, rate limiting, and CORS governance",
                    "Containerized deployments with health checks and graceful teardown",
                    "Full audit trail logging for security compliance"
                ]
            }

        elif stage_name == "architecture":
            components = list(base_bp.architecture.components)
            # Propagate database modification from previous stage if present
            db_choice = prev_stack.get("database") or base_bp.tech_stack.database
            desc = base_bp.architecture.description
            if "sqlite" in db_choice.lower():
                desc = desc.replace("pgvector", "SQLite vector extension").replace("PostgreSQL", "SQLite")
            elif "mongodb" in db_choice.lower():
                desc = desc.replace("PostgreSQL", "MongoDB")

            if guidance:
                desc += f" (Architectural constraint: {guidance})"

            return {
                "description": desc,
                "components": components,
                "communication_protocol": "REST over HTTP/2, WebSockets for streaming events",
                "caching_strategy": "Redis in-memory caching for active sessions and frequent queries"
            }

        elif stage_name == "tech_stack":
            fe = prev_stack.get("frontend") or base_bp.tech_stack.frontend
            be = prev_stack.get("backend") or base_bp.tech_stack.backend
            db = prev_stack.get("database") or base_bp.tech_stack.database
            ai = prev_stack.get("ai") or base_bp.tech_stack.ai

            if guidance:
                if "go" in guidance.lower() or "golang" in guidance.lower():
                    be = "Go (Golang 1.22+) with Gin / Echo"
                if "sqlite" in guidance.lower():
                    db = "SQLite 3 with WAL mode enabled"
                if "vue" in guidance.lower():
                    fe = "Vue 3 + Vite + Tailwind CSS"

            return {
                "frontend": fe,
                "backend": be,
                "database": db,
                "ai": ai,
                "rationale": "Chosen for fast developer velocity, high reliability, and rich ecosystem support."
            }

        elif stage_name == "development":
            tasks = [t.model_dump() for t in base_bp.development_tasks]
            if guidance:
                tasks.insert(0, {
                    "title": "Custom Milestone Implementation",
                    "description": f"Incorporate custom guidance: {guidance}",
                    "priority": "high"
                })
            return {
                "sprints": [
                    {"sprint": 1, "focus": "Project foundation, database setup, and core ingestion"},
                    {"sprint": 2, "focus": "Domain intelligence processing and API layer"},
                    {"sprint": 3, "focus": "Client UI, dashboard, and integration testing"}
                ],
                "tasks": tasks,
                "next_steps": base_bp.next_steps
            }

        return {}

    # Slice 1 compatibility method
    async def generate_project_blueprint(self, project: Project) -> Blueprint:
        """Maintains full backward compatibility with Slice 1 single-shot generation."""
        await self.run_all_stages(project)
        return project.blueprint
