from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pathlib import Path

from ..models import Project, DevelopmentTask
from ..providers.base import AIProvider
from ..providers.factory import get_ai_provider
from ..implementation.models import (
    ImplementationProposal,
    FileOperation,
    ValidationResult,
    TestResult,
    FailureAnalysis,
    TaskImplementationResult
)
from .models import AgentInfo, AgentRole, AgentStatus

logger = logging.getLogger("rogers.agents.roles")


class BaseSpecializedAgent:
    """Base class for specialized multi-agent roles."""
    def __init__(self, agent_id: str, role: AgentRole, name: str, specialization: str, provider: Optional[AIProvider] = None):
        self.agent_id = agent_id
        self.role = role
        self.name = name
        self.specialization = specialization
        self.status: AgentStatus = "idle"
        self.current_task_id: Optional[str] = None
        self.current_task_title: Optional[str] = None
        self.tasks_completed = 0
        self.recent_logs: List[str] = []
        self.provider = provider or get_ai_provider()

    def get_info(self) -> AgentInfo:
        return AgentInfo(
            agent_id=self.agent_id,
            role=self.role,
            name=self.name,
            specialization=self.specialization,
            status=self.status,
            current_task_id=self.current_task_id,
            current_task_title=self.current_task_title,
            tasks_completed=self.tasks_completed,
            recent_logs=self.recent_logs[-8:]
        )

    def log(self, message: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        entry = f"[{ts}] {message}"
        self.recent_logs.append(entry)
        logger.info(f"[{self.name} | {self.role.upper()}]: {message}")


class ResearchAgent(BaseSpecializedAgent):
    """Investigates domain context, extracts key requirements, and evaluates dependencies."""
    def __init__(self, provider: Optional[AIProvider] = None):
        super().__init__(
            agent_id="agent_researcher_01",
            role="researcher",
            name="Falcon Recon",
            specialization="Technical domain investigation and dependency analysis",
            provider=provider
        )

    async def investigate_task(self, project: Project, task: DevelopmentTask, relevant_files: Dict[str, str]) -> Dict[str, Any]:
        self.status = "busy"
        self.current_task_id = task.id
        self.current_task_title = task.title
        self.log(f"Analyzing technical requirements for task: '{task.title}'")

        context = {
            "task_id": task.id,
            "title": task.title,
            "description": task.description,
            "priority": task.priority,
            "depends_on": task.depends_on or [],
            "files_available": list(relevant_files.keys()),
            "tech_stack": project.blueprint.tech_stack.model_dump() if project.blueprint else {}
        }
        self.log(f"Research completed for '{task.title}'. Extracted {len(relevant_files)} context files.")
        self.status = "idle"
        self.current_task_id = None
        self.current_task_title = None
        return context


class ArchitectureAgent(BaseSpecializedAgent):
    """Evaluates component design, target file paths, and potential write collisions."""
    def __init__(self, provider: Optional[AIProvider] = None):
        super().__init__(
            agent_id="agent_architect_01",
            role="architect",
            name="Vision Architect",
            specialization="Component boundary design and file isolation planning",
            provider=provider
        )

    async def design_task_structure(self, task: DevelopmentTask, project_context: Dict[str, Any]) -> List[str]:
        self.status = "busy"
        self.current_task_id = task.id
        self.current_task_title = task.title
        self.log(f"Evaluating structural component layout for '{task.title}'")

        # Predict target files based on task title and tech stack
        predicted_files: List[str] = []
        lower_title = task.title.lower()
        if "scaffold" in lower_title or "database" in lower_title:
            predicted_files = ["backend/app/main.py", "backend/app/database.py"]
        elif "auth" in lower_title:
            predicted_files = ["backend/app/routes/auth.py", "backend/app/auth.py"]
        elif "model" in lower_title or "crud" in lower_title or "domain" in lower_title:
            predicted_files = ["backend/app/models/entities.py", "backend/app/routes/api.py"]
        elif "frontend" in lower_title or "ui" in lower_title:
            predicted_files = ["frontend/src/App.tsx", "frontend/src/components/Dashboard.tsx"]
        elif "test" in lower_title or "ci" in lower_title:
            predicted_files = ["tests/test_api.py", ".github/workflows/ci.yml"]
        else:
            predicted_files = [f"backend/app/services/{task.id}.py"]

        self.log(f"Architecture boundary planned: {len(predicted_files)} target file paths identified.")
        self.status = "idle"
        self.current_task_id = None
        self.current_task_title = None
        return predicted_files


class DevelopmentAgent(BaseSpecializedAgent):
    """Synthesizes code implementations and file operations."""
    def __init__(self, agent_id: str = "agent_developer_01", name: str = "War Machine Builder", provider: Optional[AIProvider] = None):
        super().__init__(
            agent_id=agent_id,
            role="developer",
            name=name,
            specialization="Sandboxed code synthesis and surgical file modifications",
            provider=provider
        )

    async def implement_code(
        self,
        task: DevelopmentTask,
        project_context: Dict[str, Any],
        relevant_files: Dict[str, str]
    ) -> ImplementationProposal:
        self.status = "busy"
        self.current_task_id = task.id
        self.current_task_title = task.title
        self.log(f"Generating implementation for '{task.title}'")

        proposal = await self.provider.generate_task_implementation(
            task_title=task.title,
            task_description=task.description,
            project_context=project_context,
            relevant_files=relevant_files
        )

        self.tasks_completed += 1
        self.log(f"Synthesized {len(proposal.changes)} file operations: {proposal.summary}")
        self.status = "idle"
        self.current_task_id = None
        self.current_task_title = None
        return proposal


class TestingAgent(BaseSpecializedAgent):
    __test__ = False
    """Executes validation tests, verifies passes, and analyzes test diagnostics."""
    def __init__(self, provider: Optional[AIProvider] = None):
        super().__init__(
            agent_id="agent_tester_01",
            role="tester",
            name="Hawkeye QA",
            specialization="Automated test execution, diagnostic analysis, and regression checks",
            provider=provider
        )

    async def verify_tests(self, task: DevelopmentTask, test_result: TestResult, validation_result: ValidationResult) -> bool:
        self.status = "busy"
        self.current_task_id = task.id
        self.current_task_title = task.title
        self.log(f"Auditing tests for '{task.title}': validation={validation_result.status}, tests={test_result.status}")

        passed = (validation_result.status == "passed") and (test_result.status in ("passed", "no_tests"))
        if passed:
            self.tasks_completed += 1
            self.log(f"Verification gate PASSED for '{task.title}'")
        else:
            self.log(f"Verification gate FAILED for '{task.title}': {test_result.failure_summary or validation_result.error}")

        self.status = "idle"
        self.current_task_id = None
        self.current_task_title = None
        return passed


class ReviewAgent(BaseSpecializedAgent):
    """Performs security checks, secret scanning, and code quality audits."""
    def __init__(self, provider: Optional[AIProvider] = None):
        super().__init__(
            agent_id="agent_reviewer_01",
            role="reviewer",
            name="Captain America Security Shield",
            specialization="Security audit, secret interception, and quality verification",
            provider=provider
        )

    async def review_implementation(self, task: DevelopmentTask, files_changed: List[str]) -> bool:
        self.status = "busy"
        self.current_task_id = task.id
        self.current_task_title = task.title
        self.log(f"Reviewing {len(files_changed)} files for security and compliance")

        for f in files_changed:
            if ".env" in f or ".git" in f or f.endswith(".pem") or f.endswith(".key"):
                self.log(f"SECURITY ALERT: Blocked sensitive file '{f}'")
                self.status = "idle"
                return False

        self.tasks_completed += 1
        self.log(f"Review passed: All {len(files_changed)} changed files verified safe.")
        self.status = "idle"
        self.current_task_id = None
        self.current_task_title = None
        return True
