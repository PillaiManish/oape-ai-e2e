"""
Base Agent Class

All OAPE agents inherit from this base class. Each agent has:
- A specialized system prompt (role + expertise)
- Access to specific tools
- Its own iteration budget
- Ability to hand off to other agents
"""

import os
import json
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
import anthropic


class AgentStatus(Enum):
    """Agent execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    HANDED_OFF = "handed_off"


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    name: str
    role: str
    goal: str
    expertise: List[str]
    tools: List[str]  # Tool names this agent can use
    max_iterations: int = 50
    temperature: float = 0.7


@dataclass
class AgentMessage:
    """Message passed between agents."""
    from_agent: str
    to_agent: str
    content: str
    artifacts: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Result from an agent's execution."""
    agent_name: str
    status: AgentStatus
    output: str
    artifacts: Dict[str, Any] = field(default_factory=dict)
    iterations_used: int = 0
    next_agent: Optional[str] = None
    error: Optional[str] = None


class BaseAgent(ABC):
    """
    Base class for all OAPE agents.
    
    Each agent is a specialized LLM with:
    - Focused system prompt based on role
    - Subset of available tools
    - Own iteration budget
    - Handoff capability to other agents
    """
    
    def __init__(
        self,
        config: AgentConfig,
        working_dir: str,
        tool_executor: Any,
        stream_callback: Optional[Callable[[str], None]] = None,
    ):
        self.config = config
        self.working_dir = working_dir
        self.tool_executor = tool_executor
        self.stream_callback = stream_callback
        self.status = AgentStatus.PENDING
        self.iterations_used = 0
        self.artifacts: Dict[str, Any] = {}
        
        # Initialize Anthropic client for Vertex AI
        self.client = anthropic.AnthropicVertex(
            region=os.environ.get("CLOUD_ML_REGION", "us-east5"),
            project_id=os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID", "")
        )
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5@20250929")
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the specialized system prompt for this agent."""
        pass
    
    @abstractmethod
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return the tool definitions this agent can use."""
        pass
    
    def _stream(self, text: str):
        """Send text to stream callback if available."""
        if self.stream_callback:
            self.stream_callback(text)
    
    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        previous_artifacts: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """
        Execute the agent's task.
        
        Args:
            task: The task description for this agent
            context: Additional context from orchestrator
            previous_artifacts: Artifacts from previous agents
            
        Returns:
            AgentResult with output, artifacts, and next agent
        """
        self.status = AgentStatus.RUNNING
        self._stream(f"\n## 🤖 {self.config.name} Agent Started\n")
        self._stream(f"**Role:** {self.config.role}\n")
        self._stream(f"**Goal:** {self.config.goal}\n\n")
        
        # Build the initial message with context
        initial_message = self._build_initial_message(task, context, previous_artifacts)
        
        messages = [{"role": "user", "content": initial_message}]
        tools = self.get_tool_definitions()
        
        try:
            while self.iterations_used < self.config.max_iterations:
                self.iterations_used += 1
                self._stream(f"*Iteration {self.iterations_used}/{self.config.max_iterations}*\n")
                
                # Call the model
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=8192,
                    temperature=self.config.temperature,
                    system=self.system_prompt,
                    tools=tools if tools else None,
                    messages=messages,
                )
                
                # Process response
                assistant_content = []
                tool_calls = []
                text_output = ""
                
                for block in response.content:
                    if block.type == "text":
                        text_output += block.text
                        self._stream(block.text)
                        assistant_content.append({"type": "text", "text": block.text})
                    elif block.type == "tool_use":
                        tool_calls.append(block)
                        assistant_content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        })
                
                messages.append({"role": "assistant", "content": assistant_content})
                
                # Check for completion
                if response.stop_reason == "end_turn" and not tool_calls:
                    self.status = AgentStatus.COMPLETED
                    return AgentResult(
                        agent_name=self.config.name,
                        status=self.status,
                        output=text_output,
                        artifacts=self.artifacts,
                        iterations_used=self.iterations_used,
                        next_agent=self._determine_next_agent(text_output),
                    )
                
                # Execute tool calls
                if tool_calls:
                    tool_results = await self._execute_tools(tool_calls)
                    messages.append({"role": "user", "content": tool_results})
            
            # Max iterations reached
            self.status = AgentStatus.FAILED
            return AgentResult(
                agent_name=self.config.name,
                status=self.status,
                output=text_output,
                artifacts=self.artifacts,
                iterations_used=self.iterations_used,
                error=f"Max iterations ({self.config.max_iterations}) reached",
            )
            
        except Exception as e:
            self.status = AgentStatus.FAILED
            return AgentResult(
                agent_name=self.config.name,
                status=self.status,
                output="",
                artifacts=self.artifacts,
                iterations_used=self.iterations_used,
                error=str(e),
            )
    
    def _build_initial_message(
        self,
        task: str,
        context: Optional[Dict[str, Any]],
        previous_artifacts: Optional[Dict[str, Any]],
    ) -> str:
        """Build the initial message with task and context."""
        message_parts = [f"## Task\n{task}"]
        
        if context:
            message_parts.append(f"\n## Context\n```json\n{json.dumps(context, indent=2)}\n```")
        
        if previous_artifacts:
            message_parts.append(f"\n## Artifacts from Previous Agents\n```json\n{json.dumps(previous_artifacts, indent=2)}\n```")
        
        message_parts.append(f"\n## Working Directory\n{self.working_dir}")
        
        return "\n".join(message_parts)
    
    async def _execute_tools(self, tool_calls: List[Any]) -> List[Dict[str, Any]]:
        """Execute tool calls and return results."""
        results = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.name
            tool_input = tool_call.input
            
            self._stream(f"\n[tool: {tool_name}]\n")
            
            try:
                # Execute via tool executor
                result = await self.tool_executor.execute(
                    tool_name,
                    tool_input,
                    self.working_dir,
                )
                
                # Truncate long results
                result_str = str(result)
                if len(result_str) > 2000:
                    result_str = result_str[:2000] + "... (truncated)"
                
                self._stream(f"[result: {result_str[:200]}...]\n")
                
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": result_str,
                })
                
                # Store artifacts if relevant
                self._extract_artifacts(tool_name, tool_input, result)
                
            except Exception as e:
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": f"Error: {str(e)}",
                    "is_error": True,
                })
        
        return results
    
    def _extract_artifacts(self, tool_name: str, tool_input: Dict, result: Any):
        """Extract artifacts from tool results for passing to next agent."""
        # Override in subclasses to extract specific artifacts
        pass
    
    def _determine_next_agent(self, output: str) -> Optional[str]:
        """Determine which agent should run next based on output."""
        # Override in subclasses for custom routing logic
        return None


