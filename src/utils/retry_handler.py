"""
Retry Handler Utility

Provides consistent retry logic and error handling across all agents.
Centralizes retry patterns to ensure uniform behavior and better error tracking.
"""

import asyncio
import logging
from typing import Callable, Any, Optional, Dict
from functools import wraps

logger = logging.getLogger(__name__)


class RetryHandler:
    """Handles retry logic with exponential backoff and comprehensive error tracking."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 2.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    ):
        """Initialize retry handler.

        Args:
            max_retries: Maximum number of retry attempts (default: 3)
            base_delay: Base delay in seconds for exponential backoff (default: 2.0)
            max_delay: Maximum delay between retries in seconds (default: 60.0)
            exponential_base: Base for exponential backoff calculation (default: 2.0)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt using exponential backoff.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds, capped at max_delay
        """
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)

    async def execute_with_retry(
        self,
        operation_name: str,
        async_func: Callable,
        on_final_failure: Optional[Callable[[Exception], Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs
    ) -> Any:
        """Execute async operation with retry logic and comprehensive error handling.

        Args:
            operation_name: Human-readable name of the operation (for logging)
            async_func: Async function to execute
            on_final_failure: Optional callback for final failure (receives exception)
            context: Optional context dict for logging
            *args: Positional arguments for async_func
            **kwargs: Keyword arguments for async_func

        Returns:
            Result from async_func if successful

        Raises:
            Exception: Re-raises the last exception if all retries exhausted
                      and on_final_failure is not provided

        Example:
            >>> handler = RetryHandler(max_retries=3)
            >>> result = await handler.execute_with_retry(
            ...     "database_query",
            ...     db.query,
            ...     context={'table': 'users'},
            ...     query="SELECT * FROM users"
            ... )
        """
        last_exception = None
        context = context or {}

        for attempt in range(self.max_retries):
            try:
                return await async_func(*args, **kwargs)

            except Exception as e:
                last_exception = e

                logger.warning(
                    f"{operation_name} attempt {attempt + 1}/{self.max_retries} failed",
                    extra={
                        'operation': operation_name,
                        'attempt': attempt + 1,
                        'max_attempts': self.max_retries,
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        **context
                    }
                )

                # If this was the last attempt
                if attempt == self.max_retries - 1:
                    logger.error(
                        f"{operation_name} failed after {self.max_retries} attempts",
                        extra={
                            'operation': operation_name,
                            'total_attempts': self.max_retries,
                            'final_error': str(e),
                            **context
                        },
                        exc_info=True
                    )

                    # Call failure callback if provided
                    if on_final_failure:
                        return on_final_failure(e)

                    # Otherwise re-raise
                    raise

                # Calculate and apply backoff delay
                delay = self.calculate_delay(attempt)
                logger.debug(
                    f"Retrying {operation_name} after {delay:.1f}s delay",
                    extra={
                        'operation': operation_name,
                        'delay_seconds': delay,
                        'next_attempt': attempt + 2
                    }
                )
                await asyncio.sleep(delay)

        # Should never reach here, but just in case
        if last_exception:
            raise last_exception

    def execute_sync_with_retry(
        self,
        operation_name: str,
        sync_func: Callable,
        on_final_failure: Optional[Callable[[Exception], Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs
    ) -> Any:
        """Execute synchronous operation with retry logic.

        Args:
            operation_name: Human-readable name of the operation
            sync_func: Synchronous function to execute
            on_final_failure: Optional callback for final failure
            context: Optional context dict for logging
            *args: Positional arguments for sync_func
            **kwargs: Keyword arguments for sync_func

        Returns:
            Result from sync_func if successful

        Raises:
            Exception: Re-raises the last exception if all retries exhausted
        """
        import time
        last_exception = None
        context = context or {}

        for attempt in range(self.max_retries):
            try:
                return sync_func(*args, **kwargs)

            except Exception as e:
                last_exception = e

                logger.warning(
                    f"{operation_name} attempt {attempt + 1}/{self.max_retries} failed",
                    extra={
                        'operation': operation_name,
                        'attempt': attempt + 1,
                        'max_attempts': self.max_retries,
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        **context
                    }
                )

                if attempt == self.max_retries - 1:
                    logger.error(
                        f"{operation_name} failed after {self.max_retries} attempts",
                        extra={
                            'operation': operation_name,
                            'total_attempts': self.max_retries,
                            'final_error': str(e),
                            **context
                        },
                        exc_info=True
                    )

                    if on_final_failure:
                        return on_final_failure(e)
                    raise

                delay = self.calculate_delay(attempt)
                logger.debug(f"Retrying {operation_name} after {delay:.1f}s delay")
                time.sleep(delay)

        if last_exception:
            raise last_exception


def with_retry(
    operation_name: str = None,
    max_retries: int = 3,
    base_delay: float = 2.0,
    on_failure: Optional[Callable] = None
):
    """Decorator for adding retry logic to async functions.

    Args:
        operation_name: Name for logging (defaults to function name)
        max_retries: Maximum retry attempts
        base_delay: Base delay for exponential backoff
        on_failure: Callback on final failure

    Example:
        >>> @with_retry(operation_name="fetch_data", max_retries=5)
        >>> async def fetch_data(url: str):
        >>>     async with httpx.AsyncClient() as client:
        >>>         return await client.get(url)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            handler = RetryHandler(max_retries=max_retries, base_delay=base_delay)
            op_name = operation_name or func.__name__

            return await handler.execute_with_retry(
                op_name,
                func,
                on_final_failure=on_failure,
                *args,
                **kwargs
            )

        return wrapper
    return decorator


# Convenience function for quick retries
async def retry_async(
    func: Callable,
    max_retries: int = 3,
    operation_name: str = None,
    *args,
    **kwargs
) -> Any:
    """Convenience function for quick async retries.

    Args:
        func: Async function to retry
        max_retries: Maximum attempts
        operation_name: Operation name for logging
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Example:
        >>> result = await retry_async(api.fetch, max_retries=5, url="https://api.example.com")
    """
    handler = RetryHandler(max_retries=max_retries)
    op_name = operation_name or getattr(func, '__name__', 'unknown_operation')

    return await handler.execute_with_retry(
        op_name,
        func,
        *args,
        **kwargs
    )
