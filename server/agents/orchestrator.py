"""
Orchestrator Agent

The central coordinator for the multi-agent system. Responsible for:
- Routing tasks to appropriate agents
- Managing workflow execution
- Coordinating agent handoffs
- Aggregating results
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from .base import AgentResult, AgentStatus
from .architect import Architect
from .api_engineer import APIEngineer
from .controller_engineer import ControllerEngineer
from .qa_engineer import QAEngineer
from .validator import Validator


class WorkflowType(Enum):
    """Types of workflows the orchestrator can run."""
    API_GENERATE = "api-generate"         # Generate API types only
    API_IMPLEMENT = "api-implement"       # Full implementation from EP
    API_GENERATE_TESTS = "api-generate-tests"  # Generate tests only
    E2E_GENERATE = "e2e-generate"         # Generate e2e tests


@dataclass
class WorkflowResult:
    """Result of a complete workflow execution."""
    workflow_type: WorkflowType
    status: str  # "success", "partial", "failed"
    agents_executed: List[str]
    agent_results: Dict[str, AgentResult]
    artifacts: Dict[str, Any] = field(default_factory=dict)
    total_iterations: int = 0
    error: Optional[str] = None


class Orchestrator:
    """
    Central coordinator for the multi-agent system.
    
    Routes tasks to specialized agents and manages workflow execution.
    """
    
    # Workflow definitions: which agents run in what order
    WORKFLOWS = {
        WorkflowType.API_GENERATE: [
            "Architect",
            "APIEngineer",
            "Validator",
        ],
        WorkflowType.API_IMPLEMENT: [
            "Architect",
            "APIEngineer",
            "ControllerEngineer",
            "QAEngineer",
            "Validator",
        ],
        WorkflowType.API_GENERATE_TESTS: [
            "QAEngineer",
            "Validator",
        ],
        WorkflowType.E2E_GENERATE: [
            "Architect",
            "QAEngineer",
            "Validator",
        ],
    }
    
    def __init__(
        self,
        working_dir: str,
        tool_executor: Any,
        stream_callback: Optional[Callable[[str], None]] = None,
    ):
        self.working_dir = working_dir
        self.tool_executor = tool_executor
        self.stream_callback = stream_callback
        
        # Initialize all agents
        self.agents = {
            "Architect": Architect(working_dir, tool_executor, stream_callback),
            "APIEngineer": APIEngineer(working_dir, tool_executor, stream_callback),
            "ControllerEngineer": ControllerEngineer(working_dir, tool_executor, stream_callback),
            "QAEngineer": QAEngineer(working_dir, tool_executor, stream_callback),
            "Validator": Validator(working_dir, tool_executor, stream_callback),
        }
    
    def _stream(self, text: str):
        """Send text to stream callback."""
        if self.stream_callback:
            self.stream_callback(text)
    
    def detect_workflow(self, command: str, prompt: str) -> WorkflowType:
        """
        Detect which workflow to run based on command and prompt.
        
        Args:
            command: The command name (api-implement, ep-generate, etc.)
            prompt: The user's prompt
            
        Returns:
            WorkflowType to execute
        """
        command_lower = command.lower().replace("-", "_").replace(" ", "_")
        
        if "api_generate_tests" in command_lower:
            return WorkflowType.API_GENERATE_TESTS
        elif "api_generate" in command_lower and "test" not in command_lower:
            return WorkflowType.API_GENERATE
        elif "api_implement" in command_lower:
            return WorkflowType.API_IMPLEMENT
        elif "e2e" in command_lower:
            return WorkflowType.E2E_GENERATE
        else:
            # Default to api-implement
            return WorkflowType.API_IMPLEMENT
    
    async def execute(
        self,
        command: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowResult:
        """
        Execute a workflow based on the command.
        
        Args:
            command: The command to execute
            prompt: User's prompt (EP URL, feature description, etc.)
            context: Additional context
            
        Returns:
            WorkflowResult with all agent outputs
        """
        # Detect workflow type
        workflow_type = self.detect_workflow(command, prompt)
        agent_sequence = self.WORKFLOWS.get(workflow_type, [])
        
        self._stream(f"\n# 🎯 Workflow: {workflow_type.value}\n")
        self._stream(f"**Agents:** {' → '.join(agent_sequence)}\n\n")
        
        # Execute agents in sequence
        agent_results: Dict[str, AgentResult] = {}
        all_artifacts: Dict[str, Any] = {}
        total_iterations = 0
        
        for i, agent_name in enumerate(agent_sequence):
            self._stream(f"\n---\n## Agent {i+1}/{len(agent_sequence)}: {agent_name}\n---\n")
            
            agent = self.agents.get(agent_name)
            if not agent:
                self._stream(f"⚠️ Agent {agent_name} not found!\n")
                continue
            
            # Build task for this agent
            task = self._build_task(workflow_type, agent_name, prompt, all_artifacts)
            
            # Execute agent
            result = await agent.execute(
                task=task,
                context=context,
                previous_artifacts=all_artifacts,
            )
            
            agent_results[agent_name] = result
            total_iterations += result.iterations_used
            
            # Collect artifacts
            all_artifacts.update(result.artifacts)
            all_artifacts[f"{agent_name}_output"] = result.output
            
            # Check for failure
            if result.status == AgentStatus.FAILED:
                self._stream(f"\n❌ Agent {agent_name} failed: {result.error}\n")
                
                # Decide whether to continue or abort
                if agent_name == "Validator":
                    # Validator failures are warnings, continue
                    self._stream("⚠️ Validation had issues but continuing...\n")
                else:
                    # Other failures might abort
                    return WorkflowResult(
                        workflow_type=workflow_type,
                        status="failed",
                        agents_executed=list(agent_results.keys()),
                        agent_results=agent_results,
                        artifacts=all_artifacts,
                        total_iterations=total_iterations,
                        error=f"Agent {agent_name} failed: {result.error}",
                    )
            else:
                self._stream(f"\n✅ Agent {agent_name} completed ({result.iterations_used} iterations)\n")
        
        # Generate final summary
        self._generate_summary(workflow_type, agent_results, all_artifacts)
        
        return WorkflowResult(
            workflow_type=workflow_type,
            status="success",
            agents_executed=list(agent_results.keys()),
            agent_results=agent_results,
            artifacts=all_artifacts,
            total_iterations=total_iterations,
        )
    
    def _build_task(
        self,
        workflow_type: WorkflowType,
        agent_name: str,
        prompt: str,
        artifacts: Dict[str, Any],
    ) -> str:
        """Build the task description for an agent."""
        
        if workflow_type == WorkflowType.API_IMPLEMENT:
            if agent_name == "Architect":
                return f"""Analyze the Enhancement Proposal and design the implementation:

