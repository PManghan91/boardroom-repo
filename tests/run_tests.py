"""Test runner script for the Boardroom AI test suite.

This script provides convenient ways to run different types of tests
with appropriate configurations and reporting.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Optional


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> int:
    """Run a command and return the exit code."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def run_unit_tests(coverage: bool = True, verbose: bool = False) -> int:
    """Run unit tests only."""
    cmd = ["python", "-m", "pytest", "tests/unit/"]
    
    if coverage:
        cmd.extend(["--cov=app", "--cov-report=term-missing"])
    
    if verbose:
        cmd.append("-v")
    
    cmd.extend(["-m", "unit"])
    
    return run_command(cmd)


def run_integration_tests(verbose: bool = False) -> int:
    """Run integration tests only."""
    cmd = ["python", "-m", "pytest", "tests/integration/"]
    
    if verbose:
        cmd.append("-v")
    
    cmd.extend(["-m", "integration"])
    
    return run_command(cmd)


def run_all_tests(coverage: bool = True, verbose: bool = False, parallel: bool = False) -> int:
    """Run all tests."""
    cmd = ["python", "-m", "pytest"]
    
    if coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-report=json:coverage.json"
        ])
    
    if verbose:
        cmd.append("-v")
    
    if parallel:
        cmd.extend(["-n", "auto"])
    
    return run_command(cmd)


def run_fast_tests(verbose: bool = False) -> int:
    """Run only fast tests (exclude slow tests)."""
    cmd = ["python", "-m", "pytest", "-m", "not slow"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd)


def run_slow_tests(verbose: bool = False) -> int:
    """Run only slow tests."""
    cmd = ["python", "-m", "pytest", "-m", "slow"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd)


def run_infrastructure_tests(verbose: bool = False) -> int:
    """Run infrastructure tests to verify testing setup."""
    cmd = ["python", "-m", "pytest", "tests/test_infrastructure.py"]
    
    if verbose:
        cmd.append("-v")
    
    return run_command(cmd)


def generate_coverage_report() -> int:
    """Generate HTML coverage report."""
    cmd = ["python", "-m", "pytest", "--cov=app", "--cov-report=html:htmlcov", "--cov-only"]
    
    return run_command(cmd)


def check_coverage_threshold(threshold: int = 70) -> int:
    """Check if coverage meets the specified threshold."""
    cmd = ["python", "-m", "pytest", "--cov=app", f"--cov-fail-under={threshold}", "--cov-only"]
    
    return run_command(cmd)


def main():
    """Main test runner with command line interface."""
    if len(sys.argv) < 2:
        print("Usage: python run_tests.py [command] [options]")
        print("\nCommands:")
        print("  unit              Run unit tests only")
        print("  integration       Run integration tests only")
        print("  all               Run all tests")
        print("  fast              Run fast tests only (exclude slow)")
        print("  slow              Run slow tests only")
        print("  infrastructure    Run infrastructure tests")
        print("  coverage          Generate coverage report")
        print("  check-coverage    Check coverage threshold")
        print("\nOptions:")
        print("  --verbose, -v     Verbose output")
        print("  --no-coverage     Disable coverage (for unit/all tests)")
        print("  --parallel, -p    Run tests in parallel (for all tests)")
        print("  --threshold N     Coverage threshold (for check-coverage)")
        return 1
    
    command = sys.argv[1]
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    no_coverage = "--no-coverage" in sys.argv
    parallel = "--parallel" in sys.argv or "-p" in sys.argv
    
    # Get threshold for coverage check
    threshold = 70
    if "--threshold" in sys.argv:
        try:
            threshold_idx = sys.argv.index("--threshold") + 1
            if threshold_idx < len(sys.argv):
                threshold = int(sys.argv[threshold_idx])
        except (ValueError, IndexError):
            print("Invalid threshold value")
            return 1
    
    # Set environment for testing
    os.environ["APP_ENV"] = "test"
    
    if command == "unit":
        return run_unit_tests(coverage=not no_coverage, verbose=verbose)
    elif command == "integration":
        return run_integration_tests(verbose=verbose)
    elif command == "all":
        return run_all_tests(coverage=not no_coverage, verbose=verbose, parallel=parallel)
    elif command == "fast":
        return run_fast_tests(verbose=verbose)
    elif command == "slow":
        return run_slow_tests(verbose=verbose)
    elif command == "infrastructure":
        return run_infrastructure_tests(verbose=verbose)
    elif command == "coverage":
        return generate_coverage_report()
    elif command == "check-coverage":
        return check_coverage_threshold(threshold=threshold)
    else:
        print(f"Unknown command: {command}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)