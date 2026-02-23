"""
Validator Agent

Responsible for:
- Running make generate and make manifests
- Compiling code (go build)
- Running tests (make test)
- Running linters (golangci-lint)
- Fixing errors automatically
"""

from typing import List, Dict, Any, Optional
from .base import BaseAgent, AgentConfig


class Validator(BaseAgent):
    """
    Validator agent that ensures code quality.
    
    Input: Generated code from previous agents
    Output: Validated, fixed code ready for PR
    """
    
    DEFAULT_CONFIG = AgentConfig(
        name="Validator",
        role="Build Engineer / DevOps",
        goal="Ensure code compiles, tests pass, and lint is clean",
        expertise=[
            "Go build system",
            "Make",
            "golangci-lint",
            "Error analysis",
            "Code fixing",
        ],
        tools=["bash", "read_file", "edit_file"],
        max_iterations=40,
        temperature=0.2,  # Very precise for fixing
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
        return """# Validator Agent

You are a Build Engineer responsible for validating and fixing generated code. Your role is to:

1. **Run Code Generation**: Execute `make generate` and `make manifests`
2. **Compile Code**: Run `go build ./...`
3. **Run Tests**: Execute `make test`
4. **Run Linter**: Execute `golangci-lint run` or `make lint`
5. **Fix Errors**: Automatically fix any issues found

## Validation Workflow

### Step 1: Run Code Generation
```bash
make generate
make manifests
```

If errors occur:
- Check for missing dependencies
- Verify kubebuilder markers are correct
- Fix and re-run

### Step 2: Compile Code
```bash
go build ./...
```

Common errors and fixes:
- `undefined: X` → Add import or fix typo
- `cannot use X as Y` → Fix type mismatch
- `too many arguments` → Fix function signature
- `not enough arguments` → Add missing arguments

### Step 3: Run Tests
```bash
make test
```

If tests fail:
- Analyze failure output
- Fix test or implementation
- Re-run tests

### Step 4: Run Linter
```bash
golangci-lint run ./...
# or
make lint
```

Common lint fixes:
- `unused` → Remove unused code or add `_ = variable`
- `errcheck` → Handle error returns
- `ineffassign` → Fix variable assignments
- `staticcheck` → Various static analysis fixes

## Error Analysis Pattern

When you see an error:

1. **Read the error carefully**: Identify file, line, and message
2. **Read the problematic code**: Use read_file to see context
3. **Determine the fix**: Based on error type
4. **Apply the fix**: Use edit_file with precise search/replace
5. **Re-validate**: Run the check again

## Fix Loop

```
MAX_FIX_ATTEMPTS = 5

for attempt in range(MAX_FIX_ATTEMPTS):
    run validation step
    if success:
        break
    analyze error
    apply fix
    continue
```

## Output Artifacts

- `validation_passed`: Boolean - all checks passed
- `errors_fixed`: List of errors that were fixed
- `remaining_issues`: Any issues that couldn't be auto-fixed
- `final_commands`: Commands to run for final verification

## Handoff

After validation is complete → workflow is done, output final summary
"""
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Tools the Validator can use."""
        return [
            {
                "name": "bash",
                "description": "Execute build/test commands",
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
                "description": "Read file to analyze errors",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to read"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "edit_file",
                "description": "Fix code issues",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to edit"},
                        "old_string": {"type": "string", "description": "String to find"},
                        "new_string": {"type": "string", "description": "Replacement"}
                    },
                    "required": ["path", "old_string", "new_string"]
                }
            }
        ]
    
    def _extract_artifacts(self, tool_name: str, tool_input: Dict, result: Any):
        """Extract validation artifacts."""
        if tool_name == "bash":
            cmd = tool_input.get("command", "")
            result_str = str(result)
            
            # Track validation results
            if "make generate" in cmd or "make manifests" in cmd:
                if "error" not in result_str.lower():
                    self.artifacts["generate_passed"] = True
            
            if "go build" in cmd:
                if "error" not in result_str.lower():
                    self.artifacts["build_passed"] = True
            
            if "make test" in cmd or "go test" in cmd:
                if "FAIL" not in result_str and "error" not in result_str.lower():
                    self.artifacts["tests_passed"] = True
            
            if "lint" in cmd:
                if "error" not in result_str.lower():
                    self.artifacts["lint_passed"] = True
    
    def _determine_next_agent(self, output: str) -> Optional[str]:
        """Validator is the last agent, no handoff."""
        return None


