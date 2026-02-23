"""
Tool Adapter for Multi-Agent System

Wraps the existing tool executor for async execution by agents.
"""

import asyncio
import subprocess
import os
import glob as glob_module
from typing import Any, Dict


class AsyncToolExecutor:
    """
    Async wrapper for tool execution.
    
    Provides async methods for all tools that agents can use.
    """
    
    def __init__(self, working_dir: str):
        self.working_dir = working_dir
    
    async def execute(self, tool_name: str, tool_input: Dict[str, Any], working_dir: str = None) -> str:
        """
        Execute a tool by name with the given input.
        
        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool
            working_dir: Override working directory
            
        Returns:
            Tool execution result as string
        """
        cwd = working_dir or self.working_dir
        
        # Map tool names to methods
        tool_methods = {
            "bash": self._bash,
            "read_file": self._read_file,
            "write_file": self._write_file,
            "edit_file": self._edit_file,
            "glob": self._glob,
            "grep": self._grep,
            "web_fetch": self._web_fetch,
        }
        
        method = tool_methods.get(tool_name)
        if not method:
            return f"Error: Unknown tool '{tool_name}'"
        
        try:
            return await method(tool_input, cwd)
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"
    
    async def _bash(self, input: Dict[str, Any], cwd: str) -> str:
        """Execute a bash command."""
        command = input.get("command", "")
        if not command:
            return "Error: No command provided"
        
        # Run in executor to not block
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n[Exit code: {result.returncode}]"
        
        return output or "(no output)"
    
    async def _read_file(self, input: Dict[str, Any], cwd: str) -> str:
        """Read a file's contents."""
        path = input.get("path", "")
        if not path:
            return "Error: No path provided"
        
        # Handle relative paths
        if not os.path.isabs(path):
            path = os.path.join(cwd, path)
        
        if not os.path.exists(path):
            return f"Error: File not found: {path}"
        
        try:
            with open(path, "r") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    async def _write_file(self, input: Dict[str, Any], cwd: str) -> str:
        """Write content to a file."""
        path = input.get("path", "")
        content = input.get("content", "")
        
        if not path:
            return "Error: No path provided"
        
        # Handle relative paths
        if not os.path.isabs(path):
            path = os.path.join(cwd, path)
        
        # Create directories if needed
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        try:
            with open(path, "w") as f:
                f.write(content)
            return f"Successfully wrote to {path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"
    
    async def _edit_file(self, input: Dict[str, Any], cwd: str) -> str:
        """Edit a file using search/replace."""
        path = input.get("path", "")
        old_string = input.get("old_string", "")
        new_string = input.get("new_string", "")
        
        if not path:
            return "Error: No path provided"
        if not old_string:
            return "Error: No old_string provided"
        
        # Handle relative paths
        if not os.path.isabs(path):
            path = os.path.join(cwd, path)
        
        if not os.path.exists(path):
            return f"Error: File not found: {path}"
        
        try:
            with open(path, "r") as f:
                content = f.read()
            
            if old_string not in content:
                return f"Error: String not found in file: {old_string[:100]}..."
            
            # Count occurrences
            count = content.count(old_string)
            if count > 1:
                return f"Error: String found {count} times, must be unique. Add more context."
            
            new_content = content.replace(old_string, new_string, 1)
            
            with open(path, "w") as f:
                f.write(new_content)
            
            return f"Successfully edited {path}"
        except Exception as e:
            return f"Error editing file: {str(e)}"
    
    async def _glob(self, input: Dict[str, Any], cwd: str) -> str:
        """Find files matching a glob pattern."""
        pattern = input.get("pattern", "")
        if not pattern:
            return "Error: No pattern provided"
        
        # Make pattern relative to cwd
        full_pattern = os.path.join(cwd, pattern)
        
        matches = glob_module.glob(full_pattern, recursive=True)
        
        if not matches:
            return f"No files found matching: {pattern}"
        
        # Make paths relative to cwd
        relative_matches = [os.path.relpath(m, cwd) for m in matches]
        
        return "\n".join(relative_matches)
    
    async def _grep(self, input: Dict[str, Any], cwd: str) -> str:
        """Search for a pattern in files."""
        pattern = input.get("pattern", "")
        path = input.get("path", ".")
        
        if not pattern:
            return "Error: No pattern provided"
        
        # Use ripgrep if available, otherwise grep
        command = f"rg -n '{pattern}' {path} 2>/dev/null || grep -rn '{pattern}' {path} 2>/dev/null"
        
        result = await self._bash({"command": command}, cwd)
        
        if not result or result == "(no output)":
            return f"No matches found for pattern: {pattern}"
        
        return result
    
    async def _web_fetch(self, input: Dict[str, Any], cwd: str) -> str:
        """Fetch content from a URL."""
        url = input.get("url", "")
        if not url:
            return "Error: No URL provided"
        
        # Use curl to fetch
        command = f"curl -sL '{url}' | head -c 50000"
        
        return await self._bash({"command": command}, cwd)

