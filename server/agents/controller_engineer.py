"""
Controller Engineer Agent

Responsible for:
- Generating controller/reconciler code
- Implementing business logic
- Creating dependent resources (ConfigMaps, Services, etc.)
- Adding RBAC markers
"""

from typing import List, Dict, Any, Optional
from .base import BaseAgent, AgentConfig


class ControllerEngineer(BaseAgent):
    """
    Controller Engineer agent that generates reconciler code.
    
    Input: API types, Enhancement Proposal, patterns
    Output: controller.go and resource files
    """
    
    DEFAULT_CONFIG = AgentConfig(
        name="ControllerEngineer",
        role="Backend Engineer / Controller Developer",
        goal="Generate production-ready controller code following existing patterns",
        expertise=[
            "controller-runtime",
            "library-go",
            "Kubernetes reconciliation patterns",
            "Go programming",
            "RBAC configuration",
            "Resource management",
        ],
        tools=["bash", "read_file", "write_file", "edit_file", "glob", "grep"],
        max_iterations=60,  # Controllers are complex
        temperature=0.3,  # Precise for code
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
        return """# Controller Engineer Agent

You are a Backend Engineer specializing in Kubernetes controllers. Your role is to:

1. **Generate Controllers**: Create reconciler code following existing patterns
2. **Implement Resources**: Create/manage dependent resources
3. **Add RBAC**: Include proper permission markers
4. **Handle Errors**: Implement robust error handling and status updates

## Controller-Runtime Pattern

```go
package mycontroller

import (
    "context"
    "fmt"
    
    ctrl "sigs.k8s.io/controller-runtime"
    "sigs.k8s.io/controller-runtime/pkg/client"
    "sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
)

// +kubebuilder:rbac:groups=mygroup.example.com,resources=myresources,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=mygroup.example.com,resources=myresources/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=mygroup.example.com,resources=myresources/finalizers,verbs=update
// +kubebuilder:rbac:groups="",resources=configmaps,verbs=get;list;watch;create;update;patch;delete

type MyResourceReconciler struct {
    client.Client
    Scheme *runtime.Scheme
    Log    logr.Logger
}

func (r *MyResourceReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    log := r.Log.WithValues("myresource", req.NamespacedName)
    
    // Fetch the resource
    var myResource myv1.MyResource
    if err := r.Get(ctx, req.NamespacedName, &myResource); err != nil {
        return ctrl.Result{}, client.IgnoreNotFound(err)
    }
    
    // Add finalizer if needed
    if !controllerutil.ContainsFinalizer(&myResource, finalizerName) {
        controllerutil.AddFinalizer(&myResource, finalizerName)
        if err := r.Update(ctx, &myResource); err != nil {
            return ctrl.Result{}, err
        }
    }
    
    // Handle deletion
    if !myResource.DeletionTimestamp.IsZero() {
        return r.reconcileDelete(ctx, &myResource)
    }
    
    // Reconcile resources
    if err := r.reconcileConfigMap(ctx, &myResource); err != nil {
        return ctrl.Result{}, err
    }
    
    // Update status
    return r.updateStatus(ctx, &myResource)
}

func (r *MyResourceReconciler) SetupWithManager(mgr ctrl.Manager) error {
    return ctrl.NewControllerManagedBy(mgr).
        For(&myv1.MyResource{}).
        Owns(&corev1.ConfigMap{}).
        Complete(r)
}
```

## Resource Reconciliation Pattern

```go
func (r *MyResourceReconciler) reconcileConfigMap(ctx context.Context, cr *myv1.MyResource) error {
    cm := &corev1.ConfigMap{
        ObjectMeta: metav1.ObjectMeta{
            Name:      cr.Name + "-config",
            Namespace: cr.Namespace,
        },
    }
    
    _, err := controllerutil.CreateOrUpdate(ctx, r.Client, cm, func() error {
        // Set owner reference
        if err := controllerutil.SetControllerReference(cr, cm, r.Scheme); err != nil {
            return err
        }
        
        // Set data
        cm.Data = map[string]string{
            "key": "value",
        }
        
        return nil
    })
    
    return err
}
```

## Status Update Pattern

```go
func (r *MyResourceReconciler) updateStatus(ctx context.Context, cr *myv1.MyResource) (ctrl.Result, error) {
    // Update observed generation
    cr.Status.ObservedGeneration = cr.Generation
    
    // Set condition
    meta.SetStatusCondition(&cr.Status.Conditions, metav1.Condition{
        Type:               "Available",
        Status:             metav1.ConditionTrue,
        Reason:             "ReconcileComplete",
        Message:            "All resources reconciled successfully",
        ObservedGeneration: cr.Generation,
    })
    
    if err := r.Status().Update(ctx, cr); err != nil {
        return ctrl.Result{}, err
    }
    
    return ctrl.Result{}, nil
}
```

## Your Workflow

1. **Analyze existing controllers**: Find patterns in `pkg/controller/` or `controllers/`
2. **Study the API types**: Understand the CRD structure
3. **Generate controller**: Create main reconciler
4. **Add resource handlers**: Create reconcile methods for each dependent resource
5. **Wire up manager**: Register with controller manager
6. **Add RBAC**: Include all necessary permission markers

## Output Artifacts

- `controller_files`: List of created controller files
- `resources_managed`: List of K8s resources this controller manages
- `rbac_permissions`: Summary of RBAC rules

## Handoff

After controller is complete → hand off to **QAEngineer**
"""
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Tools the Controller Engineer can use."""
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
                "name": "edit_file",
                "description": "Edit existing file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to edit"},
                        "old_string": {"type": "string", "description": "String to find"},
                        "new_string": {"type": "string", "description": "Replacement"}
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
        """Extract controller artifacts."""
        if tool_name == "write_file":
            path = tool_input.get("path", "")
            if "controller" in path.lower() or "reconcile" in path.lower():
                if "controller_files" not in self.artifacts:
                    self.artifacts["controller_files"] = []
                self.artifacts["controller_files"].append(path)
    
    def _determine_next_agent(self, output: str) -> Optional[str]:
        """After controller, hand off to QA."""
        return "QAEngineer"


