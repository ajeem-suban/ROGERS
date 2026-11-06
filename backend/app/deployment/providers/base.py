"""
Base Deployment Provider Interface for ROGERS Deployment Automation (Slice 9).
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from backend.app.deployment.models import (
    DeploymentPlatform,
    ProjectStackDetection,
    GeneratedConfigFile,
    DeploymentPlan,
    DeploymentRecord
)


class BaseDeploymentProvider(ABC):
    """Abstract interface that every deployment target provider implements."""

    platform: DeploymentPlatform

    @abstractmethod
    def generate_configurations(
        self,
        project_dir: Path,
        stack: ProjectStackDetection,
        target_port: int,
        env_vars: Dict[str, str]
    ) -> List[GeneratedConfigFile]:
        """Generates target-specific deployment configuration files (e.g. Dockerfile, yaml, json)."""
        pass

    @abstractmethod
    def build_plan_steps(
        self,
        stack: ProjectStackDetection,
        target_port: int,
        health_check_path: str
    ) -> Tuple[Optional[str], Optional[str], List[str], List[str]]:
        """Returns (build_command, start_command, steps_list, risks_list)."""
        pass

    def apply_configurations(self, project_dir: Path, configs: List[GeneratedConfigFile]) -> List[str]:
        """Writes the generated configuration files to the project directory."""
        written = []
        for cfg in configs:
            target_path = project_dir / cfg.path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(cfg.content, encoding="utf-8")
            written.append(str(target_path.relative_to(project_dir)))
        return written
