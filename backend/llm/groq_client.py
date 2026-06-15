import os
import json
import logging

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class GroqLLM:

    def __init__(self):
        logger.info("[LLM] Initializing GroqLLM client")

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            logger.error("[LLM] GROQ_API_KEY not found in environment variables")
            raise ValueError("GROQ_API_KEY environment variable is not set")

        try:
            self.client = Groq(api_key=api_key)
            logger.info("[LLM] Groq client initialized successfully")

        except Exception as e:
            logger.error(f"[LLM] Failed to initialize Groq client: {e}")
            raise

    def analyze_log(self, log_text: str) -> dict:
        logger.info(f"[LLM] Analyzing log: {log_text[:80]}...")

        system_prompt = """You are an expert DevOps log classification engine.
You MUST classify every log into one of these categories:

ERROR CATEGORIES:
- Authentication Failure, Database Error, API Timeout, Disk Full,
- HTTP 500, HTTP 403, HTTP 404, Memory Leak, CPU Spike,
- Kubernetes CrashLoop, SSL Error, DNS Failure, Redis Failure,
- Kafka Failure, Payment Failure, React Component Error

OPERATIONAL CATEGORIES:
- Successful Login, Payment Success, Data Sync Complete,
- Search Index Updated, Component Rendered, Slow Query,
- Rate Limit Warning, Memory Warning

SEVERITY VALUES: Critical, High, Medium, Low

You MUST respond with ONLY valid JSON, no markdown, no explanation.
Format:
{"classification": "...", "severity": "...", "root_cause": "...", "solution": "..."}"""

        user_prompt = f"Classify this log:\n\n{log_text}"

        try:
            logger.debug("[LLM] Sending request to Groq API (llama-3.1-8b-instant)")

            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )

            content = response.choices[0].message.content
            logger.debug(f"[LLM] Raw response received: {content[:100]}...")

        except Exception as e:
            logger.error(f"[LLM] Groq API call failed: {e}")
            return {
                "classification": "Unknown",
                "severity": "Unknown",
                "root_cause": f"LLM API error: {str(e)}",
                "solution": "Manual review required"
            }

        # Try to extract JSON — handle markdown code fences
        try:
            parsed_json = json.loads(content)
        except json.JSONDecodeError:
            # Strip markdown fences like ```json ... ```
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                try:
                    parsed_json = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    parsed_json = None
            else:
                # Try finding raw JSON object in the response
                brace_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                if brace_match:
                    try:
                        parsed_json = json.loads(brace_match.group(0))
                    except json.JSONDecodeError:
                        parsed_json = None
                else:
                    parsed_json = None

        if parsed_json and parsed_json.get("classification") and parsed_json.get("classification") != "Unknown":
            logger.info(
                f"[LLM] Successfully parsed response — "
                f"classification: {parsed_json.get('classification')}, "
                f"severity: {parsed_json.get('severity')}"
            )
            return parsed_json

        logger.warning(f"[LLM] Failed to extract valid classification from response")
        logger.debug(f"[LLM] Raw content was: {content}")
        return {
            "classification": "Unknown",
            "severity": "Unknown",
            "root_cause": content,
            "solution": "Manual review required"
        }
