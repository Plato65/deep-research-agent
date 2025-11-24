"""Observability and telemetry system for research workflow.

Provides structured logging, per-agent metrics, and quality degradation alerts.
"""

import structlog
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import json


# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)


class TelemetryTracker:
    """Tracks telemetry and metrics for research workflow."""

    def __init__(self, output_dir: str = "./outputs/telemetry"):
        """Initialize telemetry tracker.

        Args:
            output_dir: Directory to store telemetry logs
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.logger = structlog.get_logger()
        self.session_start = datetime.now()
        self.session_id = self.session_start.strftime("%Y%m%d_%H%M%S")

        # Metrics storage
        self.metrics: Dict[str, Any] = {
            "session_id": self.session_id,
            "start_time": self.session_start.isoformat(),
            "agents": {},
            "quality_alerts": [],
            "errors": []
        }

    def log_agent_start(self, agent_name: str, **context):
        """Log agent execution start.

        Args:
            agent_name: Name of the agent
            **context: Additional context to log
        """
        self.logger.info(
            "agent_started",
            agent=agent_name,
            timestamp=datetime.now().isoformat(),
            **context
        )

        if agent_name not in self.metrics["agents"]:
            self.metrics["agents"][agent_name] = {
                "executions": 0,
                "total_duration": 0,
                "errors": 0
            }

    def log_agent_complete(
        self,
        agent_name: str,
        duration: float,
        **metrics
    ):
        """Log agent execution completion with metrics.

        Args:
            agent_name: Name of the agent
            duration: Execution duration in seconds
            **metrics: Agent-specific metrics
        """
        self.logger.info(
            "agent_completed",
            agent=agent_name,
            duration_seconds=round(duration, 2),
            timestamp=datetime.now().isoformat(),
            **metrics
        )

        # Update aggregate metrics
        if agent_name in self.metrics["agents"]:
            self.metrics["agents"][agent_name]["executions"] += 1
            self.metrics["agents"][agent_name]["total_duration"] += duration
            self.metrics["agents"][agent_name]["last_metrics"] = metrics

    def log_search_metrics(
        self,
        query: str,
        sources_found: int,
        avg_credibility: Optional[float] = None,
        dedup_filtered: int = 0,
        api_used: str = "unknown",
        query_type: str = "general"
    ):
        """Log search operation metrics.

        Args:
            query: Search query executed
            sources_found: Number of sources found
            avg_credibility: Average credibility score
            dedup_filtered: Number of duplicates filtered
            api_used: Search API used
            query_type: Type of query
        """
        self.logger.info(
            "search_completed",
            query=query[:100],
            sources_found=sources_found,
            avg_credibility=round(avg_credibility, 1) if avg_credibility else None,
            dedup_filtered=dedup_filtered,
            api_used=api_used,
            query_type=query_type,
            timestamp=datetime.now().isoformat()
        )

        # Check for quality alerts
        if sources_found < 5:
            self.alert_insufficient_sources(query, sources_found)

        if avg_credibility and avg_credibility < 50:
            self.alert_low_credibility(query, avg_credibility)

    def log_synthesis_metrics(
        self,
        findings_count: int,
        sources_used: int,
        avg_source_credibility: Optional[float] = None
    ):
        """Log synthesis operation metrics.

        Args:
            findings_count: Number of key findings extracted
            sources_used: Number of sources used
            avg_source_credibility: Average credibility of sources
        """
        self.logger.info(
            "synthesis_completed",
            findings_count=findings_count,
            sources_used=sources_used,
            avg_credibility=round(avg_source_credibility, 1) if avg_source_credibility else None,
            timestamp=datetime.now().isoformat()
        )

        # Check for quality alerts
        if findings_count < 3:
            self.alert_insufficient_findings(findings_count)

    def log_quality_validation(
        self,
        validation_results: Dict[str, Any],
        passed: bool
    ):
        """Log quality validation results.

        Args:
            validation_results: Results from QualityValidator
            passed: Whether validation passed
        """
        self.logger.info(
            "quality_validation",
            passed=passed,
            overall_score=validation_results.get("overall_score"),
            citation_coverage=validation_results.get("citations", {}).get("citation_coverage"),
            hallucination_risk=validation_results.get("hallucinations", {}).get("hallucination_risk"),
            freshness_score=validation_results.get("freshness", {}).get("freshness_score"),
            issues_count=len(validation_results.get("issues", [])),
            timestamp=datetime.now().isoformat()
        )

        if not passed:
            self.alert_quality_failure(validation_results)

    def log_model_operation(
        self,
        agent_name: str,
        operation: str,
        model_name: str,
        duration: Optional[float] = None
    ):
        """Log model loading/unloading operations.

        Args:
            agent_name: Name of the agent
            operation: Operation type (load/unload)
            model_name: Name of the model
            duration: Operation duration in seconds
        """
        self.logger.info(
            "model_operation",
            agent=agent_name,
            operation=operation,
            model=model_name,
            duration_seconds=round(duration, 2) if duration else None,
            timestamp=datetime.now().isoformat()
        )

    def log_error(
        self,
        component: str,
        error_type: str,
        message: str,
        **context
    ):
        """Log error with structured context.

        Args:
            component: Component where error occurred
            error_type: Type of error
            message: Error message
            **context: Additional context
        """
        self.logger.error(
            "error_occurred",
            component=component,
            error_type=error_type,
            message=message,
            timestamp=datetime.now().isoformat(),
            **context
        )

        self.metrics["errors"].append({
            "component": component,
            "type": error_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })

    # Alert methods

    def alert_insufficient_sources(self, query: str, count: int):
        """Alert for insufficient sources found.

        Args:
            query: The search query
            count: Number of sources found
        """
        self.logger.warning(
            "alert_insufficient_sources",
            alert_type="insufficient_sources",
            query=query[:100],
            sources_found=count,
            threshold=5,
            severity="medium",
            timestamp=datetime.now().isoformat()
        )

        self.metrics["quality_alerts"].append({
            "type": "insufficient_sources",
            "query": query[:100],
            "count": count,
            "timestamp": datetime.now().isoformat()
        })

    def alert_low_credibility(self, query: str, credibility: float):
        """Alert for low average credibility.

        Args:
            query: The search query
            credibility: Average credibility score
        """
        self.logger.warning(
            "alert_low_credibility",
            alert_type="low_credibility",
            query=query[:100],
            avg_credibility=round(credibility, 1),
            threshold=50,
            severity="medium",
            timestamp=datetime.now().isoformat()
        )

        self.metrics["quality_alerts"].append({
            "type": "low_credibility",
            "query": query[:100],
            "credibility": round(credibility, 1),
            "timestamp": datetime.now().isoformat()
        })

    def alert_insufficient_findings(self, count: int):
        """Alert for insufficient key findings.

        Args:
            count: Number of findings extracted
        """
        self.logger.warning(
            "alert_insufficient_findings",
            alert_type="insufficient_findings",
            findings_count=count,
            threshold=3,
            severity="high",
            timestamp=datetime.now().isoformat()
        )

        self.metrics["quality_alerts"].append({
            "type": "insufficient_findings",
            "count": count,
            "timestamp": datetime.now().isoformat()
        })

    def alert_quality_failure(self, validation_results: Dict[str, Any]):
        """Alert for quality validation failure.

        Args:
            validation_results: Validation results from QualityValidator
        """
        self.logger.error(
            "alert_quality_failure",
            alert_type="quality_validation_failed",
            overall_score=validation_results.get("overall_score"),
            issues=validation_results.get("issues", []),
            severity="critical",
            timestamp=datetime.now().isoformat()
        )

        self.metrics["quality_alerts"].append({
            "type": "quality_validation_failed",
            "score": validation_results.get("overall_score"),
            "issues": validation_results.get("issues", []),
            "timestamp": datetime.now().isoformat()
        })

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session metrics.

        Returns:
            Dictionary with session summary
        """
        session_duration = (datetime.now() - self.session_start).total_seconds()

        summary = {
            "session_id": self.session_id,
            "duration_seconds": round(session_duration, 2),
            "agents": self.metrics["agents"],
            "quality_alerts_count": len(self.metrics["quality_alerts"]),
            "errors_count": len(self.metrics["errors"]),
            "end_time": datetime.now().isoformat()
        }

        return summary

    def save_session_metrics(self):
        """Save session metrics to file."""
        summary = self.get_session_summary()

        output_file = self.output_dir / f"session_{self.session_id}.json"

        try:
            with open(output_file, 'w') as f:
                json.dump({
                    "summary": summary,
                    "detailed_metrics": self.metrics
                }, f, indent=2)

            self.logger.info(
                "session_metrics_saved",
                output_file=str(output_file),
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            self.logger.error(
                "failed_to_save_metrics",
                error=str(e),
                timestamp=datetime.now().isoformat()
            )


# Global telemetry tracker instance
_telemetry_tracker: Optional[TelemetryTracker] = None


def get_telemetry() -> TelemetryTracker:
    """Get or create global telemetry tracker.

    Returns:
        TelemetryTracker instance
    """
    global _telemetry_tracker

    if _telemetry_tracker is None:
        _telemetry_tracker = TelemetryTracker()

    return _telemetry_tracker


def reset_telemetry():
    """Reset global telemetry tracker (useful for testing)."""
    global _telemetry_tracker
    _telemetry_tracker = None
