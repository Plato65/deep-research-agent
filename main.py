"""Main entry point for the Deep Research Agent."""

import asyncio
import sys
from pathlib import Path
import logging
import requests
from typing import Dict, Any, Tuple

from src.config import config
from src.graph import run_research

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def validate_environment() -> Tuple[bool, Dict[str, Any]]:
    """Pre-flight checks before research run.

    Validates API keys, connectivity, cache directories, and estimates cost.

    Returns:
        Tuple of (passed: bool, results: dict)
    """
    logger.info("Running pre-flight environment validation")

    results = {
        "checks": [],
        "warnings": [],
        "errors": [],
        "passed": True
    }

    # 1. Validate basic config
    try:
        config.validate_config()
        results["checks"].append({
            "name": "Basic Configuration",
            "status": "✓ PASS",
            "details": f"Provider: {config.model_provider}, Mode: {config.research_mode}"
        })
    except ValueError as e:
        results["errors"].append(f"Configuration error: {e}")
        results["passed"] = False
        results["checks"].append({
            "name": "Basic Configuration",
            "status": "✗ FAIL",
            "details": str(e)
        })

    # 2. Test search API connectivity (if enabled)
    if config.enable_cloud_apis:
        api_tests = []

        # Test Serper API
        if config.serper_api_key:
            try:
                response = requests.post(
                    "https://google.serper.dev/search",
                    json={"q": "test"},
                    headers={"X-API-KEY": config.serper_api_key},
                    timeout=5
                )
                if response.status_code in [200, 429]:  # 429 = rate limit, but key is valid
                    api_tests.append("Serper: ✓")
                else:
                    api_tests.append(f"Serper: ✗ (HTTP {response.status_code})")
                    results["warnings"].append(f"Serper API returned status {response.status_code}")
            except Exception as e:
                api_tests.append(f"Serper: ✗ ({str(e)[:30]})")
                results["warnings"].append(f"Serper API test failed: {e}")

        # Test Tavily API
        if config.tavily_api_key:
            try:
                response = requests.post(
                    "https://api.tavily.com/search",
                    json={"query": "test", "max_results": 1},
                    headers={"Authorization": f"Bearer {config.tavily_api_key}"},
                    timeout=5
                )
                if response.status_code in [200, 429]:
                    api_tests.append("Tavily: ✓")
                else:
                    api_tests.append(f"Tavily: ✗ (HTTP {response.status_code})")
                    results["warnings"].append(f"Tavily API returned status {response.status_code}")
            except Exception as e:
                api_tests.append(f"Tavily: ✗ ({str(e)[:30]})")
                results["warnings"].append(f"Tavily API test failed: {e}")

        # Test Brave API
        if config.brave_api_key:
            try:
                response = requests.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    params={"q": "test", "count": 1},
                    headers={"X-Subscription-Token": config.brave_api_key},
                    timeout=5
                )
                if response.status_code in [200, 429]:
                    api_tests.append("Brave: ✓")
                else:
                    api_tests.append(f"Brave: ✗ (HTTP {response.status_code})")
                    results["warnings"].append(f"Brave API returned status {response.status_code}")
            except Exception as e:
                api_tests.append(f"Brave: ✗ ({str(e)[:30]})")
                results["warnings"].append(f"Brave API test failed: {e}")

        if api_tests:
            results["checks"].append({
                "name": "Search APIs",
                "status": "TESTED",
                "details": ", ".join(api_tests)
            })
        else:
            results["warnings"].append("No premium search APIs configured (will use DuckDuckGo)")
            results["checks"].append({
                "name": "Search APIs",
                "status": "⚠ NONE",
                "details": "No premium APIs - using DuckDuckGo fallback"
            })
    else:
        results["checks"].append({
            "name": "Search APIs",
            "status": "DISABLED",
            "details": "Cloud APIs disabled (privacy mode)"
        })

    # 3. Verify cache directories
    cache_dirs = [
        Path(config.cache_dir),
        Path("./.cache/deduplication"),
        Path("./outputs"),
        Path("./outputs/telemetry")
    ]

    cache_issues = []
    for cache_dir in cache_dirs:
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            if not cache_dir.exists() or not cache_dir.is_dir():
                cache_issues.append(str(cache_dir))
        except Exception as e:
            cache_issues.append(f"{cache_dir} ({e})")

    if cache_issues:
        results["errors"].append(f"Cache directory issues: {', '.join(cache_issues)}")
        results["passed"] = False
        results["checks"].append({
            "name": "Cache Directories",
            "status": "✗ FAIL",
            "details": f"Issues: {', '.join(cache_issues)}"
        })
    else:
        results["checks"].append({
            "name": "Cache Directories",
            "status": "✓ PASS",
            "details": f"All {len(cache_dirs)} directories accessible"
        })

    # 4. Estimate cost (if using paid APIs)
    cost_estimate = estimate_research_cost(config)
    results["checks"].append({
        "name": "Cost Estimate",
        "status": "INFO",
        "details": cost_estimate
    })

    # 5. Model configuration summary
    models_info = []
    if config.planner_model:
        models_info.append(f"Planner: {config.planner_model}")
    if config.search_model:
        models_info.append(f"Search: {config.search_model}")
    if config.synthesis_model:
        models_info.append(f"Synthesis: {config.synthesis_model}")
    if config.writing_model:
        models_info.append(f"Writing: {config.writing_model}")

    if models_info:
        results["checks"].append({
            "name": "Multi-Model Setup",
            "status": "ENABLED",
            "details": ", ".join(models_info)
        })
    else:
        results["checks"].append({
            "name": "Multi-Model Setup",
            "status": "DEFAULT",
            "details": f"All agents using: {config.model_name}"
        })

    logger.info(f"Pre-flight validation: {'PASSED' if results['passed'] else 'FAILED'}")

    return results["passed"], results


