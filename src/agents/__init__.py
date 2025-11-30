"""
Research Agent Modules

This package contains all research agent implementations including:
- Core agents (ResearchPlanner, ResearchSearcher, ResearchSynthesizer, ReportWriter, ResearchCritic)
- Base agent class with common functionality
- Specialized agents (DR Tulu, OLMo)
"""

# Import core agents from core_agents module
from src.core_agents import (
    ResearchPlanner,
    ResearchSearcher,
    ResearchSynthesizer,
    ReportWriter,
    ResearchCritic,
    get_llm,
    get_research_tools
)

# Import base class for agent development
from src.agents.base_agent import BaseResearchAgent

# Import specialized agents
from src.agents.dr_tulu_writer import DRTuluReportWriter
from src.agents.olmo_thinker import OLMoThinker

__all__ = [
    # Core agents
    'ResearchPlanner',
    'ResearchSearcher',
    'ResearchSynthesizer',
    'ReportWriter',
    'ResearchCritic',
    'get_llm',
    'get_research_tools',
    # Base class
    'BaseResearchAgent',
    # Specialized agents
    'DRTuluReportWriter',
    'OLMoThinker',
]
