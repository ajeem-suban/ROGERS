from abc import ABC, abstractmethod
from typing import Any, Dict
from ..models import Blueprint
from ..implementation.models import ImplementationProposal


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