def estimate_research_cost(cfg) -> str:
    """Estimate cost for current research configuration.

    Args:
        cfg: ResearchConfig instance

    Returns:
        Cost estimate string
    """
    if cfg.model_provider == "gemini":
        # Gemini 2.5 Flash pricing (approximate)
        # Input: $0.075 per 1M tokens, Output: $0.30 per 1M tokens
        # Estimate: 5 queries × 5 results × 1000 tokens each = ~25k input tokens
        #           8 sections × 500 tokens each = ~4k output tokens
        estimated_input = 25000
        estimated_output = 4000
        cost = (estimated_input / 1_000_000 * 0.075) + (estimated_output / 1_000_000 * 0.30)
        return f"~${cost:.4f} per report (Gemini)"

    elif cfg.model_provider == "openai":
        # GPT-4o-mini pricing (approximate)
        # Input: $0.15 per 1M tokens, Output: $0.60 per 1M tokens
        estimated_input = 25000
        estimated_output = 4000
        cost = (estimated_input / 1_000_000 * 0.15) + (estimated_output / 1_000_000 * 0.60)
        return f"~${cost:.4f} per report (OpenAI)"

    elif cfg.model_provider in ["ollama", "lmstudio"]:
        return "Free (local models)"

    else:
        return "Unknown"


def display_validation_results(results: Dict[str, Any]):
    """Display validation results in a user-friendly format.

    Args:
        results: Validation results dictionary
    """
    print("\n" + "=" * 80)
    print("PRE-FLIGHT ENVIRONMENT VALIDATION")
    print("=" * 80 + "\n")

    for check in results["checks"]:
        print(f"{check['status']:12} | {check['name']:25} | {check['details']}")

    if results["warnings"]:
        print("\n" + "⚠" * 40)
        print("WARNINGS:")
        for warning in results["warnings"]:
            print(f"  ⚠ {warning}")
        print("⚠" * 40)

    if results["errors"]:
        print("\n" + "✗" * 40)
        print("ERRORS:")
        for error in results["errors"]:
            print(f"  ✗ {error}")
        print("✗" * 40)

    print("\n" + "=" * 80)
    if results["passed"]:
        print("✓ VALIDATION PASSED - Ready to start research")
    else:
        print("✗ VALIDATION FAILED - Fix errors before proceeding")
    print("=" * 80 + "\n")


