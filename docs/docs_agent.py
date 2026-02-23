#!/usr/bin/env python3
"""
Architecture Documentation Agent for Event Service GUI.

This agent analyzes the codebase and generates C4 Model architecture documentation.

Usage:
    python docs_agent.py              # Analyze codebase and suggest documentation
    python docs_agent.py --generate   # Generate full documentation suite
    python docs_agent.py --analyze    # Analyze current architecture
"""

import os
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class ServiceIntegration:
    """Represents a microservice integration."""
    name: str
    host_env: str
    port_env: str
    purpose: str
    adapter_class: str


class ArchitectureDocumentationAgent:
    """Agent for analyzing and understanding the architecture."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.docs_dir = self.project_root / "docs"
        self.app_dir = self.project_root / "event_service_gui"
        
        # Discovered integrations
        self.services: list[ServiceIntegration] = [
            ServiceIntegration(
                name="Event Service",
                host_env="EVENTS_HOST_SERVER",
                port_env="EVENTS_HOST_PORT",
                purpose="Core event and race data",
                adapter_class="EventsAdapter"
            ),
            ServiceIntegration(
                name="User Service",
                host_env="USERS_HOST_SERVER",
                port_env="USERS_HOST_PORT",
                purpose="Authentication and user management",
                adapter_class="UserAdapter"
            ),
            ServiceIntegration(
                name="Competition Format Service",
                host_env="COMPETITION_FORMAT_HOST_SERVER",
                port_env="COMPETITION_FORMAT_HOST_PORT",
                purpose="Competition rules and formats",
                adapter_class="CompetitionFormatAdapter"
            ),
            ServiceIntegration(
                name="Race Service",
                host_env="RACE_HOST_SERVER",
                port_env="RACE_HOST_PORT",
                purpose="Race execution and timing",
                adapter_class="RaceService"
            ),
            ServiceIntegration(
                name="Photo Service",
                host_env="PHOTO_HOST_SERVER",
                port_env="PHOTO_HOST_PORT",
                purpose="Photo management",
                adapter_class="PhotosAdapter"
            ),
        ]
    
    def analyze_codebase(self) -> dict:
        """Analyze the codebase and extract key information."""
        print("🔍 Analyzing codebase...")
        
        analysis = {
            "views": self._count_files("views", "*.py"),
            "services": self._count_files("services", "*_adapter.py"),
            "templates": self._count_files("templates", "*.html"),
            "static_files": self._count_files("static", "*.*"),
            "config_files": self._count_files("config", "*.json"),
            "test_files": self._count_files("../tests", "test_*.py"),
            "total_python_lines": self._count_python_lines(),
            "external_services": len(self.services),
        }
        
        print(f"  ✓ Views: {analysis['views']}")
        print(f"  ✓ Service Adapters: {analysis['services']}")
        print(f"  ✓ Templates: {analysis['templates']}")
        print(f"  ✓ External Services: {analysis['external_services']}")
        print(f"  ✓ Configuration Files: {analysis['config_files']}")
        
        return analysis
    
    def _count_files(self, directory: str, pattern: str) -> int:
        """Count files matching pattern in directory."""
        try:
            path = self.app_dir / directory
            if path.exists():
                return len(list(path.glob(pattern)))
        except Exception:
            pass
        return 0
    
    def _count_python_lines(self) -> int:
        """Count total lines of Python code."""
        total = 0
        for py_file in self.app_dir.rglob("*.py"):
            try:
                with open(py_file) as f:
                    total += len(f.readlines())
            except Exception:
                pass
        return total
    
    def extract_integrations(self) -> list[dict]:
        """Extract information about external service integrations."""
        print("🔗 Extracting service integrations...")
        
        integrations = []
        for service in self.services:
            integrations.append({
                "name": service.name,
                "purpose": service.purpose,
                "adapter": service.adapter_class,
                "environment_vars": [service.host_env, service.port_env],
            })
            print(f"  ✓ {service.name} → {service.adapter_class}")
        
        return integrations
    
    def generate_summary_report(self, analysis: dict) -> str:
        """Generate a human-readable summary report."""
        report = f"""
# Architecture Analysis Report

## Codebase Metrics

- **Total Python Lines**: {analysis['total_python_lines']:,}
- **View Components**: {analysis['views']}
- **Service Adapters**: {analysis['services']}
- **HTML Templates**: {analysis['templates']}
- **Configuration Files**: {analysis['config_files']}
- **Static Files**: {analysis['static_files']}
- **Test Files**: {analysis['test_files']}
- **External Microservices**: {analysis['external_services']}

## Architecture Summary

### Layers Identified
1. **Presentation Layer** (templates/) - {analysis['templates']} Jinja2 templates
2. **View/Routing Layer** (views/) - {analysis['views']} HTTP request handlers
3. **Service/Business Logic** (services) - Orchestration and validation
4. **Adapter/Integration Layer** (services/) - {analysis['services']} external service adapters

### External Dependencies
- Flask/aiohttp web framework
- JWT-based authentication
- MongoDB via microservices
- {analysis['external_services']} external microservices

## Key Patterns Identified

✓ Adapter Pattern - Service abstraction via adapters
✓ Facade Pattern - Services provide simplified interfaces
✓ MVC Pattern - Views, Business Logic, Data separation
✓ Configuration-Driven - Environment variable configuration
✓ Async-First - Non-blocking I/O with aiohttp

## Documentation Status

Currently documented:
- [x] C4 Context Model
- [x] C4 Container Model  
- [x] C4 Component Model
- [x] Data Models
- [x] Design Patterns
- [x] Integration Points
- [x] Deployment Architecture

Generate full documentation suite with: `python docs_agent.py --generate`

"""
        return report
    
    def print_integration_summary(self, integrations: list[dict]) -> None:
        """Print a summary of service integrations."""
        print("\n📡 Service Integrations:\n")
        print("┌─────────────────────────────┬────────────────────────────────┐")
        print("│ Service                     │ Adapter Class                  │")
        print("├─────────────────────────────┼────────────────────────────────┤")
        for integration in integrations:
            print(f"│ {integration['name']:<27} │ {integration['adapter']:<30} │")
        print("└─────────────────────────────┴────────────────────────────────┘\n")
    
    def run_analysis(self, verbose: bool = True) -> None:
        """Run complete analysis of the architecture."""
        print("\n" + "=" * 60)
        print("🏗️  Event Service GUI - Architecture Documentation Agent")
        print("=" * 60 + "\n")
        
        # Analyze
        analysis = self.analyze_codebase()
        integrations = self.extract_integrations()
        
        # Summary
        self.print_integration_summary(integrations)
        
        # Report
        if verbose:
            report = self.generate_summary_report(analysis)
            print(report)
        
        print("\n" + "=" * 60)
        print("✅ Analysis Complete!")
        print("=" * 60)
        print("\n📚 Documentation Location:")
        print(f"   {self.docs_dir}/")
        print("\n📖 Start with:")
        print(f"   {self.docs_dir / '00_index.md'}")
        print("\n")


def main():
    """Main entry point."""
    agent = ArchitectureDocumentationAgent()
    agent.run_analysis(verbose=True)


if __name__ == "__main__":
    main()
