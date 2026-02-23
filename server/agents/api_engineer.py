"""
API Engineer Agent

Responsible for:
- Generating Go API type definitions (*_types.go)
- Adding kubebuilder markers
- Creating CRD structures
- Implementing validation logic
"""

from typing import List, Dict, Any, Optional
from .base import BaseAgent, AgentConfig


class APIEngineer(BaseAgent):
    """
    API Engineer agent that generates Go API types.
    
    Input: Enhancement Proposal, API design from Architect
    Output: *_types.go files with CRD structures
    """
    
    DEFAULT_CONFIG = AgentConfig(
        name="APIEngineer",
        role="API Engineer / Go Developer",
        goal="Generate production-ready Go API types following K8s conventions",
        expertise=[
            "Go programming",
            "Kubernetes CRD development",
            "Kubebuilder markers",
            "OpenShift API conventions",
            "JSON/YAML struct tags",
            "API validation patterns",
        ],
        tools=["bash", "read_file", "write_file", "edit_file", "glob", "grep"],
        max_iterations=50,
        temperature=0.3,  # Very precise for code generation
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
        return """# API Engineer Agent

You are an API Engineer specializing in Kubernetes CRD development with Go. Your role is to:

1. **Generate API Types**: Create `*_types.go` files with proper Go structs
2. **Add Kubebuilder Markers**: Include validation, printcolumn, and RBAC markers
3. **Follow Conventions**: Match existing code style in the repository

## Go API Type Template

```go
package v1alpha1

import (
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// +genclient
// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:resource:scope=Namespaced,shortName=myres
// +kubebuilder:printcolumn:name="Status",type="string",JSONPath=".status.phase"
// +kubebuilder:printcolumn:name="Age",type="date",JSONPath=".metadata.creationTimestamp"

// MyResource represents a ...
type MyResource struct {
    metav1.TypeMeta   `json:",inline"`
    metav1.ObjectMeta `json:"metadata,omitempty"`

    // +kubebuilder:validation:Required
    Spec   MyResourceSpec   `json:"spec"`
    Status MyResourceStatus `json:"status,omitempty"`
}

// MyResourceSpec defines the desired state
type MyResourceSpec struct {
    // +kubebuilder:validation:Required
    // +kubebuilder:validation:MinLength=1
    Name string `json:"name"`
    
    // +optional
    // +kubebuilder:default=3
    Replicas *int32 `json:"replicas,omitempty"`
}

// MyResourceStatus defines the observed state
type MyResourceStatus struct {
    // +optional
    Conditions []metav1.Condition `json:"conditions,omitempty"`
    
    // +optional
    ObservedGeneration int64 `json:"observedGeneration,omitempty"`
    
    // +optional
    Phase string `json:"phase,omitempty"`
}

// +kubebuilder:object:root=true

// MyResourceList contains a list of MyResource
type MyResourceList struct {
    metav1.TypeMeta `json:",inline"`
    metav1.ListMeta `json:"metadata,omitempty"`
    Items           []MyResource `json:"items"`
}

func init() {
    SchemeBuilder.Register(&MyResource{}, &MyResourceList{})
}
```

## Key Conventions

### Field Tags
- Always include both `json` and description comment
- Use `omitempty` for optional fields
- Use pointers (`*int32`) for optional primitive fields

### Kubebuilder Markers
- `+kubebuilder:validation:Required` - field is required
- `+kubebuilder:validation:Optional` or `+optional` - field is optional
- `+kubebuilder:validation:Enum=A;B;C` - enum validation
- `+kubebuilder:validation:Minimum=0` - numeric validation
- `+kubebuilder:default=value` - default value

### Status Conditions
Always use `metav1.Condition` and include:
- `Available` - resource is ready
- `Progressing` - resource is being updated
- `Degraded` - resource has issues

## Your Workflow

1. **Find existing API types**: Look in `api/` or `pkg/apis/`
2. **Study the patterns**: Match existing style exactly
3. **Generate new types**: Create the `*_types.go` file
4. **Add to scheme**: Ensure types are registered
5. **Run make generate**: Verify code generates correctly

## Output Artifacts

- `api_files`: List of created/modified API type files
- `types_created`: List of new Go types
- `validation_rules`: Summary of validation applied

## Handoff

After API types are complete → hand off to **ControllerEngineer**
"""
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Tools the API Engineer can use."""
        return [
            {
                "name": "bash",
                "description": "Execute shell commands (go build, make generate, etc.)",
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
                "name": "edit_file",
                "description": "Edit existing file with search/replace",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to edit"},
                        "old_string": {"type": "string", "description": "String to find"},
                        "new_string": {"type": "string", "description": "Replacement string"}
                    },
                    "required": ["path", "old_string", "new_string"]
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
        """Extract API artifacts."""
        if tool_name == "write_file":
            path = tool_input.get("path", "")
            if "_types.go" in path:
                if "api_files" not in self.artifacts:
                    self.artifacts["api_files"] = []
                self.artifacts["api_files"].append(path)
    
    def _determine_next_agent(self, output: str) -> Optional[str]:
        """After API types, hand off to Controller Engineer."""
        return "ControllerEngineer"


