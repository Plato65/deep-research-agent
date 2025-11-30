"""
Research Agent Modules

This package contains all research agent implementations including:
- Base agent class with common functionality
- Specialized agents (DR Tulu, OLMo)
- Core research agents (defined in ../agents.py for backward compatibility)
"""

# Import base class for agent development
from src.agents.base_agent import BaseResearchAgent

# Import specialized agents
from src.agents.dr_tulu_writer import DRTuluReportWriter
from src.agents.olmo_thinker import OLMoThinker

__all__ = [
    'BaseResearchAgent',
    'DRTuluReportWriter',
    'OLMoThinker',
]
