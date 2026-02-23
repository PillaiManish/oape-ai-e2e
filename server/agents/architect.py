"""
Architect Agent

Responsible for:
- Reviewing and refining Enhancement Proposals
- Analyzing existing codebase patterns
- Designing API structures
- Planning implementation approach
- Ensuring consistency with existing architecture
"""

from typing import List, Dict, Any, Optional
from .base import BaseAgent, AgentConfig


class Architect(BaseAgent):
    """
    Architect agent that designs and plans implementations.
    
    Input: Enhancement Proposal (from PM or URL)
    Output: Refined EP, API design, implementation plan
    """
    
    DEFAULT_CONFIG = AgentConfig(
        name="Architect",
        role="Software Architect / Technical Lead",
        goal="Design robust APIs and plan implementation following existing patterns",
        expertise=[
            "Kubernetes API conventions",
            "OpenShift API conventions",
            "Go programming patterns",
            "Controller-runtime architecture",
            "Library-go patterns",
            "CRD design",
        ],
        tools=["bash", "read_file", "write_file", "web_fetch", "glob", "grep"],
        max_iterations=40,
        temperature=0.5,  # More precise for design work
    )
    
    def __init__(self, working_dir: str, tool_executor: Any, stream_callback=None):
        super().__init__(
            config=self.DEFAULT_CONFIG,
            working_dir=working_dir,
            tool_executor=tool_executor,
            stream_callback=stream_callback,
        )
    
    @property
    def system_prompt(self) -> str:
        return """# Architect Agent

You are a Software Architect specializing in Kubernetes operators and OpenShift. Your role is to:

1. **Review Enhancement Proposals**: Validate technical feasibility and completeness
2. **Analyze Codebase**: Understand existing patterns and conventions
3. **Design APIs**: Create CRD structures following K8s/OpenShift conventions
4. **Plan Implementation**: Define which controllers need changes

## Key Conventions to Follow

### Kubernetes API Conventions
- Use `metav1.Condition` for status conditions
- Follow naming: `<Resource>Spec`, `<Resource>Status`
- Use pointers for optional fields
- Add kubebuilder markers for validation

### OpenShift API Conventions
- All fields have json and yaml tags
- Optional fields must be marked with `+optional`
- Use `// +kubebuilder:validation:*` for validation
- Status should have `conditions` and `observedGeneration`

### Controller Patterns
For **controller-runtime**:
```go
func (r *Reconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error)
```

For **library-go**:
```go
func (c *Controller) sync(ctx context.Context, syncCtx factory.SyncContext) error
```

## Your Workflow

1. **Fetch the Enhancement Proposal**: Read from URL or local path
2. **Analyze the repository**:
   - Detect framework (controller-runtime vs library-go)
   - Find existing API types in `api/` or `pkg/apis/`
   - Study existing controller patterns
3. **Design the API**:
   - Define new structs or modifications
   - Add validation rules
   - Plan status conditions
4. **Create implementation plan**:
   - Which files need to be created/modified
   - Order of implementation
   - Dependencies between components

## Output Artifacts

- `framework`: "controller-runtime" or "library-go"
- `api_design`: JSON structure of proposed API changes
- `implementation_plan`: Ordered list of tasks
- `files_to_create`: List of new files
- `files_to_modify`: List of existing files to change

## Handoff

After design is complete:
- If API types need creation → hand off to **APIEngineer**
- If only controller changes → hand off to **ControllerEngineer**
"""
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Tools the Architect can use."""
        return [
            {
                "name": "bash",
                "description": "Execute shell commands",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Command to execute"}
                    },
                    "required": ["command"]
                }
            },
            {
                "name": "read_file",
                "description": "Read file contents",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to read"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "write_file",
                "description": "Write content to file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to write"},
                        "content": {"type": "string", "description": "Content to write"}
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "web_fetch",
                "description": "Fetch URL content",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to fetch"}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "glob",
                "description": "Find files matching pattern",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Glob pattern"}
                    },
                    "required": ["pattern"]
                }
            },
            {
                "name": "grep",
                "description": "Search for patterns in files",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Regex pattern"},
                        "path": {"type": "string", "description": "Path to search"}
                    },
                    "required": ["pattern"]
                }
            }
        ]
    
    def _extract_artifacts(self, tool_name: str, tool_input: Dict, result: Any):
        """Extract design artifacts."""
        if tool_name == "bash":
            cmd = tool_input.get("command", "")
            result_str = str(result)
            
            # Detect framework
            if "controller-runtime" in result_str:
                self.artifacts["framework"] = "controller-runtime"
            elif "library-go" in result_str:
                self.artifacts["framework"] = "library-go"
    
    def _determine_next_agent(self, output: str) -> Optional[str]:
        """Route to appropriate engineer based on design."""
        output_lower = output.lower()
        
        if "api type" in output_lower or "crd" in output_lower or "_types.go" in output_lower:
            return "APIEngineer"
        elif "controller" in output_lower or "reconcile" in output_lower:
            return "ControllerEngineer"
        else:
            return "APIEngineer"  # Default to API first


