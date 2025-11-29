"""
Base class for research agents with common functionality.

Eliminates code duplication across all agent classes.
"""

import logging
import subprocess
from typing import Optional
from src.config import config
from src.llm import get_llm

logger = logging.getLogger(__name__)


class BaseResearchAgent:
    """Base class for all research agents with lazy loading and memory management."""

    def __init__(
        self,
        agent_name: str,
        model_override: Optional[str] = None,
        temperature: Optional[float] = None,
        use_tools: bool = False
    ):
        """Initialize base research agent.

        Args:
            agent_name: Name of the agent (for logging)
            model_override: Specific model to use (overrides config)
            temperature: LLM temperature (overrides config)
            use_tools: Whether this agent uses tools
        """
        self.agent_name = agent_name
        self.model_name = model_override or self._get_default_model_name()
        self.temperature = temperature if temperature is not None else config.llm_temperature
        self.llm = None  # Lazy loading
        self.tools = None
        self.use_tools = use_tools
        self.max_retries = config.max_retries

        logger.info(f"{agent_name} initialized (lazy load: {self.model_name})")

    def _get_default_model_name(self) -> str:
        """Get default model name for this agent. Override in subclasses."""
        return config.model_name

    def _ensure_llm_loaded(self):
        """Ensure LLM is loaded (lazy loading pattern)."""
        if self.llm is None:
            logger.info(f"Loading {self.agent_name} LLM: {self.model_name}")
            self.llm = get_llm(temperature=self.temperature, model_override=self.model_name)

    def unload_model(self):
        """Unload the LLM to free memory (only works with Ollama)."""
        if self.llm is not None and config.model_provider == "ollama":
            try:
                subprocess.run(
                    ["ollama", "stop", self.model_name],
                    check=False,
                    capture_output=True
                )
                logger.info(f"Unloaded {self.agent_name} model: {self.model_name}")
            except Exception as e:
                logger.debug(f"Could not unload model: {e}")
            self.llm = None
