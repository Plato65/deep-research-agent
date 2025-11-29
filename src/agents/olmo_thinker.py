"""
OLMo 3 32B Think Critic

Uses OLMo 3 32B Think for enhanced research quality evaluation with explicit reasoning.
Leverages OLMo's <think> tags for transparent evaluation process.
"""

import json
import re
import logging
import asyncio
import time
from typing import Dict
from openai import AsyncOpenAI

from src.state import ResearchState
from src.config import config
from src.utils.tokens import estimate_tokens

logger = logging.getLogger(__name__)


class OLMoThinker:
    """Research critic using OLMo 3 32B Think for enhanced reasoning."""

    def __init__(self, endpoint: str = "http://localhost:30002/v1", model_name: str = None):
        """Initialize OLMo thinker.

        Args:
            endpoint: VLLM/LM Studio server endpoint (default: http://localhost:30002/v1)
            model_name: Model identifier (default: auto-detect or use config)
        """
        self.endpoint = endpoint
        self.max_retries = config.max_retries

        # Model name: Allow override, fall back to config, or use default
        self.model_name = model_name or getattr(config, 'olmo_model_name', None) or "allenai/Olmo-3-32B-Think"

        # Use async OpenAI client for VLLM/LM Studio
        self.client = AsyncOpenAI(
            base_url=endpoint,
            api_key="dummy"  # VLLM/LM Studio don't require real API key
        )

        logger.info(f"OLMoThinker initialized (endpoint: {endpoint}, model: {self.model_name})")

    def _create_critique_prompt(self, state: ResearchState) -> str:
        """Create critique prompt for OLMo Think.

        OLMo uses:
        - <|im_start|> chat format
        - <think> tags for reasoning
        - Returns structured JSON evaluation

        Args:
            state: Research state

        Returns:
            Formatted prompt
        """
        objectives = state.plan.objectives if state.plan else []
        findings = state.key_findings if state.key_findings else []
        sources_count = len(state.search_results) if state.search_results else 0

        objectives_text = "\n".join([f"{i+1}. {obj}" for i, obj in enumerate(objectives)]) if objectives else "No objectives specified"
        findings_text = "\n".join([f"- {finding}" for finding in findings[:20]]) if findings else "No findings extracted"

        prompt = f"""Research Topic: {state.research_topic}

Research Objectives:
{objectives_text}

Key Findings ({len(findings)} findings from {sources_count} sources):
{findings_text}

Evaluate this research on 5 dimensions:

1. **Coverage (0-100)**: Do findings address ALL objectives?
2. **Evidence (0-100)**: Are claims well-supported by sources?
3. **Depth (0-100)**: Is analysis substantive or superficial?
4. **Specificity (0-100)**: Are findings concrete or vague?
5. **Recency (0-100)**: Is information current and relevant?

Think carefully about each dimension, then provide your evaluation as JSON:

{{
    "coverage_score": <0-100>,
    "evidence_score": <0-100>,
    "depth_score": <0-100>,
    "specificity_score": <0-100>,
    "recency_score": <0-100>,
    "overall_score": <average of all scores>,
    "strengths": ["strength 1", "strength 2", ...],
    "weaknesses": ["weakness 1", "weakness 2", ...],
    "missing_topics": ["topic 1", "topic 2", ...],
    "recommended_queries": ["query 1", "query 2", ...],
    "should_refine": <true if overall_score < 70, false otherwise>,
    "feedback": "Detailed explanation of evaluation"
}}

If overall_score < 70, you MUST provide specific recommended_queries to address the gaps."""

        return prompt

    def _extract_json_from_response(self, text: str) -> Dict:
        """Extract JSON from OLMo response, handling <think> tags.

        Args:
            text: Response text from OLMo

        Returns:
            Parsed JSON dict
        """
        # Remove <think> tags if present
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

        # Try to extract JSON object
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned, re.DOTALL)

        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error: {e}")

        # Fallback: try to find JSON anywhere in text
        try:
            # Find outermost braces
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                json_str = text[start:end+1]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # If all parsing fails, return default structure
        logger.error("Failed to extract JSON from OLMo response")
        raise ValueError("Could not parse JSON from OLMo response")

    async def critique(self, state: ResearchState) -> dict:
        """Evaluate research quality using OLMo Think.

        Compatible with existing ResearchCritic interface.

        Args:
            state: Research state

        Returns:
            Dict with quality_score and critique_feedback
        """
        logger.info("Evaluating research quality with OLMo Think")

        prompt = self._create_critique_prompt(state)

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()

                # OLMo 3 32B Think parameters (from model card)
                response = await self.client.chat.completions.create(
                    model=self.model_name,  # Use configured model name (supports LM Studio)
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert research quality evaluator. Analyze research findings and provide detailed critique. Use <think> tags to show your reasoning process."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=4096,
                    temperature=0.6,  # Recommended for OLMo Think
                    top_p=0.95,        # Recommended for OLMo Think
                )

                duration = time.time() - start_time

                # Extract response text
                response_text = response.choices[0].message.content

                # Parse JSON from response
                result = self._extract_json_from_response(response_text)

                # Token usage
                input_tokens = response.usage.prompt_tokens if response.usage else estimate_tokens(prompt)
                output_tokens = response.usage.completion_tokens if response.usage else estimate_tokens(response_text)

                call_detail = {
                    'agent': 'OLMoThinker',
                    'operation': 'critique',
                    'model': 'allenai/Olmo-3-32B-Think',
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'duration': round(duration, 2),
                    'attempt': attempt + 1
                }

                # Validate result structure
                required_keys = ["coverage_score", "evidence_score", "depth_score",
                               "specificity_score", "recency_score", "overall_score",
                               "should_refine", "feedback"]

                if not all(key in result for key in required_keys):
                    missing = set(required_keys) - set(result.keys())
                    logger.warning(f"Missing keys in critique: {missing}")

                    # Add missing keys with default values
                    for key in missing:
                        if key.endswith('_score'):
                            result[key] = 50
                        elif key == 'should_refine':
                            result[key] = False
                        elif key == 'feedback':
                            result[key] = "Evaluation incomplete"
                        else:
                            result[key] = []

                # Ensure scores are in valid range
                for score_key in ["coverage_score", "evidence_score", "depth_score",
                                "specificity_score", "recency_score", "overall_score"]:
                    if score_key in result:
                        result[score_key] = max(0, min(100, result[score_key]))

                logger.info(f"OLMo critique complete - Overall score: {result['overall_score']}/100")
                logger.info(f"  Coverage: {result.get('coverage_score', 'N/A')}, "
                          f"Evidence: {result.get('evidence_score', 'N/A')}, "
                          f"Depth: {result.get('depth_score', 'N/A')}, "
                          f"Specificity: {result.get('specificity_score', 'N/A')}, "
                          f"Recency: {result.get('recency_score', 'N/A')}")

                if result.get('should_refine'):
                    logger.warning(f"Research quality insufficient ({result['overall_score']}/100) - refinement recommended")
                    if result.get('missing_topics'):
                        logger.warning(f"  Missing topics: {', '.join(result['missing_topics'][:3])}")
                    if result.get('recommended_queries'):
                        logger.info(f"  Recommended queries: {len(result['recommended_queries'])}")

                # Return updates to merge into state
                return {
                    "quality_score": result,
                    "critique_feedback": result.get("feedback", ""),
                    "llm_calls": state.llm_calls + 1,
                    "total_input_tokens": state.total_input_tokens + input_tokens,
                    "total_output_tokens": state.total_output_tokens + output_tokens,
                    "llm_call_details": state.llm_call_details + [call_detail]
                }

            except Exception as e:
                logger.warning(f"OLMo critique attempt {attempt + 1}/{self.max_retries} failed: {e}")
                if attempt == self.max_retries - 1:
                    logger.error(f"All OLMo critique attempts failed: {e}")
                    # Return neutral scores if critique fails
                    return {
                        "quality_score": {
                            "coverage_score": 50,
                            "evidence_score": 50,
                            "depth_score": 50,
                            "specificity_score": 50,
                            "recency_score": 50,
                            "overall_score": 50,
                            "should_refine": False,
                            "feedback": f"Critique failed: {str(e)}",
                            "strengths": [],
                            "weaknesses": ["Critique process failed"],
                            "missing_topics": [],
                            "recommended_queries": []
                        },
                        "critique_feedback": f"Critique failed: {str(e)}",
                        "llm_calls": state.llm_calls + 1,
                        "total_input_tokens": state.total_input_tokens,
                        "total_output_tokens": state.total_output_tokens,
                        "llm_call_details": state.llm_call_details
                    }
                else:
                    await asyncio.sleep(2 ** attempt)

        # Should never reach here, but fallback
        return {
            "quality_score": {
                "coverage_score": 50,
                "evidence_score": 50,
                "depth_score": 50,
                "specificity_score": 50,
                "recency_score": 50,
                "overall_score": 50,
                "should_refine": False,
                "feedback": "Maximum retries exceeded",
                "strengths": [],
                "weaknesses": ["Critique process failed"],
                "missing_topics": [],
                "recommended_queries": []
            },
            "critique_feedback": "Maximum retries exceeded",
            "llm_calls": state.llm_calls + 1,
            "total_input_tokens": state.total_input_tokens,
            "total_output_tokens": state.total_output_tokens,
            "llm_call_details": state.llm_call_details
        }
