"""
Cloud Deployment Providers for ROGERS Deployment Automation (Slice 9).
Provides configuration generators for Render, Vercel, Netlify, and Railway.
"""
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import json

from backend.app.deployment.models import (
    DeploymentPlatform,
    ProjectStackDetection,
    GeneratedConfigFile
)
from backend.app.deployment.providers.base import BaseDeploymentProvider


class RenderDeploymentProvider(BaseDeploymentProvider):
    platform: DeploymentPlatform = "render"

    def generate_configurations(
        self,
        project_dir: Path,
        stack: ProjectStackDetection,
        target_port: int,
        env_vars: Dict[str, str]
    ) -> List[GeneratedConfigFile]:
        is_node = any(k in stack.language.lower() or k in stack.framework.lower() for k in ["node", "typescript", "javascript", "react", "vite"])
        env_type = "node" if is_node else "python"
        
        build_cmd = stack.build_command or ("npm install && npm run build" if is_node else "pip install -r requirements.txt")
        start_cmd = stack.start_command or ("npm start" if is_node else f"uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT")

        env_vars_block = ""
        for k in sorted(env_vars.keys()):
            env_vars_block += f"      - key: {k}\n        value: {env_vars[k]}\n"

        yaml_content = f"""services:
  - type: web
    name: {project_dir.name.lower()}
    env: {env_type}
    plan: free
    region: oregon
    buildCommand: {build_cmd}
    startCommand: {start_cmd}
    healthCheckPath: /health
    autoDeploy: false
    envVars:
      - key: PORT
        value: {target_port}
{env_vars_block}"""

        return [
            GeneratedConfigFile(
                filename="render.yaml",
                path="render.yaml",
                content=yaml_content.strip() + "\n",
                file_type="yaml"
            )
        ]

    def build_plan_steps(
        self,
        stack: ProjectStackDetection,
        target_port: int,
        health_check_path: str
    ) -> Tuple[Optional[str], Optional[str], List[str], List[str]]:
        build_cmd = stack.build_command or "pip install -r requirements.txt"
        start_cmd = stack.start_command or f"uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT"
        steps = [
            "Generate Blueprint render.yaml infrastructure-as-code specification",
            "Configure isolated Render Web Service container environment",
            "Install pinned production dependencies without cache contamination",
            f"Bind web runtime listener to dynamic port with endpoint {health_check_path}",
            "Probe service availability with automatic TLS certificate termination"
        ]
        risks = [
            "Render free tier services spin down after 15 minutes of inactivity.",
            "Requires Render API Key or GitHub repository link for automated webhook deployment."
        ]
        return build_cmd, start_cmd, steps, risks


class VercelDeploymentProvider(BaseDeploymentProvider):
    platform: DeploymentPlatform = "vercel"

    def generate_configurations(
        self,
        project_dir: Path,
        stack: ProjectStackDetection,
        target_port: int,
        env_vars: Dict[str, str]
    ) -> List[GeneratedConfigFile]:
        out_dir = stack.output_dir or "dist"
        vercel_config = {
            "version": 2,
            "name": project_dir.name.lower(),
            "buildCommand": stack.build_command or "npm run build",
            "outputDirectory": out_dir,
            "routes": [
                {
                    "src": "/(.*)",
                    "dest": "/$1"
                }
            ],
            "env": env_vars
        }

        return [
            GeneratedConfigFile(
                filename="vercel.json",
                path="vercel.json",
                content=json.dumps(vercel_config, indent=2) + "\n",
                file_type="json"
            )
        ]

    def build_plan_steps(
        self,
        stack: ProjectStackDetection,
        target_port: int,
        health_check_path: str
    ) -> Tuple[Optional[str], Optional[str], List[str], List[str]]:
        build_cmd = stack.build_command or "npm run build"
        start_cmd = None
        steps = [
            "Generate vercel.json manifest with static asset route mapping",
            "Compile production optimized bundle to target output directory",
            "Deploy assets to Vercel Global Edge Network",
            "Perform instant preview URL verification and TLS edge certificate binding"
        ]
        risks = [
            "Vercel is primarily optimized for frontend SPAs and serverless functions.",
            "Long-running stateful background processes cannot run on Vercel Edge."
        ]
        return build_cmd, start_cmd, steps, risks


