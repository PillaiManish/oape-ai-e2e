"""
OAPE Multi-Agent System

This module implements a MetaGPT-inspired multi-agent architecture for
operator development automation. Each agent has specialized roles and
responsibilities, working together to complete complex tasks.

Agent Hierarchy:
    Orchestrator
    ├── Architect (Design & Planning)
    ├── APIEngineer (API Types)
    ├── ControllerEngineer (Reconcilers)
    ├── QAEngineer (Tests)
    └── Validator (Build & Lint)
"""

from .base import BaseAgent, AgentConfig, AgentMessage, AgentResult
from .orchestrator import Orchestrator
from .architect import Architect
from .api_engineer import APIEngineer
from .controller_engineer import ControllerEngineer
from .qa_engineer import QAEngineer
from .validator import Validator

__all__ = [
    "BaseAgent",
    "AgentConfig", 
    "AgentMessage",
    "AgentResult",
    "Orchestrator",
    "Architect",
    "APIEngineer",
    "ControllerEngineer",
    "QAEngineer",
    "Validator",
]


