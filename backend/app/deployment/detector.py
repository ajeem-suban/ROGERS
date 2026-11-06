"""
Stack Detector for ROGERS Deployment Automation (Slice 9).
Analyzes generated project file structure, dependencies, and blueprint to determine
runtime language, framework, build/start commands, ports, and configuration files.
"""
import os
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

from backend.app.deployment.models import ProjectStackDetection
from backend.app.models import Blueprint


class StackDetector:
    """Inspects a project workspace and determines deployment stack attributes."""

    @classmethod
    def detect(cls, project_dir: Path, blueprint: Optional[Blueprint] = None) -> ProjectStackDetection:
        detected_configs: List[str] = []
        required_env_vars: List[str] = []

        # Check existing config files
        config_candidates = [
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
            "render.yaml",
            "vercel.json",
            "netlify.toml",
            "railway.json",
            "Procfile",
            ".env.example",
            ".env.template"
        ]
        if project_dir.exists():
            for cfg in config_candidates:
                if (project_dir / cfg).exists():
                    detected_configs.append(cfg)
                # Also check backend/frontend subdirectories
                elif (project_dir / "backend" / cfg).exists():
                    detected_configs.append(f"backend/{cfg}")
                elif (project_dir / "frontend" / cfg).exists():
                    detected_configs.append(f"frontend/{cfg}")

        # Extract environment variables from .env.example or code
        cls._scan_env_vars(project_dir, required_env_vars)

        # 1. Inspect package.json / Node projects
        node_detection = cls._inspect_node(project_dir)
        if node_detection:
            node_detection.detected_configs = detected_configs
            node_detection.required_env_vars = list(set(required_env_vars))
            return node_detection

        # 2. Inspect Python projects
        python_detection = cls._inspect_python(project_dir)
        if python_detection:
            python_detection.detected_configs = detected_configs
            python_detection.required_env_vars = list(set(required_env_vars))
            return python_detection

        # 3. Fallback to Blueprint metadata if available
        if blueprint and blueprint.tech_stack:
            ts = blueprint.tech_stack
            lang = (ts.language or "python").lower()
            framework = (ts.framework or "fastapi").lower()
            
            is_node = any(k in lang or k in framework for k in ["node", "react", "typescript", "javascript", "vue", "next"])
            if is_node:
                return ProjectStackDetection(
                    language="typescript" if "typescript" in lang else "javascript",
                    framework=framework,
                    package_manager="npm",
                    build_command="npm run build",
                    start_command="npm run preview -- --host 0.0.0.0 --port 5173",
                    default_port=5173,
                    output_dir="dist",
                    detected_configs=detected_configs,
                    required_env_vars=list(set(required_env_vars))
                )
            else:
                return ProjectStackDetection(
                    language="python",
                    framework=framework,
                    package_manager="pip",
                    build_command="pip install -r requirements.txt",
                    start_command=f"uvicorn backend.app.main:app --host 0.0.0.0 --port 8000",
                    default_port=8000,
                    output_dir=None,
                    detected_configs=detected_configs,
                    required_env_vars=list(set(required_env_vars))
                )

        # 4. Default generic static / web project
        return ProjectStackDetection(
            language="python",
            framework="fastapi",
            package_manager="pip",
            build_command="pip install -r requirements.txt",
            start_command="uvicorn app.main:app --host 0.0.0.0 --port 8000",
            default_port=8000,
            output_dir=None,
            detected_configs=detected_configs,
            required_env_vars=list(set(required_env_vars))
        )

    @classmethod
    def _inspect_node(cls, project_dir: Path) -> Optional[ProjectStackDetection]:
        # Check root or frontend directory for package.json
        pkg_paths = [project_dir / "package.json", project_dir / "frontend" / "package.json"]
        for pkg_path in pkg_paths:
            if pkg_path.exists():
                try:
                    data = json.loads(pkg_path.read_text(encoding="utf-8"))
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    scripts = data.get("scripts", {})

                    framework = "node"
                    default_port = 3000
                    output_dir = "dist"

                    if "react" in deps or "vite" in deps:
                        framework = "react-vite" if "vite" in deps else "react"
                        default_port = 5173 if "vite" in deps else 3000
                    elif "next" in deps:
                        framework = "nextjs"
                        default_port = 3000
                        output_dir = ".next"
                    elif "express" in deps:
                        framework = "express"
                        default_port = 3000
                        output_dir = None

                    build_cmd = "npm run build" if "build" in scripts else None
                    if "start" in scripts:
                        start_cmd = "npm start"
                    elif "preview" in scripts:
                        start_cmd = f"npm run preview -- --host 0.0.0.0 --port {default_port}"
                    else:
                        start_cmd = f"node dist/index.js" if output_dir else "node index.js"

                    # Check yarn.lock / pnpm-lock
                    rel_dir = pkg_path.parent
                    pkg_mgr = "npm"
                    if (rel_dir / "pnpm-lock.yaml").exists():
                        pkg_mgr = "pnpm"
                    elif (rel_dir / "yarn.lock").exists():
                        pkg_mgr = "yarn"

                    return ProjectStackDetection(
                        language="typescript" if ("typescript" in deps or (rel_dir / "tsconfig.json").exists()) else "javascript",
                        framework=framework,
                        package_manager=pkg_mgr,
                        build_command=build_cmd,
                        start_command=start_cmd,
                        default_port=default_port,
                        output_dir=output_dir
                    )
                except Exception:
                    pass
        return None

    @classmethod
    def _inspect_python(cls, project_dir: Path) -> Optional[ProjectStackDetection]:
        candidates = [
            project_dir / "requirements.txt",
            project_dir / "pyproject.toml",
            project_dir / "backend" / "requirements.txt",
            project_dir / "backend" / "pyproject.toml",
            project_dir / "main.py",
            project_dir / "backend" / "app" / "main.py"
        ]

        found = any(c.exists() for c in candidates)
        if not found:
            return None

        # Check framework
        framework = "python"
        req_paths = [project_dir / "requirements.txt", project_dir / "backend" / "requirements.txt"]
        all_req_text = ""
        for rp in req_paths:
            if rp.exists():
                try:
                    all_req_text += "\n" + rp.read_text(encoding="utf-8")
                except Exception:
                    pass

        if "fastapi" in all_req_text.lower():
            framework = "fastapi"
        elif "flask" in all_req_text.lower():
            framework = "flask"
        elif "django" in all_req_text.lower():
            framework = "django"

        # Determine start command
        if (project_dir / "backend" / "app" / "main.py").exists():
            start_cmd = "uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"
        elif (project_dir / "main.py").exists():
            start_cmd = "python main.py"
        else:
            start_cmd = "uvicorn app.main:app --host 0.0.0.0 --port 8000"

        # Package manager
        pkg_mgr = "pip"
        if (project_dir / "pyproject.toml").exists() or (project_dir / "backend" / "pyproject.toml").exists():
            pkg_mgr = "pip"

        return ProjectStackDetection(
            language="python",
            framework=framework,
            package_manager=pkg_mgr,
            build_command="pip install -r requirements.txt",
            start_command=start_cmd,
            default_port=8000,
            output_dir=None
        )

    @classmethod
    def _scan_env_vars(cls, project_dir: Path, target_list: List[str]):
        if not project_dir.exists():
            return
        
        # Check .env.example / .env.template
        for name in [".env.example", ".env.template", "backend/.env.example"]:
            p = project_dir / name
            if p.exists():
                try:
                    lines = p.read_text(encoding="utf-8").splitlines()
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            var_name = line.split("=", 1)[0].strip()
                            if var_name and var_name not in target_list:
                                target_list.append(var_name)
                except Exception:
                    pass

        # Regex scan source files for os.environ.get or process.env
        pattern_py = re.compile(r'os\.(?:environ\.get|getenv)\(["\']([A-Z0-9_]+)["\']')
        pattern_js = re.compile(r'process\.env\.([A-Z0-9_]+)')

        for root, _, files in os.walk(project_dir):
            # Ignore .git, node_modules, .venv
            if any(ignore in root for ignore in [".git", "node_modules", ".venv", "__pycache__", ".rogers"]):
                continue
            for f in files:
                if f.endswith((".py", ".ts", ".js", ".tsx", ".jsx")):
                    f_path = Path(root) / f
                    try:
                        content = f_path.read_text(encoding="utf-8", errors="ignore")
                        for match in pattern_py.findall(content):
                            if match not in target_list and match not in ["PATH", "PORT", "PYTHONPATH"]:
                                target_list.append(match)
                        for match in pattern_js.findall(content):
                            if match not in target_list and match not in ["NODE_ENV", "PORT"]:
                                target_list.append(match)
                    except Exception:
                        pass
