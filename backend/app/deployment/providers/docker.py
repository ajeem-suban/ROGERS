"""
Docker & Container Deployment Provider for ROGERS (Slice 9).
Generates production multi-stage Dockerfile and docker-compose.yml configurations.
"""
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from backend.app.deployment.models import (
    DeploymentPlatform,
    ProjectStackDetection,
    GeneratedConfigFile
)
from backend.app.deployment.providers.base import BaseDeploymentProvider


class DockerDeploymentProvider(BaseDeploymentProvider):
    platform: DeploymentPlatform = "docker"

    def generate_configurations(
        self,
        project_dir: Path,
        stack: ProjectStackDetection,
        target_port: int,
        env_vars: Dict[str, str]
    ) -> List[GeneratedConfigFile]:
        configs: List[GeneratedConfigFile] = []

        is_python = stack.language.lower() == "python"
        is_node = any(k in stack.language.lower() or k in stack.framework.lower() for k in ["node", "typescript", "javascript", "react", "vite", "next"])

        # 1. Generate Dockerfile
        if is_python:
            dockerfile_content = f"""# syntax=docker/dockerfile:1
FROM python:3.11-slim as base

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PORT={target_port}

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

EXPOSE {target_port}

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:{target_port}/health || exit 1

CMD ["sh", "-c", "{stack.start_command or f'uvicorn backend.app.main:app --host 0.0.0.0 --port {target_port}'}"]
"""
        elif is_node:
            dockerfile_content = f"""# syntax=docker/dockerfile:1
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN {stack.build_command or 'npm run build'}

# Production runtime stage
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \\
    PORT={target_port}

COPY --from=builder /app ./

EXPOSE {target_port}

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \\
    CMD wget -qO- http://localhost:{target_port}/health || exit 1

CMD ["sh", "-c", "{stack.start_command or f'npm run preview -- --host 0.0.0.0 --port {target_port}'}"]
"""
        else:
            dockerfile_content = f"""# syntax=docker/dockerfile:1
FROM python:3.11-slim
WORKDIR /app
COPY . .
EXPOSE {target_port}
CMD ["python", "main.py"]
"""

        configs.append(GeneratedConfigFile(
            filename="Dockerfile",
            path="Dockerfile",
            content=dockerfile_content.strip() + "\n",
            file_type="dockerfile"
        ))

        # 2. Generate docker-compose.yml
        env_lines = ""
        for k in sorted(env_vars.keys()):
            env_lines += f"      - {k}={env_vars[k]}\n"

        compose_content = f"""version: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
    image: rogers-{project_dir.name.lower()}:latest
    container_name: rogers-{project_dir.name.lower()}
    ports:
      - "{target_port}:{target_port}"
    environment:
      - PORT={target_port}
{env_lines}    restart: unless-stopped
"""
        configs.append(GeneratedConfigFile(
            filename="docker-compose.yml",
            path="docker-compose.yml",
            content=compose_content.strip() + "\n",
            file_type="yaml"
        ))

        # 3. .dockerignore
        dockerignore = """__pycache__
*.pyc
*.pyo
*.pyd
.venv
venv
env
node_modules
.git
.gitignore
.rogers
.env
dist
build
.pytest_cache
"""
        configs.append(GeneratedConfigFile(
            filename=".dockerignore",
            path=".dockerignore",
            content=dockerignore.strip() + "\n",
            file_type="dockerfile"
        ))

        return configs

    def build_plan_steps(
        self,
        stack: ProjectStackDetection,
        target_port: int,
        health_check_path: str
    ) -> Tuple[Optional[str], Optional[str], List[str], List[str]]:
        build_cmd = f"docker build -t rogers-app:latest ."
        start_cmd = f"docker run -d -p {target_port}:{target_port} --name rogers-app rogers-app:latest"
        steps = [
            "Generate verified multi-stage Dockerfile and docker-compose.yml",
            "Synthesize .dockerignore exclusion list to protect local credentials",
            f"Execute container image build targeting port {target_port}",
            f"Launch container instance in detached isolated bridge network",
            f"Probe HTTP health endpoint at http://localhost:{target_port}{health_check_path}"
        ]
        risks = [
            "Docker daemon must be running if deploying to a local Docker host.",
            f"Host port {target_port} must not collide with other local services."
        ]
        return build_cmd, start_cmd, steps, risks
