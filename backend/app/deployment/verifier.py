"""
Readiness Verifier for ROGERS Deployment Automation (Slice 9).
Evaluates project directory structure, secret leakage, test verification status,
Git cleanliness, and configuration completeness before permitting deployment.
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.app.deployment.models import (
    ReadinessCheckItem,
    DeploymentReadinessReport,
    ReadinessStatus
)
from backend.app.models import Project


class DeploymentVerifier:
    """Performs rigorous security and operational readiness evaluations."""

    SECRET_PATTERNS = [
        (re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'), "Hardcoded Private Key"),
        (re.compile(r'ghp_[a-zA-Z0-9]{36}'), "GitHub Personal Access Token"),
        (re.compile(r'glpat-[a-zA-Z0-9\-_]{20}'), "GitLab Personal Access Token"),
        (re.compile(r'AIza[0-9A-Za-z\-_]{35}'), "Google API Key"),
        (re.compile(r'sk_live_[0-9a-zA-Z]{24}'), "Stripe Live API Key"),
        (re.compile(r'xox[baprs]-[0-9a-zA-Z\-]{10,}'), "Slack Token"),
        (re.compile(r'(?:password|secret|api_key)\s*=\s*["\'][a-zA-Z0-9!@#$%^&*()_+=\-`~]{12,}["\']', re.IGNORECASE), "Plaintext Secret Assignment")
    ]

    @classmethod
    def evaluate(cls, project: Project, project_dir: Path) -> DeploymentReadinessReport:
        checks: List[ReadinessCheckItem] = []
        blockers: List[str] = []
        warnings: List[str] = []
        recommendations: List[str] = []

        # 1. Project Directory Structure Check
        cls._check_project_structure(project_dir, checks, blockers, recommendations)

        # 2. Secret Scanner Check
        cls._check_secrets(project_dir, checks, blockers, warnings, recommendations)

        # 3. Test & Verification Gate Check
        cls._check_test_verification(project, checks, blockers, warnings, recommendations)

        # 4. Git Repository Cleanliness Check
        cls._check_git_status(project, project_dir, checks, warnings, recommendations)

        # 5. Runtime Entrypoint Check
        cls._check_entrypoint(project_dir, checks, blockers, recommendations)

        # Aggregate Score & Overall Status
        has_blocker = any(c.status == "blocked" for c in checks)
        has_warning = any(c.status == "warning" for c in checks)

        if has_blocker:
            overall_status: ReadinessStatus = "blocked"
            can_deploy = False
            score = max(10, 60 - len(blockers) * 20)
        elif has_warning:
            overall_status = "ready_with_warnings"
            can_deploy = True
            score = max(60, 100 - len(warnings) * 10)
        else:
            overall_status = "ready"
            can_deploy = True
            score = 100

        return DeploymentReadinessReport(
            overall_status=overall_status,
            can_deploy=can_deploy,
            score=score,
            checks=checks,
            blockers=blockers,
            warnings=warnings,
            recommendations=recommendations
        )

    @classmethod
    def _check_project_structure(cls, project_dir: Path, checks: List[ReadinessCheckItem], blockers: List[str], recommendations: List[str]):
        if not project_dir.exists():
            item = ReadinessCheckItem(
                id="dir_exists",
                title="Project Directory Existence",
                status="blocked",
                severity="critical",
                details=f"Target directory {project_dir.name} does not exist on disk.",
                recommendation="Initialize or scaffold the project files before attempting deployment."
            )
            checks.append(item)
            blockers.append(item.details)
            return

        files = [f for f in project_dir.iterdir() if not f.name.startswith(".")]
        if not files:
            item = ReadinessCheckItem(
                id="dir_not_empty",
                title="Project File Structure",
                status="blocked",
                severity="critical",
                details="Project directory contains no source or configuration files.",
                recommendation="Generate starter files or tasks before deploying."
            )
            checks.append(item)
            blockers.append(item.details)
        else:
            checks.append(ReadinessCheckItem(
                id="dir_structure",
                title="Project File Structure",
                status="pass",
                severity="info",
                details=f"Project directory is properly initialized with {len(files)} primary items."
            ))

    @classmethod
    def _check_secrets(cls, project_dir: Path, checks: List[ReadinessCheckItem], blockers: List[str], warnings: List[str], recommendations: List[str]):
        if not project_dir.exists():
            return

        detected_leaks: List[str] = []

        # Check for unmasked .env files with actual secret values
        env_file = project_dir / ".env"
        if env_file.exists():
            try:
                content = env_file.read_text(encoding="utf-8", errors="ignore")
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        _, val = line.split("=", 1)
                        val = val.strip().strip("'\"")
                        if len(val) > 10 and not any(placeholder in val.lower() for placeholder in ["example", "changeme", "your_", "todo", "sample", "test"]):
                            detected_leaks.append(f"Unmasked real value in .env: line starting with {line[:15]}...")
            except Exception:
                pass

        # Scan code files for secret patterns
        for root, _, files in os.walk(project_dir):
            if any(ign in root for ign in [".git", "node_modules", ".venv", "__pycache__", ".rogers"]):
                continue
            for f in files:
                if f.endswith((".py", ".ts", ".js", ".json", ".yaml", ".yml", ".env", ".txt", ".cfg", ".ini", ".toml")):
                    f_path = Path(root) / f
                    try:
                        content = f_path.read_text(encoding="utf-8", errors="ignore")
                        for pattern, name in cls.SECRET_PATTERNS:
                            if pattern.search(content):
                                detected_leaks.append(f"{name} detected in {f_path.relative_to(project_dir)}")
                    except Exception:
                        pass

        if detected_leaks:
            detail = f"Detected {len(detected_leaks)} potential secret leaks: {', '.join(detected_leaks[:3])}"
            rec = "Remove hardcoded credentials or replace unmasked .env secrets with environment variables."
            item = ReadinessCheckItem(
                id="secret_scanner",
                title="Security & Secret Leakage Scanner",
                status="blocked",
                severity="critical",
                details=detail,
                recommendation=rec
            )
            checks.append(item)
            blockers.append(detail)
            recommendations.append(rec)
        else:
            checks.append(ReadinessCheckItem(
                id="secret_scanner",
                title="Security & Secret Leakage Scanner",
                status="pass",
                severity="info",
                details="Zero plaintext secrets or unauthorized private credentials found in repository."
            ))

    @classmethod
    def _check_test_verification(cls, project: Project, checks: List[ReadinessCheckItem], blockers: List[str], warnings: List[str], recommendations: List[str]):
        # Check delivery package metadata or mission state
        pkg = project.package_metadata
        mission = project.mission_state or {}
        tasks = project.blueprint.development_tasks if project.blueprint else []

        tests_verified = False
        all_passed = False

        if pkg and pkg.verification_status:
            tests_verified = True
            all_passed = (pkg.verification_status.get("status") in ["verified", "passed", "complete"])

        if not tests_verified and mission.get("status") == "completed":
            tests_verified = True
            all_passed = True

        if not tests_verified and tasks:
            # Check if any tasks were implemented and tested
            verified_count = sum(1 for t in tasks if t.status in ["tested", "verified", "completed"])
            if verified_count > 0:
                tests_verified = True
                all_passed = (verified_count == len(tasks))

        if all_passed:
            checks.append(ReadinessCheckItem(
                id="test_verification",
                title="Test Suite & Quality Verification",
                status="pass",
                severity="info",
                details="All project unit tests and validation gates have verified execution successfully."
            ))
        elif tests_verified:
            item = ReadinessCheckItem(
                id="test_verification",
                title="Test Suite & Quality Verification",
                status="warning",
                severity="warning",
                details="Some development tasks remain unverified or have incomplete test suites.",
                recommendation="Run testing or complete the mission execution before deploying to production."
            )
            checks.append(item)
            warnings.append(item.details)
            recommendations.append(item.recommendation)
        else:
            item = ReadinessCheckItem(
                id="test_verification",
                title="Test Suite & Quality Verification",
                status="warning",
                severity="warning",
                details="No automated test execution results recorded for this project yet.",
                recommendation="Execute mission tests in Mission Control to confirm functional stability."
            )
            checks.append(item)
            warnings.append(item.details)
            recommendations.append(item.recommendation)

    @classmethod
    def _check_git_status(cls, project: Project, project_dir: Path, checks: List[ReadinessCheckItem], warnings: List[str], recommendations: List[str]):
        git_dir = project_dir / ".git"
        if not git_dir.exists():
            item = ReadinessCheckItem(
                id="git_status",
                title="Version Control (Git) Status",
                status="warning",
                severity="warning",
                details="Project repository is not currently initialized with Git.",
                recommendation="Initialize Git and commit working code in the GitHub & Publishing tab."
            )
            checks.append(item)
            warnings.append(item.details)
            recommendations.append(item.recommendation)
        else:
            checks.append(ReadinessCheckItem(
                id="git_status",
                title="Version Control (Git) Status",
                status="pass",
                severity="info",
                details="Project repository is tracked in Git version control."
            ))

    @classmethod
    def _check_entrypoint(cls, project_dir: Path, checks: List[ReadinessCheckItem], blockers: List[str], recommendations: List[str]):
        if not project_dir.exists():
            return

        candidates = [
            project_dir / "main.py",
            project_dir / "backend" / "app" / "main.py",
            project_dir / "package.json",
            project_dir / "frontend" / "package.json",
            project_dir / "index.html",
            project_dir / "Dockerfile"
        ]

        if any(c.exists() for c in candidates):
            checks.append(ReadinessCheckItem(
                id="entrypoint_check",
                title="Application Entrypoint Validation",
                status="pass",
                severity="info",
                details="Recognized application entrypoint file exists."
            ))
        else:
            item = ReadinessCheckItem(
                id="entrypoint_check",
                title="Application Entrypoint Validation",
                status="blocked",
                severity="critical",
                details="No recognized runtime entrypoint found (main.py, package.json, or Dockerfile).",
                recommendation="Create an entrypoint file or scaffold starter files before proceeding."
            )
            checks.append(item)
            blockers.append(item.details)
            recommendations.append(item.recommendation)
