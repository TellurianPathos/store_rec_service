#!/usr/bin/env python3
"""
Test runner script for the AI-Enhanced Recommendation System
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {command}")
        print(f"Exit code: {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False


def main():
    """Main test runner function"""
    print("🧪 AI-Enhanced Recommendation System Test Suite")
    
    # Change to project directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Check if virtual environment is activated
    if not os.environ.get('VIRTUAL_ENV') and not sys.prefix != sys.base_prefix:
        print("⚠️  Warning: No virtual environment detected")
        print("Consider running: source .venv/bin/activate")
    
    # Test commands to run
    test_commands = [
        {
            "command": "python -m pytest --version",
            "description": "Checking pytest installation"
        },
        {
            "command": "python -m pytest tests/ -v",
            "description": "Running all tests with verbose output"
        },
        {
            "command": "python -m pytest tests/ --cov=app --cov-report=term-missing",
            "description": "Running tests with coverage report"
        },
        {
            "command": "python -m pytest tests/ -m 'not slow'",
            "description": "Running fast tests only"
        }
    ]
    
    # Optional commands (may fail if dependencies not installed)
    optional_commands = [
        {
            "command": "python -m pytest tests/ --cov=app --cov-report=html",
            "description": "Generating HTML coverage report"
        },
        {
            "command": "python -c 'import flake8; print(\"flake8 available\")'",
            "description": "Checking code style tools"
        }
    ]
    
    success_count = 0
    total_count = len(test_commands)
    
    # Run main test commands
    for test_cmd in test_commands:
        if run_command(test_cmd["command"], test_cmd["description"]):
            success_count += 1
        else:
            print(f"❌ Failed: {test_cmd['description']}")
    
    # Run optional commands (don't count failures)
    print(f"\n{'='*60}")
    print("🔧 Optional Commands")
    print(f"{'='*60}")
    
    for opt_cmd in optional_commands:
        run_command(opt_cmd["command"], opt_cmd["description"])
    
    # Print summary
    print(f"\n{'='*60}")
    print("📊 Test Summary")
    print(f"{'='*60}")
    print(f"✅ Passed: {success_count}/{total_count}")
    print(f"❌ Failed: {total_count - success_count}/{total_count}")
    
    if success_count == total_count:
        print("🎉 All tests passed!")
        
        # Check if coverage report was generated
        if os.path.exists("htmlcov/index.html"):
            print(f"📊 Coverage report: file://{os.path.abspath('htmlcov/index.html')}")
    else:
        print("❌ Some tests failed. Check output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