Enhancement Proposal: {prompt}

1. Fetch and parse the enhancement proposal
2. Analyze existing codebase patterns
3. Create an implementation plan
4. Identify which API types and controllers need to be created/modified
"""
            elif agent_name == "APIEngineer":
                return f"""Generate Go API types based on the design:

Enhancement Proposal: {prompt}
Implementation plan: See artifacts from Architect

Create *_types.go files following existing patterns in the repository.
"""
            elif agent_name == "ControllerEngineer":
                return f"""Generate controller/reconciler code:

Enhancement Proposal: {prompt}
API types created: {artifacts.get('api_files', [])}

Create controller code following existing patterns. Include RBAC markers.
"""
            elif agent_name == "QAEngineer":
                return f"""Generate tests for the implementation:

Files created:
- API types: {artifacts.get('api_files', [])}
- Controllers: {artifacts.get('controller_files', [])}

Create integration tests and unit tests following existing patterns.
"""
            elif agent_name == "Validator":
                return """Validate all generated code:

1. Run `make generate` and `make manifests`
2. Run `go build ./...`
3. Run `make test`
4. Run linter

Fix any errors found and re-validate until all checks pass.
"""
        
        elif workflow_type == WorkflowType.API_GENERATE:
            if agent_name == "Architect":
                return f"""Analyze the Enhancement Proposal for API design:

Enhancement Proposal: {prompt}

Extract API requirements and design CRD structures.
"""
            elif agent_name == "APIEngineer":
                return f"""Generate Go API types:

Enhancement Proposal: {prompt}

Create *_types.go files following existing patterns.
"""
            elif agent_name == "Validator":
                return "Validate API types compile correctly."
        
        elif workflow_type == WorkflowType.API_GENERATE_TESTS:
            if agent_name == "QAEngineer":
                return f"""Generate integration tests for existing API types:

API path: {prompt}

Create comprehensive tests following existing patterns.
"""
            elif agent_name == "Validator":
                return "Validate tests compile and pass."
        
        # Default task
        return f"Execute your role for: {prompt}"
    
    def _generate_summary(
        self,
        workflow_type: WorkflowType,
        agent_results: Dict[str, AgentResult],
        artifacts: Dict[str, Any],
    ):
        """Generate a final summary of the workflow execution."""
        self._stream("\n\n# 📋 Workflow Summary\n\n")
        self._stream(f"**Workflow:** {workflow_type.value}\n\n")
        
        self._stream("## Agent Execution\n\n")
        self._stream("| Agent | Status | Iterations |\n")
        self._stream("|-------|--------|------------|\n")
        
        for agent_name, result in agent_results.items():
            status_emoji = "✅" if result.status == AgentStatus.COMPLETED else "❌"
            self._stream(f"| {agent_name} | {status_emoji} {result.status.value} | {result.iterations_used} |\n")
        
        total_iters = sum(r.iterations_used for r in agent_results.values())
        self._stream(f"\n**Total Iterations:** {total_iters}\n\n")
        
        # List artifacts
        if artifacts:
            self._stream("## Generated Artifacts\n\n")
            for key, value in artifacts.items():
                if isinstance(value, list):
                    self._stream(f"- **{key}:** {len(value)} items\n")
                    for item in value[:5]:  # Show first 5
                        self._stream(f"  - {item}\n")
                elif isinstance(value, str) and len(value) < 100:
                    self._stream(f"- **{key}:** {value}\n")
                elif isinstance(value, bool):
                    self._stream(f"- **{key}:** {'✅' if value else '❌'}\n")
        
        self._stream("\n---\n**Workflow Complete!**\n")


