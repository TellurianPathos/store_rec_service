#!/usr/bin/env python3
"""
Security audit script for AI Recommendation Service
Comprehensive security checks and vulnerability assessment
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import tempfile
import requests
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class SecurityIssue:
    """Security issue data structure"""
    severity: str
    category: str
    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    recommendation: Optional[str] = None


@dataclass
class SecurityReport:
    """Security audit report"""
    timestamp: str
    total_issues: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    issues: List[SecurityIssue]


class SecurityAuditor:
    """Main security auditor class"""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.issues: List[SecurityIssue] = []
        
    def run_audit(self) -> SecurityReport:
        """Run comprehensive security audit"""
        print("🔍 Starting security audit...")
        
        # Run all security checks
        self._check_dependencies()
        self._check_secrets()
        self._check_code_quality()
        self._check_docker_security()
        self._check_configuration()
        self._check_api_security()
        
        return self._generate_report()
    
    def _check_dependencies(self):
        """Check for vulnerable dependencies"""
        print("📦 Checking dependencies for vulnerabilities...")
        
        try:
            # Run pip-audit
            result = subprocess.run(
                ["pip-audit", "--format=json", "--desc"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                # Parse results if available
                try:
                    audit_data = json.loads(result.stdout)
                    for vulnerability in audit_data.get("vulnerabilities", []):
                        self.issues.append(SecurityIssue(
                            severity="high",
                            category="dependency",
                            title=f"Vulnerable dependency: {vulnerability['package']}",
                            description=vulnerability.get("description", "No description available"),
                            recommendation=f"Update to version {vulnerability.get('fixed_versions', ['latest'])[0]}"
                        ))
                except json.JSONDecodeError:
                    pass
            
        except subprocess.TimeoutExpired:
            self.issues.append(SecurityIssue(
                severity="medium",
                category="audit",
                title="Dependency audit timeout",
                description="Dependency vulnerability check timed out",
                recommendation="Run pip-audit manually to check for vulnerabilities"
            ))
        except FileNotFoundError:
            self.issues.append(SecurityIssue(
                severity="medium",
                category="audit",
                title="pip-audit not available",
                description="pip-audit tool not installed",
                recommendation="Install pip-audit: pip install pip-audit"
            ))
    
    def _check_secrets(self):
        """Check for exposed secrets"""
        print("🔐 Checking for exposed secrets...")
        
        # Check environment files
        env_files = list(self.project_path.glob(".env*"))
        for env_file in env_files:
            if env_file.name == ".env.example":
                continue
                
            try:
                content = env_file.read_text()
                lines = content.split("\n")
                
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    
                    # Check for potential secrets
                    if any(keyword in line.upper() for keyword in [
                        "PASSWORD=", "SECRET=", "KEY=", "TOKEN=", "API_KEY="
                    ]):
                        # Check if value looks like a real secret (not placeholder)
                        if "=" in line:
                            key, value = line.split("=", 1)
                            value = value.strip().strip('"\'')
                            
                            if (value and 
                                value not in ["", "your-key-here", "changeme", "password"] and
                                len(value) > 8 and
                                not value.startswith("${")):
                                
                                self.issues.append(SecurityIssue(
                                    severity="critical",
                                    category="secrets",
                                    title="Potential secret in environment file",
                                    description=f"Potential secret found in {env_file.name}",
                                    file_path=str(env_file),
                                    line_number=line_num,
                                    recommendation="Move secrets to secure environment variables or secret management system"
                                ))
                                
            except Exception as e:
                self.issues.append(SecurityIssue(
                    severity="medium",
                    category="audit",
                    title=f"Cannot read {env_file.name}",
                    description=str(e),
                    file_path=str(env_file)
                ))
        
        # Check Python files for hardcoded secrets
        python_files = list(self.project_path.rglob("*.py"))
        secret_patterns = [
            "api_key", "secret", "password", "token", "private_key",
            "access_key", "secret_key"
        ]
        
        for py_file in python_files:
            if "/.venv/" in str(py_file) or "__pycache__" in str(py_file):
                continue
                
            try:
                content = py_file.read_text()
                lines = content.split("\n")
                
                for line_num, line in enumerate(lines, 1):
                    line_lower = line.lower()
                    
                    # Look for assignment patterns with potential secrets
                    for pattern in secret_patterns:
                        if f"{pattern} =" in line_lower or f'"{pattern}"' in line_lower:
                            # Skip if it's a comment or example
                            if line.strip().startswith("#") or "example" in line_lower:
                                continue
                                
                            self.issues.append(SecurityIssue(
                                severity="high",
                                category="secrets",
                                title="Potential hardcoded secret",
                                description=f"Potential secret pattern found: {pattern}",
                                file_path=str(py_file),
                                line_number=line_num,
                                recommendation="Use environment variables or secure configuration"
                            ))
                            
            except Exception:
                continue  # Skip files that can't be read
    
    def _check_code_quality(self):
        """Check code quality and security patterns"""
        print("🔧 Checking code quality and security patterns...")
        
        try:
            # Run bandit for security issues
            result = subprocess.run(
                ["bandit", "-r", ".", "-f", "json", "-x", "tests/,*/test_*"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.stdout:
                try:
                    bandit_data = json.loads(result.stdout)
                    for issue in bandit_data.get("results", []):
                        severity_map = {
                            "LOW": "low",
                            "MEDIUM": "medium", 
                            "HIGH": "high"
                        }
                        
                        self.issues.append(SecurityIssue(
                            severity=severity_map.get(issue.get("issue_severity", "MEDIUM"), "medium"),
                            category="code-security",
                            title=issue.get("test_name", "Security issue"),
                            description=issue.get("issue_text", "No description"),
                            file_path=issue.get("filename"),
                            line_number=issue.get("line_number"),
                            recommendation="Review and fix the security issue"
                        ))
                        
                except json.JSONDecodeError:
                    pass
                    
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.issues.append(SecurityIssue(
                severity="medium",
                category="audit",
                title="Code security check unavailable",
                description="Bandit security checker not available or timed out",
                recommendation="Install bandit: pip install bandit"
            ))
    
    def _check_docker_security(self):
        """Check Docker configuration security"""
        print("🐳 Checking Docker security...")
        
        dockerfile = self.project_path / "Dockerfile"
        if dockerfile.exists():
            try:
                content = dockerfile.read_text()
                lines = content.split("\n")
                
                security_checks = [
                    ("FROM", "latest", "Using 'latest' tag is not recommended", "Use specific version tags"),
                    ("USER", "root", "Running as root user", "Use non-root user"),
                    ("ADD", "", "ADD command can be security risk", "Use COPY instead of ADD when possible"),
                    ("COPY", "--chown=", "File ownership not set", "Use --chown flag with COPY"),
                ]
                
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    
                    # Check for latest tag usage
                    if line.startswith("FROM") and ":latest" in line:
                        self.issues.append(SecurityIssue(
                            severity="medium",
                            category="docker",
                            title="Docker image using latest tag",
                            description="Using 'latest' tag makes builds non-deterministic",
                            file_path=str(dockerfile),
                            line_number=line_num,
                            recommendation="Use specific version tags"
                        ))
                    
                    # Check for running as root
                    if line.startswith("USER root") or (line.startswith("RUN") and "root" in line):
                        self.issues.append(SecurityIssue(
                            severity="high",
                            category="docker",
                            title="Docker container running as root",
                            description="Running containers as root increases security risk",
                            file_path=str(dockerfile),
                            line_number=line_num,
                            recommendation="Create and use a non-root user"
                        ))
                        
            except Exception as e:
                self.issues.append(SecurityIssue(
                    severity="low",
                    category="audit",
                    title="Cannot read Dockerfile",
                    description=str(e),
                    file_path=str(dockerfile)
                ))
    
    def _check_configuration(self):
        """Check configuration security"""
        print("⚙️ Checking configuration security...")
        
        # Check for insecure default configurations
        config_files = [
            "app/config.py",
            "config.py", 
            "settings.py",
            "app/settings.py"
        ]
        
        for config_file in config_files:
            config_path = self.project_path / config_file
            if config_path.exists():
                try:
                    content = config_path.read_text()
                    
                    # Check for insecure defaults
                    insecure_patterns = [
                        ("debug.*=.*true", "Debug mode enabled", "Disable debug in production"),
                        ("secret.*=.*['\"].*['\"]", "Hardcoded secret", "Use environment variables"),
                        ("password.*=.*['\"].*['\"]", "Hardcoded password", "Use environment variables"),
                        ("host.*=.*0\\.0\\.0\\.0", "Binding to all interfaces", "Bind to specific interfaces in production"),
                    ]
                    
                    lines = content.split("\n")
                    for line_num, line in enumerate(lines, 1):
                        line_lower = line.lower()
                        
                        for pattern, title, recommendation in insecure_patterns:
                            import re
                            if re.search(pattern, line_lower):
                                self.issues.append(SecurityIssue(
                                    severity="medium",
                                    category="configuration",
                                    title=title,
                                    description=f"Potentially insecure configuration: {line.strip()}",
                                    file_path=str(config_path),
                                    line_number=line_num,
                                    recommendation=recommendation
                                ))
                                
                except Exception:
                    continue
    
    def _check_api_security(self):
        """Check API security configuration"""
        print("🌐 Checking API security...")
        
        # Check main.py for security middleware and configurations
        main_py = self.project_path / "app" / "main.py"
        if main_py.exists():
            try:
                content = main_py.read_text()
                
                # Check for security middleware
                security_features = {
                    "CORSMiddleware": "CORS middleware configured",
                    "TrustedHostMiddleware": "Trusted host middleware configured",
                    "HTTPSRedirectMiddleware": "HTTPS redirect middleware configured",
                    "@app.middleware": "Custom middleware configured",
                    "api_key": "API key authentication",
                    "rate_limit": "Rate limiting configured",
                }
                
                missing_features = []
                for feature, description in security_features.items():
                    if feature.lower() not in content.lower():
                        missing_features.append((feature, description))
                
                if missing_features:
                    self.issues.append(SecurityIssue(
                        severity="medium",
                        category="api-security",
                        title="Missing security features",
                        description=f"Missing: {', '.join([f[0] for f in missing_features])}",
                        file_path=str(main_py),
                        recommendation="Implement missing security middleware and features"
                    ))
                    
                # Check for debug endpoints in production
                if "debug" in content.lower() and "production" in content.lower():
                    self.issues.append(SecurityIssue(
                        severity="high",
                        category="api-security",
                        title="Debug endpoints in production code",
                        description="Debug functionality present in production code",
                        file_path=str(main_py),
                        recommendation="Remove or properly guard debug endpoints"
                    ))
                    
            except Exception:
                pass
    
    def _generate_report(self) -> SecurityReport:
        """Generate final security report"""
        # Count issues by severity
        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        
        for issue in self.issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
        
        return SecurityReport(
            timestamp=datetime.now().isoformat(),
            total_issues=len(self.issues),
            critical_issues=severity_counts["critical"],
            high_issues=severity_counts["high"],
            medium_issues=severity_counts["medium"],
            low_issues=severity_counts["low"],
            issues=self.issues
        )


def print_report(report: SecurityReport, verbose: bool = False):
    """Print security report to console"""
    print("\n" + "="*80)
    print("🛡️  SECURITY AUDIT REPORT")
    print("="*80)
    print(f"Timestamp: {report.timestamp}")
    print(f"Total Issues: {report.total_issues}")
    print()
    
    # Summary by severity
    if report.critical_issues > 0:
        print(f"🔴 Critical: {report.critical_issues}")
    if report.high_issues > 0:
        print(f"🟠 High:     {report.high_issues}")
    if report.medium_issues > 0:
        print(f"🟡 Medium:   {report.medium_issues}")
    if report.low_issues > 0:
        print(f"🔵 Low:      {report.low_issues}")
    
    if report.total_issues == 0:
        print("✅ No security issues found!")
        return
    
    # Detailed issues
    if verbose:
        print("\n" + "-"*80)
        print("DETAILED ISSUES")
        print("-"*80)
        
        severity_icons = {
            "critical": "🔴",
            "high": "🟠", 
            "medium": "🟡",
            "low": "🔵"
        }
        
        for issue in sorted(report.issues, key=lambda x: {
            "critical": 0, "high": 1, "medium": 2, "low": 3
        }[x.severity]):
            icon = severity_icons.get(issue.severity, "❓")
            print(f"\n{icon} [{issue.severity.upper()}] {issue.title}")
            print(f"   Category: {issue.category}")
            print(f"   Description: {issue.description}")
            
            if issue.file_path:
                location = issue.file_path
                if issue.line_number:
                    location += f":{issue.line_number}"
                print(f"   Location: {location}")
                
            if issue.recommendation:
                print(f"   Recommendation: {issue.recommendation}")
    
    # Exit code based on severity
    if report.critical_issues > 0:
        print(f"\n❌ Audit failed: {report.critical_issues} critical issues found")
        return 2
    elif report.high_issues > 0:
        print(f"\n⚠️  Audit passed with warnings: {report.high_issues} high severity issues found")
        return 1
    else:
        print(f"\n✅ Audit passed: Only {report.medium_issues + report.low_issues} low/medium severity issues found")
        return 0


def save_report(report: SecurityReport, output_file: Path):
    """Save security report to JSON file"""
    report_data = asdict(report)
    with open(output_file, 'w') as f:
        json.dump(report_data, f, indent=2)
    print(f"📄 Report saved to {output_file}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Security audit for AI Recommendation Service")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--output", "-o", type=Path, help="Output file for JSON report")
    parser.add_argument("--project-path", type=Path, default=Path.cwd(), help="Project path")
    
    args = parser.parse_args()
    
    # Run security audit
    auditor = SecurityAuditor(args.project_path)
    report = auditor.run_audit()
    
    # Print report
    exit_code = print_report(report, args.verbose)
    
    # Save report if requested
    if args.output:
        save_report(report, args.output)
    
    # Exit with appropriate code
    sys.exit(exit_code)


if __name__ == "__main__":
    main()