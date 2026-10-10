from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from ..models import Blueprint
from ..implementation.models import ImplementationProposal, FailureAnalysis


class AIProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the AI provider."""
        pass

    @abstractmethod
    async def generate_blueprint(self, project_name: str, project_idea: str) -> Blueprint:
        """
        Analyze the project idea and return a structured technical Blueprint.
        Must raise an informative exception on failure.
        """
        pass

    @abstractmethod
    async def generate_task_implementation(
        self,
        task_title: str,
        task_description: str,
        project_context: Dict[str, Any],
        relevant_files: Dict[str, str]
    ) -> ImplementationProposal:
        """
        Generates structured file operations (create, modify) to implement a specific development task.
        """
        pass

    @abstractmethod
    async def analyze_failure(
        self,
        task_title: str,
        task_description: str,
        test_output: str,
        relevant_files: Dict[str, str],
        current_implementation: Optional[ImplementationProposal] = None
    ) -> FailureAnalysis:
        """
        Diagnoses test or compilation failures and provides structured root-cause analysis.
        """
        pass

    @abstractmethod
    async def generate_repair(
        self,
        task_title: str,
        task_description: str,
        failure_analysis: FailureAnalysis,
        test_output: str,
        relevant_files: Dict[str, str],
        attempt: int
    ) -> ImplementationProposal:
        """
        Generates targeted file modifications to fix the diagnosed failure.
        """
        pass
