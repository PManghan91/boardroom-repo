#!/usr/bin/env python3
"""Code quality automation script for FastAPI LangGraph Template.

This script provides comprehensive code quality checks including:
- Code formatting with Black and isort
- Linting with Ruff and additional checks
- Quality metrics reporting
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class CodeQualityRunner:
    """Automated code quality runner for the FastAPI LangGraph Template project."""
    
    def __init__(self, project_root: Path) -> None:
        """Initialize the code quality runner.
        
        Args:
            project_root: Root directory of the project.
        """
        self.project_root = project_root
        self.app_dir = project_root / "app"
        self.tests_dir = project_root / "tests"
        self.scripts_dir = project_root / "scripts"
        self.quality_results: Dict[str, Dict[str, Any]] = {}
    
    def run_command(
        self, 
        command: List[str], 
        cwd: Optional[Path] = None,
        timeout: int = 300,
    ) -> Tuple[int, str, str]:
        """Run a shell command and return the result.
        
        Args:
            command: Command to run as a list of strings.
            cwd: Working directory for the command.
            timeout: Command timeout in seconds.
            
        Returns:
            Tuple of (return_code, stdout, stderr).
        """
        try:
            result = subprocess.run(
                command,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return 1, "", str(e)
    
    def format_code(self) -> bool:
        """Format code with Black and isort.
        
        Returns:
            True if formatting succeeded, False otherwise.
        """
        print("🎨 Formatting code with Black and isort...")
        
        # Run Black
        print("  Running Black...")
        code, stdout, stderr = self.run_command([
            "python", "-m", "black", 
            str(self.app_dir), 
            str(self.tests_dir),
            str(self.scripts_dir),
            "--line-length", "119",
        ])
        
        if code != 0:
            print(f"❌ Black failed: {stderr}")
            return False
        
        # Run isort
        print("  Running isort...")
        code, stdout, stderr = self.run_command([
            "python", "-m", "isort",
            str(self.app_dir),
            str(self.tests_dir),
            str(self.scripts_dir),
            "--profile", "black",
            "--line-length", "119",
        ])
        
        if code != 0:
            print(f"❌ isort failed: {stderr}")
            return False
        
        print("✅ Code formatting completed")
        return True
    
    def lint_code(self) -> bool:
        """Lint code with Ruff.
        
        Returns:
            True if linting passed, False otherwise.
        """
        print("🔍 Linting code with Ruff...")
        
        code, stdout, stderr = self.run_command([
            "python", "-m", "ruff", "check",
            str(self.app_dir),
            str(self.tests_dir),
            str(self.scripts_dir),
            "--output-format", "json",
        ])
        
        # Parse Ruff output
        issues = []
        if stdout:
            try:
                # Ruff outputs one JSON object per line
                for line in stdout.strip().split('\n'):
                    if line.strip():
                        issues.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        
        self.quality_results["ruff"] = {
            "issues_count": len(issues),
            "issues": issues,
            "passed": code == 0,
        }
        
        if code != 0:
            print(f"❌ Ruff found {len(issues)} issues")
            for issue in issues[:10]:  # Show first 10 issues
                filename = issue.get("filename", "unknown")
                location = issue.get("location", {})
                row = location.get("row", "?")
                message = issue.get("message", "Unknown error")
                print(f"  {filename}:{row} - {message}")
            if len(issues) > 10:
                print(f"  ... and {len(issues) - 10} more issues")
            return False
        
        print("✅ Linting passed")
        return True
    
    def calculate_quality_score(self) -> float:
        """Calculate overall quality score.
        
        Returns:
            Quality score from 0.0 to 10.0.
        """
        score = 10.0
        
        # Deduct points for issues
        ruff_issues = self.quality_results.get("ruff", {}).get("issues_count", 0)
        score -= min(ruff_issues * 0.1, 3.0)  # Max 3 points deduction
        
        return max(0.0, score)
    
    def generate_report(self) -> str:
        """Generate a comprehensive quality report.
        
        Returns:
            Formatted quality report string.
        """
        score = self.calculate_quality_score()
        
        report = f"""
📊 CODE QUALITY REPORT - FastAPI LangGraph Template
{'=' * 60}

Overall Quality Score: {score:.1f}/10.0

🔍 LINTING (Ruff):
  - Issues: {self.quality_results.get('ruff', {}).get('issues_count', 0)}
  - Status: {'✅ PASS' if self.quality_results.get('ruff', {}).get('passed', False) else '❌ FAIL'}

RECOMMENDATIONS:
"""
        
        # Add recommendations based on results
        if self.quality_results.get('ruff', {}).get('issues_count', 0) > 0:
            report += "- Fix linting issues to improve code style\n"
        
        if score >= 9.0:
            report += "- Excellent code quality! 🎉\n"
        elif score >= 7.0:
            report += "- Good code quality with room for improvement\n"
        else:
            report += "- Code quality needs significant improvement\n"
        
        return report


def main() -> None:
    """Main entry point for the code quality script."""
    parser = argparse.ArgumentParser(description="Run code quality checks")
    parser.add_argument("--format", action="store_true", help="Format code before checking")
    parser.add_argument("--lint", action="store_true", help="Run linting only")
    parser.add_argument("--all", action="store_true", help="Run all checks (default)")
    parser.add_argument("--report", type=str, help="Save report to file")
    parser.add_argument("--fail-on-score", type=float, default=7.0, help="Fail if score below threshold")
    
    args = parser.parse_args()
    
    # Default to all checks if no specific check is requested
    if not any([args.format, args.lint]):
        args.all = True
    
    project_root = Path(__file__).parent.parent
    runner = CodeQualityRunner(project_root)
    
    success = True
    
    # Format code if requested
    if args.format or args.all:
        if not runner.format_code():
            success = False
    
    # Run individual checks
    if args.lint or args.all:
        if not runner.lint_code():
            success = False
    
    # Generate and display report
    if args.all or args.report:
        report = runner.generate_report()
        print(report)
        
        # Save report if requested
        if args.report:
            try:
                with open(args.report, 'w') as f:
                    f.write(report)
                print(f"📝 Quality report saved to {args.report}")
            except Exception as e:
                print(f"❌ Failed to save report: {e}")
        
        # Check if score meets threshold
        score = runner.calculate_quality_score()
        if score < args.fail_on_score:
            print(f"❌ Quality score {score:.1f} is below threshold {args.fail_on_score}")
            success = False
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()