class NetlifyDeploymentProvider(BaseDeploymentProvider):
    platform: DeploymentPlatform = "netlify"

    def generate_configurations(
        self,
        project_dir: Path,
        stack: ProjectStackDetection,
        target_port: int,
        env_vars: Dict[str, str]
    ) -> List[GeneratedConfigFile]:
        out_dir = stack.output_dir or "dist"
        build_cmd = stack.build_command or "npm run build"

        toml_content = f"""[build]
  command = "{build_cmd}"
  publish = "{out_dir}"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[context.production.environment]
"""
        for k in sorted(env_vars.keys()):
            toml_content += f'  {k} = "{env_vars[k]}"\n'

        return [
            GeneratedConfigFile(
                filename="netlify.toml",
                path="netlify.toml",
                content=toml_content.strip() + "\n",
                file_type="toml"
            )
        ]

    def build_plan_steps(
        self,
        stack: ProjectStackDetection,
        target_port: int,
        health_check_path: str
    ) -> Tuple[Optional[str], Optional[str], List[str], List[str]]:
        build_cmd = stack.build_command or "npm run build"
        start_cmd = None
        steps = [
            "Generate netlify.toml with single-page app rewrite rule configuration",
            "Execute client-side assets production compilation",
            "Publish static dist directory to Netlify High-Performance CDN",
            "Verify edge DNS resolution and instant rollback capability"
        ]
        risks = [
            "Persistent server-side Python processes require Netlify functions or separate backend."
        ]
        return build_cmd, start_cmd, steps, risks


class RailwayDeploymentProvider(BaseDeploymentProvider):
    platform: DeploymentPlatform = "railway"

    def generate_configurations(
        self,
        project_dir: Path,
        stack: ProjectStackDetection,
        target_port: int,
        env_vars: Dict[str, str]
    ) -> List[GeneratedConfigFile]:
        is_node = any(k in stack.language.lower() or k in stack.framework.lower() for k in ["node", "typescript", "javascript"])
        start_cmd = stack.start_command or ("npm start" if is_node else f"uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT")

        railway_config = {
            "$schema": "https://railway.app/railway.schema.json",
            "build": {
                "builder": "NIXPACKS",
                "buildCommand": stack.build_command or ("npm run build" if is_node else "pip install -r requirements.txt")
            },
            "deploy": {
                "startCommand": start_cmd,
                "healthcheckPath": "/health",
                "healthcheckTimeout": 100,
                "restartPolicyType": "ON_FAILURE",
                "restartPolicyMaxRetries": 3
            }
        }

        procfile_content = f"web: {start_cmd}\n"

        return [
            GeneratedConfigFile(
                filename="railway.json",
                path="railway.json",
                content=json.dumps(railway_config, indent=2) + "\n",
                file_type="json"
            ),
            GeneratedConfigFile(
                filename="Procfile",
                path="Procfile",
                content=procfile_content,
                file_type="procfile"
            )
        ]

    def build_plan_steps(
        self,
        stack: ProjectStackDetection,
        target_port: int,
        health_check_path: str
    ) -> Tuple[Optional[str], Optional[str], List[str], List[str]]:
        build_cmd = stack.build_command or "pip install -r requirements.txt"
        start_cmd = stack.start_command or "uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT"
        steps = [
            "Generate railway.json schema configuration and Procfile entrypoints",
            "Nixpacks build system auto-detects dependencies and provisions runtime",
            f"Launch isolated container worker bound to dynamic port $PORT",
            f"Monitor health check probe at {health_check_path} with auto-healing restart policy"
        ]
        risks = [
            "Requires Railway CLI or linked GitHub repository with active project token."
        ]
        return build_cmd, start_cmd, steps, risks
