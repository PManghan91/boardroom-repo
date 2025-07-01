#!/usr/bin/env python3
"""
Dedicated test runner for AI operations testing suite.

This script provides a unified interface for running all AI-related tests
with proper configuration, reporting, and coverage analysis.
"""

import argparse
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import json


class AITestRunner:
    """Comprehensive test runner for AI operations."""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.test_results: Dict[str, Any] = {}
        self.start_time = time.time()
        
    def setup_environment(self) -> None:
        """Setup test environment and dependencies."""
        print("🔧 Setting up test environment...")
        
        # Ensure we're in the project root
        os.chdir(self.project_root)
        
        # Check for required environment variables
        env_file = self.project_root / ".env"
        if not env_file.exists():
            print("⚠️  No .env file found, using environment defaults")
        
        # Set test-specific environment variables
        os.environ.setdefault("ENVIRONMENT", "test")
        os.environ.setdefault("LOG_LEVEL", "WARNING")
        os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")  # Test DB
        
        print("✅ Environment setup complete")
    
    def run_command(self, command: List[str], description: str) -> Dict[str, Any]:
        """Run a command and capture results."""
        print(f"🚀 {description}")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                cwd=self.project_root
            )
            
            duration = time.time() - start_time
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": duration,
                "command": " ".join(command)
            }
            
        except Exception as e:
            duration = time.time() - start_time
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "duration": duration,
                "command": " ".join(command)
            }
    
    def run_unit_tests(self, specific_module: Optional[str] = None) -> Dict[str, Any]:
        """Run unit tests for AI modules."""
        print("\n📋 Running AI unit tests...")
        
        # Define test modules
        test_modules = {
            "langgraph": "tests/unit/test_langgraph_graph.py",
            "ai_state_manager": "tests/unit/test_ai_state_manager.py",
            "meeting_tools": "tests/unit/test_meeting_management_tools.py"
        }
        
        if specific_module:
            if specific_module not in test_modules:
                raise ValueError(f"Unknown module: {specific_module}")
            test_modules = {specific_module: test_modules[specific_module]}
        
        results = {}
        
        for module_name, test_file in test_modules.items():
            print(f"\n  📝 Testing {module_name}...")
            
            command = [
                "python", "-m", "pytest",
                test_file,
                "-v",
                "--tb=short",
                f"--cov=app.core.langgraph" if "langgraph" in module_name else f"--cov=app.services.ai_state_manager" if "ai_state" in module_name else "--cov=app.core.langgraph.tools.meeting_management",
                "--cov-report=term-missing",
                f"--cov-report=xml:coverage-{module_name}.xml",
                f"--junit-xml=test-results-{module_name}.xml",
                "--disable-warnings"
            ]
            
            result = self.run_command(command, f"Unit tests: {module_name}")
            results[module_name] = result
            
            if result["success"]:
                print(f"  ✅ {module_name}: PASSED ({result['duration']:.2f}s)")
            else:
                print(f"  ❌ {module_name}: FAILED ({result['duration']:.2f}s)")
                if result["stderr"]:
                    print(f"     Error: {result['stderr'][:200]}...")
        
        return results
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests for AI operations."""
        print("\n🔗 Running AI integration tests...")
        
        command = [
            "python", "-m", "pytest",
            "tests/integration/test_ai_operations_endpoints.py",
            "-v",
            "--tb=short",
            "--cov=app.api.v1.ai_operations",
            "--cov-report=term-missing",
            "--cov-report=xml:coverage-integration.xml",
            "--junit-xml=test-results-integration.xml",
            "-m", "integration and not slow",
            "--disable-warnings"
        ]
        
        result = self.run_command(command, "Integration tests")
        
        if result["success"]:
            print(f"  ✅ Integration tests: PASSED ({result['duration']:.2f}s)")
        else:
            print(f"  ❌ Integration tests: FAILED ({result['duration']:.2f}s)")
        
        return {"integration": result}
    
    def run_performance_tests(self, include_slow: bool = False) -> Dict[str, Any]:
        """Run performance tests for AI operations."""
        print("\n⚡ Running AI performance tests...")
        
        # Standard performance tests
        command = [
            "python", "-m", "pytest",
            "tests/performance/test_ai_operations_performance.py",
            "-v",
            "--tb=short",
            "--junit-xml=test-results-performance.xml",
            "-m", "performance",
            "--disable-warnings"
        ]
        
        if not include_slow:
            command.extend(["-m", "performance and not slow"])
        
        result = self.run_command(command, "Performance tests")
        
        results = {"performance": result}
        
        if result["success"]:
            print(f"  ✅ Performance tests: PASSED ({result['duration']:.2f}s)")
        else:
            print(f"  ❌ Performance tests: FAILED ({result['duration']:.2f}s)")
        
        # Run load tests if requested
        if include_slow:
            print("\n  🔥 Running load tests...")
            
            load_command = [
                "python", "-m", "pytest",
                "tests/performance/test_ai_operations_performance.py",
                "-v",
                "--tb=short",
                "--junit-xml=test-results-load.xml",
                "-m", "performance and slow",
                "--disable-warnings",
                "--maxfail=1"
            ]
            
            load_result = self.run_command(load_command, "Load tests")
            results["load"] = load_result
            
            if load_result["success"]:
                print(f"  ✅ Load tests: PASSED ({load_result['duration']:.2f}s)")
            else:
                print(f"  ❌ Load tests: FAILED ({load_result['duration']:.2f}s)")
        
        return results
    
    def run_security_tests(self) -> Dict[str, Any]:
        """Run security tests for AI modules."""
        print("\n🛡️  Running security tests...")
        
        results = {}
        
        # Bandit security scan
        bandit_command = [
            "bandit",
            "-r",
            "app/core/langgraph/",
            "app/services/ai_state_manager.py",
            "app/api/v1/ai_operations.py",
            "-f", "json",
            "-o", "bandit-report.json"
        ]
        
        bandit_result = self.run_command(bandit_command, "Bandit security scan")
        results["bandit"] = bandit_result
        
        if bandit_result["success"]:
            print("  ✅ Bandit scan: PASSED")
        else:
            print("  ⚠️  Bandit scan: Issues found")
        
        # Safety dependency check
        safety_command = [
            "safety", "check",
            "--json",
            "--output", "safety-report.json"
        ]
        
        safety_result = self.run_command(safety_command, "Safety dependency check")
        results["safety"] = safety_result
        
        if safety_result["success"]:
            print("  ✅ Safety check: PASSED")
        else:
            print("  ⚠️  Safety check: Vulnerabilities found")
        
        return results
    
    def run_coverage_analysis(self) -> Dict[str, Any]:
        """Analyze and report test coverage."""
        print("\n📊 Analyzing test coverage...")
        
        # Combine coverage reports
        combine_command = [
            "coverage", "combine",
            "coverage-*.xml"
        ]
        
        combine_result = self.run_command(combine_command, "Combining coverage reports")
        
        # Generate coverage report
        report_command = [
            "coverage", "report",
            "--show-missing",
            "--format=markdown"
        ]
        
        report_result = self.run_command(report_command, "Generating coverage report")
        
        # Generate HTML coverage report
        html_command = [
            "coverage", "html",
            "-d", "coverage-html"
        ]
        
        html_result = self.run_command(html_command, "Generating HTML coverage report")
        
        results = {
            "combine": combine_result,
            "report": report_result,
            "html": html_result
        }
        
        if report_result["success"]:
            print("  ✅ Coverage analysis: COMPLETED")
            # Extract coverage percentage from output
            coverage_output = report_result["stdout"]
            if "TOTAL" in coverage_output:
                print(f"  📈 Coverage summary available in report")
        else:
            print("  ❌ Coverage analysis: FAILED")
        
        return results
    
    def generate_test_report(self) -> None:
        """Generate comprehensive test report."""
        print("\n📝 Generating test report...")
        
        total_duration = time.time() - self.start_time
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_duration": f"{total_duration:.2f}s",
            "results": self.test_results,
            "summary": self._generate_summary()
        }
        
        # Save JSON report
        report_file = self.project_root / "ai-test-report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        # Generate markdown report
        self._generate_markdown_report(report)
        
        print(f"  ✅ Test report saved: {report_file}")
        print(f"  📄 Markdown report: ai-test-report.md")
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate test summary statistics."""
        summary = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "test_categories": []
        }
        
        for category, results in self.test_results.items():
            if isinstance(results, dict):
                for test_name, result in results.items():
                    summary["total_tests"] += 1
                    if result.get("success", False):
                        summary["passed_tests"] += 1
                    else:
                        summary["failed_tests"] += 1
            
            summary["test_categories"].append(category)
        
        summary["success_rate"] = (
            summary["passed_tests"] / summary["total_tests"] * 100
            if summary["total_tests"] > 0 else 0
        )
        
        return summary
    
    def _generate_markdown_report(self, report: Dict[str, Any]) -> None:
        """Generate markdown test report."""
        md_content = f"""# AI Operations Test Report
        
**Generated:** {report['timestamp']}  
**Duration:** {report['total_duration']}

## Summary

- **Total Tests:** {report['summary']['total_tests']}
- **Passed:** {report['summary']['passed_tests']}
- **Failed:** {report['summary']['failed_tests']}
- **Success Rate:** {report['summary']['success_rate']:.1f}%

## Test Results

"""
        
        for category, results in report['results'].items():
            md_content += f"### {category.title()}\n\n"
            
            if isinstance(results, dict):
                for test_name, result in results.items():
                    status = "✅ PASSED" if result.get("success", False) else "❌ FAILED"
                    duration = result.get("duration", 0)
                    md_content += f"- **{test_name}:** {status} ({duration:.2f}s)\n"
            
            md_content += "\n"
        
        md_content += """
## Coverage Reports

- HTML coverage report: `coverage-html/index.html`
- XML coverage reports: `coverage-*.xml`

## Security Reports

- Bandit security scan: `bandit-report.json`
- Safety dependency check: `safety-report.json`

---
*Generated by AI Test Runner*
"""
        
        md_file = self.project_root / "ai-test-report.md"
        with open(md_file, "w") as f:
            f.write(md_content)
    
    def run_all_tests(self, args: argparse.Namespace) -> None:
        """Run complete AI test suite."""
        print("🚀 Starting AI Operations Test Suite")
        print("=" * 50)
        
        try:
            # Setup
            self.setup_environment()
            
            # Unit tests
            if not args.skip_unit:
                unit_results = self.run_unit_tests(args.module)
                self.test_results["unit_tests"] = unit_results
            
            # Integration tests
            if not args.skip_integration:
                integration_results = self.run_integration_tests()
                self.test_results["integration_tests"] = integration_results
            
            # Performance tests
            if args.performance or args.full:
                performance_results = self.run_performance_tests(include_slow=args.full)
                self.test_results["performance_tests"] = performance_results
            
            # Security tests
            if args.security or args.full:
                security_results = self.run_security_tests()
                self.test_results["security_tests"] = security_results
            
            # Coverage analysis
            if not args.skip_coverage:
                coverage_results = self.run_coverage_analysis()
                self.test_results["coverage"] = coverage_results
            
            # Generate report
            self.generate_test_report()
            
            # Final summary
            self._print_final_summary()
            
        except KeyboardInterrupt:
            print("\n⏹️  Test run interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n💥 Test run failed: {e}")
            sys.exit(1)
    
    def _print_final_summary(self) -> None:
        """Print final test summary."""
        summary = self._generate_summary()
        
        print("\n" + "=" * 50)
        print("🎯 AI TEST SUITE COMPLETE")
        print("=" * 50)
        
        print(f"📊 Results: {summary['passed_tests']}/{summary['total_tests']} tests passed")
        print(f"📈 Success Rate: {summary['success_rate']:.1f}%")
        print(f"⏱️  Total Duration: {time.time() - self.start_time:.2f}s")
        
        if summary['failed_tests'] > 0:
            print("\n❌ Some tests failed. Check the detailed report for more information.")
            sys.exit(1)
        else:
            print("\n✅ All tests passed successfully!")


