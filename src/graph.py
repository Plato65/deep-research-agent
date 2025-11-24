"""LangGraph workflow for deep research following best practices.

Nodes return dict updates that LangGraph automatically merges into state.
This is the recommended pattern per LangGraph documentation.
"""

import time
from langgraph.graph import StateGraph, START, END
from src.state import ResearchState
from src.agents import ResearchPlanner, ResearchSearcher, ResearchSynthesizer, ReportWriter
from src.utils.cache import ResearchCache
from src.utils.quality_checks import QualityValidator
from src.utils.telemetry import get_telemetry
from src.config import config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_research_graph():
    """Create the research workflow graph with enhanced routing and error handling."""

    # Initialize agents (with lazy loading)
    planner = ResearchPlanner()
    searcher = ResearchSearcher()
    synthesizer = ResearchSynthesizer()
    writer = ReportWriter(citation_style=config.citation_style)
    quality_validator = QualityValidator()
    telemetry = get_telemetry()

    # Wrapper functions to handle model unloading between stages with telemetry
    async def plan_with_unload(state: ResearchState) -> dict:
        """Plan and unload model after completion."""
        telemetry.log_agent_start("planner", topic=state.research_topic)
        start_time = time.time()

        result = await planner.plan(state)
        planner.unload_model()  # Free memory before next stage

        duration = time.time() - start_time
        telemetry.log_agent_complete(
            "planner",
            duration=duration,
            objectives=len(result.get("plan", {}).objectives) if result.get("plan") else 0,
            search_queries=len(result.get("plan", {}).search_queries) if result.get("plan") else 0
        )

        return result

    async def search_with_unload(state: ResearchState) -> dict:
        """Search and unload model after completion."""
        telemetry.log_agent_start("searcher", queries=len(state.plan.search_queries))
        start_time = time.time()

        result = await searcher.search(state)
        searcher.unload_model()  # Free memory before next stage

        duration = time.time() - start_time
        sources_found = len(result.get("search_results", []))

        # Calculate average credibility
        avg_credibility = None
        if state.credibility_scores:
            avg_credibility = sum(s.get("score", 0) for s in state.credibility_scores) / len(state.credibility_scores)

        telemetry.log_agent_complete(
            "searcher",
            duration=duration,
            sources_found=sources_found,
            avg_credibility=avg_credibility
        )

        return result

    async def synthesize_with_unload(state: ResearchState) -> dict:
        """Synthesize and unload model after completion."""
        telemetry.log_agent_start("synthesizer", sources=len(state.search_results))
        start_time = time.time()

        result = await synthesizer.synthesize(state)
        synthesizer.unload_model()  # Free memory before next stage

        duration = time.time() - start_time
        findings = len(result.get("key_findings", []))

        # Calculate average source credibility
        avg_credibility = None
        if state.credibility_scores:
            avg_credibility = sum(s.get("score", 0) for s in state.credibility_scores) / len(state.credibility_scores)

        telemetry.log_agent_complete(
            "synthesizer",
            duration=duration,
            findings=findings
        )

        telemetry.log_synthesis_metrics(
            findings_count=findings,
            sources_used=len(state.search_results),
            avg_source_credibility=avg_credibility
        )

        return result

    async def write_report_final(state: ResearchState) -> dict:
        """Write report (no unload - final stage)."""
        telemetry.log_agent_start("writer", findings=len(state.key_findings))
        start_time = time.time()

        result = await writer.write_report(state)

        duration = time.time() - start_time
        report_length = len(result.get("final_report", ""))

        telemetry.log_agent_complete(
            "writer",
            duration=duration,
            report_length=report_length,
            sections=len(result.get("report_sections", []))
        )

        # Don't unload - this is the final stage
        return result

    async def validate_quality(state: ResearchState) -> dict:
        """Validate report quality."""
        if not state.final_report:
            logger.warning("No report to validate")
            return {}

        telemetry.log_agent_start("quality_validator")
        start_time = time.time()

        # Run quality validation
        validation_results = await quality_validator.validate_report(
            report=state.final_report,
            sources=state.search_results,
            mode=config.research_mode,
            strict=False  # Non-strict mode for production
        )

        duration = time.time() - start_time

        # Log validation results
        telemetry.log_agent_complete(
            "quality_validator",
            duration=duration,
            passed=validation_results["passed"],
            overall_score=validation_results["overall_score"]
        )

        telemetry.log_quality_validation(
            validation_results=validation_results,
            passed=validation_results["passed"]
        )

        # Log detailed results
        logger.info(f"Quality validation: {'PASSED' if validation_results['passed'] else 'FAILED'}")
        logger.info(f"  Overall score: {validation_results['overall_score']}/100")
        logger.info(f"  Citation coverage: {validation_results['citations']['citation_coverage']}%")
        logger.info(f"  Hallucination risk: {validation_results['hallucinations']['hallucination_risk']}")
        logger.info(f"  Freshness score: {validation_results['freshness']['freshness_score']}%")

        if validation_results.get("issues"):
            logger.warning(f"  Quality issues: {len(validation_results['issues'])}")
            for issue in validation_results["issues"][:3]:  # Log first 3 issues
                logger.warning(f"    - {issue}")

        # Store validation results in state
        return {"quality_score": validation_results}


    # Define the graph
    workflow = StateGraph(ResearchState)

    # Add nodes with model unloading wrappers and quality validation
    workflow.add_node("plan", plan_with_unload)
    workflow.add_node("search", search_with_unload)
    workflow.add_node("synthesize", synthesize_with_unload)
    workflow.add_node("write_report", write_report_final)
    workflow.add_node("validate_quality", validate_quality)
    
    # Define entry point using START constant (v1.0 best practice)
    workflow.add_edge(START, "plan")
    
    def should_continue_after_plan(state: ResearchState) -> str:
        """Validate planning output and route appropriately."""
        if state.error:
            logger.error(f"Planning failed: {state.error}")
            return END
        
        if not state.plan or not state.plan.search_queries:
            logger.error("No search queries generated in plan")
            state.error = "Failed to generate valid research plan"
            return END
            
        logger.info(f"Plan validated: {len(state.plan.search_queries)} queries")
        return "search"
    
    def should_continue_after_search(state: ResearchState) -> str:
        """Validate search results and route appropriately."""
        if state.error:
            logger.error(f"Search failed: {state.error}")
            return END
        
        if not state.search_results:
            logger.warning("No search results found")
            state.error = "No search results available for synthesis"
            return END
        
        # Check minimum threshold
        if len(state.search_results) < 2:
            logger.warning(f"Insufficient search results: {len(state.search_results)}")
            state.error = "Insufficient data for comprehensive research"
            return END
            
        logger.info(f"Search validated: {len(state.search_results)} results")
        return "synthesize"
    
    def should_continue_after_synthesize(state: ResearchState) -> str:
        """Validate synthesis output and route appropriately."""
        if state.error:
            logger.error(f"Synthesis failed: {state.error}")
            return END
        
        if not state.key_findings:
            logger.warning("No key findings extracted")
            state.error = "Failed to extract findings from search results"
            return END
        
        logger.info(f"Synthesis validated: {len(state.key_findings)} findings")
        return "write_report"
    
    def should_continue_after_report(state: ResearchState) -> str:
        """Validate final report and route to quality validation."""
        if state.error:
            logger.error(f"Report generation failed: {state.error}")
            return END
        elif not state.final_report:
            logger.error("No report generated")
            state.error = "Report generation produced no output"
            return END
        else:
            logger.info("Report generation complete - proceeding to quality validation")
            return "validate_quality"

    def should_continue_after_validation(state: ResearchState) -> str:
        """Complete workflow after quality validation."""
        if state.error:
            logger.error(f"Validation failed: {state.error}")
        elif state.quality_score:
            logger.info(f"Quality validation complete: score={state.quality_score.get('overall_score', 'N/A')}")
        return END
    
    # Add conditional edges with validation
    workflow.add_conditional_edges(
        "plan",
        should_continue_after_plan,
        {
            "search": "search",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "search",
        should_continue_after_search,
        {
            "synthesize": "synthesize",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "synthesize",
        should_continue_after_synthesize,
        {
            "write_report": "write_report",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "write_report",
        should_continue_after_report,
        {
            "validate_quality": "validate_quality",
            END: END
        }
    )

    workflow.add_conditional_edges(
        "validate_quality",
        should_continue_after_validation,
        {
            END: END
        }
    )
    
    # Compile the graph
    return workflow.compile()


async def run_research(topic: str, verbose: bool = True, use_cache: bool = True) -> dict:
    """Run the research workflow for a given topic.

    Args:
        topic: Research topic
        verbose: Enable verbose logging
        use_cache: Use cached results if available

    Returns the complete accumulated state as a dict.
    """
    logger.info(f"Starting research on: {topic}")

    # Initialize telemetry for this session
    telemetry = get_telemetry()

    # Check cache first
    cache = ResearchCache()
    if use_cache:
        cached_result = cache.get(topic)
        if cached_result:
            logger.info("Using cached research result")
            return cached_result

    # Initialize state
    initial_state = ResearchState(research_topic=topic)

    # Create and run the graph
    graph = create_research_graph()

    try:
        # Execute the workflow using invoke to get complete final state
        # Note: invoke runs once and returns the complete accumulated state
        final_state = await graph.ainvoke(initial_state)

        # Cache the result
        if use_cache and not final_state.get("error"):
            cache.set(topic, final_state)

        if verbose:
            logger.info("Workflow completed")
            if final_state.get("final_report"):
                logger.info(f"Report generated: {len(final_state['final_report'])} characters")

            # Display session summary
            session_summary = telemetry.get_session_summary()
            logger.info(f"Session summary:")
            logger.info(f"  Duration: {session_summary['duration_seconds']:.1f}s")
            logger.info(f"  Quality alerts: {session_summary['quality_alerts_count']}")
            logger.info(f"  Errors: {session_summary['errors_count']}")

        return final_state

    except Exception as e:
        # Log error to telemetry
        telemetry.log_error(
            component="workflow",
            error_type=type(e).__name__,
            message=str(e)
        )
        raise

    finally:
        # Always save telemetry metrics
        telemetry.save_session_metrics()
        logger.info("Telemetry metrics saved")

