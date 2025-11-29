"""
Base Agent Class

Provides common functionality for all research agents including lazy loading,
model unloading, and consistent error handling patterns.
"""

import logging
import subprocess
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Any

from src.config import config

logger = logging.getLogger(__name__)


class BaseResearchAgent(ABC):
    """Abstract base class for all research agents.

    Provides:
    - Lazy LLM loading with configurable model selection
    - Safe model unloading with comprehensive error handling
    - Consistent retry patterns
    - Logging infrastructure

    Subclasses must implement their specific research operations.
    """

    def __init__(self, model_name: Optional[str] = None):
        """Initialize base agent.

        Args:
            model_name: Model name to use. If None, uses config.model_name
        """
        self.model_name = model_name or config.model_name
        self.llm = None
        self.max_retries = config.max_retries
        logger.debug(f"{self.__class__.__name__} initialized with model: {self.model_name}")

    def _ensure_llm_loaded(self, temperature: Optional[float] = None):
        """Ensure LLM is loaded (lazy loading pattern).

        Only loads the LLM on first use to optimize memory usage.
        Supports per-stage model configuration.

        Args:
            temperature: Optional temperature override. If None, uses default
                        for this agent's operation type.

        Note:
            This method is synchronous. For async operations, load before
            entering async context.
        """
        if self.llm is not None:
            return

        logger.info(f"Loading {self.__class__.__name__} LLM: {self.model_name}")

        # Import here to avoid circular dependency
        from src.agents import get_llm

        self.llm = get_llm(
            temperature=temperature,
            model_override=self.model_name
        )

    async def unload_model_async(self):
        """Asynchronously unload the LLM to free memory.

        Uses proper error handling and timeout to prevent hanging.
        Only attempts to unload Ollama models as other providers
        handle memory automatically.

        Safe to call multiple times - will only unload if model is loaded.

        Returns:
            True if model was unloaded, False if no action taken

        Raises:
            No exceptions - all errors are logged and suppressed
        """
        if self.llm is None:
            return False

        # Only unload for Ollama - other providers manage memory automatically
        if config.model_provider != "ollama":
            self.llm = None
            return True

        try:
            # Run subprocess with timeout to prevent hanging
            result = await asyncio.create_subprocess_exec(
                "ollama", "stop", self.model_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    result.communicate(),
                    timeout=5.0
                )

                if result.returncode == 0:
                    logger.info(
                        f"Successfully unloaded {self.__class__.__name__} model: {self.model_name}"
                    )
                else:
                    logger.warning(
                        f"Ollama stop returned non-zero exit code: {result.returncode}",
                        extra={'stderr': stderr.decode() if stderr else None}
                    )

            except asyncio.TimeoutError:
                logger.warning(
                    f"Timeout unloading model {self.model_name} - killing process"
                )
                try:
                    result.kill()
                    await result.wait()
                except Exception as e:
                    logger.debug(f"Error killing unload process: {e}")

        except FileNotFoundError:
            logger.warning(
                "Ollama command not found - ensure ollama is installed and in PATH",
                extra={'provider': config.model_provider, 'model': self.model_name}
            )

        except Exception as e:
            logger.warning(
                f"Unexpected error unloading model: {type(e).__name__}: {e}",
                extra={'model': self.model_name}
            )

        finally:
            # Always clear the LLM reference
            self.llm = None

        return True

    def unload_model(self):
        """Synchronous wrapper for model unloading.

        For use in synchronous contexts. Uses subprocess.run with timeout.
        Less preferred than unload_model_async() but necessary for
        compatibility with synchronous code paths.

        Returns:
            True if model was unloaded, False if no action taken
        """
        if self.llm is None:
            return False

        # Only unload for Ollama
        if config.model_provider != "ollama":
            self.llm = None
            return True

        try:
            result = subprocess.run(
                ["ollama", "stop", self.model_name],
                timeout=5.0,
                capture_output=True,
                text=True,
                check=True  # Raise CalledProcessError on non-zero exit
            )

            logger.info(
                f"Successfully unloaded {self.__class__.__name__} model: {self.model_name}"
            )

        except subprocess.CalledProcessError as e:
            logger.warning(
                f"Ollama stop failed with exit code {e.returncode}",
                extra={
                    'stderr': e.stderr,
                    'stdout': e.stdout,
                    'model': self.model_name
                }
            )

        except subprocess.TimeoutExpired:
            logger.warning(
                f"Timeout waiting for ollama to stop model {self.model_name}"
            )

        except FileNotFoundError:
            logger.warning(
                "Ollama command not found - ensure ollama is installed and in PATH",
                extra={'provider': config.model_provider}
            )

        except Exception as e:
            logger.warning(
                f"Unexpected error unloading model: {type(e).__name__}: {e}",
                extra={'model': self.model_name}
            )

        finally:
            # Always clear the LLM reference
            self.llm = None

        return True

    @abstractmethod
    async def _execute_primary_operation(self, *args, **kwargs) -> Any:
        """Execute the agent's primary operation.

        Subclasses must implement this method with their specific logic.

        Example:
            For ResearchPlanner: async def _execute_primary_operation(self, state):
                return await self._generate_plan(state)
        """
        pass