def main():
    """Main entry point for the AI test runner."""
    parser = argparse.ArgumentParser(
        description="AI Operations Test Suite Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_ai_tests.py                    # Run standard tests
  python scripts/run_ai_tests.py --full            # Run all tests including performance
  python scripts/run_ai_tests.py --module langgraph # Test specific module
  python scripts/run_ai_tests.py --performance     # Include performance tests
  python scripts/run_ai_tests.py --security        # Include security tests
        """
    )
    
    parser.add_argument(
        "--module",
        choices=["langgraph", "ai_state_manager", "meeting_tools"],
        help="Run tests for specific module only"
    )
    
    parser.add_argument(
        "--skip-unit",
        action="store_true",
        help="Skip unit tests"
    )
    
    parser.add_argument(
        "--skip-integration",
        action="store_true",
        help="Skip integration tests"
    )
    
    parser.add_argument(
        "--skip-coverage",
        action="store_true",
        help="Skip coverage analysis"
    )
    
    parser.add_argument(
        "--performance",
        action="store_true",
        help="Include performance tests"
    )
    
    parser.add_argument(
        "--security",
        action="store_true",
        help="Include security tests"
    )
    
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run complete test suite including performance and load tests"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Create and run test suite
    runner = AITestRunner()
    runner.run_all_tests(args)


if __name__ == "__main__":
    main()