async def main():
    """Main function to run the research agent."""

    # Run pre-flight validation
    passed, validation_results = await validate_environment()
    display_validation_results(validation_results)

    if not passed:
        logger.error("Environment validation failed - cannot proceed")
        sys.exit(1)
    
    # Get research topic
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        print("\nDeep Research Agent")
        print("=" * 50)
        topic = input("\nEnter your research topic: ").strip()

    if not topic:
        logger.error("No research topic provided")
        sys.exit(1)

    # Validate and sanitize topic
    from src.utils.validation import validate_topic
    is_valid, sanitized_topic, error_msg = validate_topic(topic)

    if not is_valid:
        logger.error(f"Invalid research topic: {error_msg}")
        print(f"\n[ERROR] {error_msg}")
        sys.exit(1)

    if sanitized_topic != topic:
        logger.info(f"Topic sanitized: '{topic}' -> '{sanitized_topic}'")
        topic = sanitized_topic
    
    print(f"\n[INFO] Starting deep research on: {topic}\n")
    print("This may take several minutes. Please wait...\n")
    
    try:
        # Run the research workflow
        final_state = await run_research(topic, verbose=True)
        
        # LangGraph returns dict with state - access fields directly
        # Check for errors
        if final_state.get("error"):
            logger.error(f"Research failed: {final_state.get('error')}")
            sys.exit(1)
        
        # Display results
        print("\n" + "=" * 80)
        print("RESEARCH COMPLETE")
        print("=" * 80)
        
        if final_state.get("plan"):
            plan = final_state["plan"]
            print(f"\nResearch Plan Summary:")
            print(f"  - Objectives: {len(plan.objectives)}")
            print(f"  - Search Queries: {len(plan.search_queries)}")
            print(f"  - Report Sections: {len(plan.report_outline)}")
        
        print(f"\nResearch Data Summary:")
        print(f"  - Search Results: {len(final_state.get('search_results', []))}")
        print(f"  - Key Findings: {len(final_state.get('key_findings', []))}")
        print(f"  - Report Sections: {len(final_state.get('report_sections', []))}")
        print(f"  - Iterations: {final_state.get('iterations', 0)}")
        
        # Save the report
        if final_state.get("final_report"):
            output_dir = Path("outputs")
            output_dir.mkdir(exist_ok=True)

            # Create safe filename
            safe_topic = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in topic)
            safe_topic = safe_topic[:50].strip()

            output_file = output_dir / f"{safe_topic}.md"
            final_report = final_state["final_report"]
            output_file.write_text(final_report, encoding='utf-8')

            # Make output location VERY obvious
            print("\n" + "=" * 80)
            print("📄 REPORT SAVED SUCCESSFULLY")
            print("=" * 80)
            print(f"\n✓ Location: {output_file.absolute()}")
            print(f"✓ Filename: {output_file.name}")
            print(f"✓ Size: {len(final_report):,} characters")
            print("\n" + "=" * 80)
            
            # Display a preview
            print("\n" + "=" * 80)
            print("REPORT PREVIEW")
            print("=" * 80)
            print(final_report[:1500])
            if len(final_report) > 1500:
                print(f"\n... (showing first 1500 of {len(final_report)} characters)")
            print("\n" + "=" * 80)
            
        else:
            logger.warning("No report was generated")
        
    except KeyboardInterrupt:
        print("\n\n[WARNING] Research interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"[ERROR] Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

