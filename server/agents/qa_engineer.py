"""
QA Engineer Agent

Responsible for:
- Generating integration tests for API types
- Creating unit tests for controllers
- Generating e2e test scaffolding
- Validating test coverage
"""

from typing import List, Dict, Any, Optional
from .base import BaseAgent, AgentConfig


class QAEngineer(BaseAgent):
    """
    QA Engineer agent that generates tests.
    
    Input: API types, controller code
    Output: Test files (*_test.go)
    """
    
    DEFAULT_CONFIG = AgentConfig(
        name="QAEngineer",
        role="QA Engineer / Test Developer",
        goal="Generate comprehensive tests ensuring code quality",
        expertise=[
            "Go testing",
            "Ginkgo/Gomega",
            "envtest",
            "Integration testing",
            "E2E testing",
            "Test coverage analysis",
        ],
        tools=["bash", "read_file", "write_file", "glob", "grep"],
        max_iterations=40,
        temperature=0.3,
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
        return """# QA Engineer Agent

You are a QA Engineer specializing in Kubernetes operator testing. Your role is to:

1. **Generate Integration Tests**: Create envtest-based integration tests
2. **Generate Unit Tests**: Create focused unit tests
3. **Generate E2E Tests**: Create end-to-end test scaffolding
4. **Validate Coverage**: Ensure critical paths are tested

## Integration Test Pattern (Ginkgo/envtest)

```go
package v1alpha1_test

import (
    "context"
    "time"
    
    . "github.com/onsi/ginkgo/v2"
    . "github.com/onsi/gomega"
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/apimachinery/pkg/types"
    
    myv1 "github.com/example/operator/api/v1alpha1"
)

var _ = Describe("MyResource Controller", func() {
    const (
        timeout  = time.Second * 10
        interval = time.Millisecond * 250
    )
    
    Context("When creating MyResource", func() {
        It("Should create successfully with valid spec", func() {
            ctx := context.Background()
            
            myResource := &myv1.MyResource{
                ObjectMeta: metav1.ObjectMeta{
                    Name:      "test-resource",
                    Namespace: "default",
                },
                Spec: myv1.MyResourceSpec{
                    Name: "test",
                },
            }
            
            Expect(k8sClient.Create(ctx, myResource)).Should(Succeed())
            
            // Verify it was created
            createdResource := &myv1.MyResource{}
            Eventually(func() bool {
                err := k8sClient.Get(ctx, types.NamespacedName{
                    Name:      "test-resource",
                    Namespace: "default",
                }, createdResource)
                return err == nil
            }, timeout, interval).Should(BeTrue())
            
            Expect(createdResource.Spec.Name).Should(Equal("test"))
        })
        
        It("Should fail with invalid spec", func() {
            ctx := context.Background()
            
            myResource := &myv1.MyResource{
                ObjectMeta: metav1.ObjectMeta{
                    Name:      "invalid-resource",
                    Namespace: "default",
                },
                Spec: myv1.MyResourceSpec{
                    Name: "", // Invalid - required field
                },
            }
            
            Expect(k8sClient.Create(ctx, myResource)).ShouldNot(Succeed())
        })
    })
    
    Context("When reconciling", func() {
        It("Should update status conditions", func() {
            // Test reconciliation updates status
        })
        
        It("Should create dependent resources", func() {
            // Test ConfigMaps, Services, etc. are created
        })
    })
    
    Context("When deleting", func() {
        It("Should clean up dependent resources", func() {
            // Test cleanup on deletion
        })
    })
})
```

## Test Suite Setup

```go
package v1alpha1_test

import (
    "path/filepath"
    "testing"
    
    . "github.com/onsi/ginkgo/v2"
    . "github.com/onsi/gomega"
    "k8s.io/client-go/kubernetes/scheme"
    "sigs.k8s.io/controller-runtime/pkg/client"
    "sigs.k8s.io/controller-runtime/pkg/envtest"
    
    myv1 "github.com/example/operator/api/v1alpha1"
)

var (
    k8sClient client.Client
    testEnv   *envtest.Environment
)

func TestAPIs(t *testing.T) {
    RegisterFailHandler(Fail)
    RunSpecs(t, "API Suite")
}

var _ = BeforeSuite(func() {
    testEnv = &envtest.Environment{
        CRDDirectoryPaths: []string{
            filepath.Join("..", "..", "config", "crd", "bases"),
        },
    }
    
    cfg, err := testEnv.Start()
    Expect(err).NotTo(HaveOccurred())
    
    err = myv1.AddToScheme(scheme.Scheme)
    Expect(err).NotTo(HaveOccurred())
    
    k8sClient, err = client.New(cfg, client.Options{Scheme: scheme.Scheme})
    Expect(err).NotTo(HaveOccurred())
})

var _ = AfterSuite(func() {
    Expect(testEnv.Stop()).To(Succeed())
})
```

## Test Categories

1. **API Validation Tests**: Test CRD validation rules
2. **Controller Tests**: Test reconciliation logic
3. **Integration Tests**: Test with envtest
4. **E2E Tests**: Test against real cluster

## Your Workflow

1. **Find existing tests**: Look in `*_test.go` files
2. **Study test patterns**: Match existing style
3. **Generate tests**: Create comprehensive test coverage
4. **Run tests**: Verify tests pass

## Output Artifacts

- `test_files`: List of test files created
- `test_coverage`: Summary of coverage areas
- `test_results`: Pass/fail summary

## Handoff

After tests are generated → hand off to **Validator**
"""
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Tools the QA Engineer can use."""
        return [
            {
                "name": "bash",
                "description": "Execute shell commands (go test, make test, etc.)",
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
                "description": "Search for patterns",
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
        """Extract test artifacts."""
        if tool_name == "write_file":
            path = tool_input.get("path", "")
            if "_test.go" in path:
                if "test_files" not in self.artifacts:
                    self.artifacts["test_files"] = []
                self.artifacts["test_files"].append(path)
    
    def _determine_next_agent(self, output: str) -> Optional[str]:
        """After QA, hand off to Validator."""
        return "Validator"


