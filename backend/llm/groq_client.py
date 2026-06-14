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

        prompt = f"""
You are an expert AI log analysis assistant.

Analyze the following log:

{log_text}

IMPORTANT:
Return ONLY valid JSON.

Format:

{{
    "classification": "...",
    "severity": "...",
    "root_cause": "...",
    "solution": "..."
}}
"""

        try:
            logger.debug("[LLM] Sending request to Groq API (llama-3.1-8b-instant)")

            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "user", "content": prompt}
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

        try:
            parsed_json = json.loads(content)
            logger.info(
                f"[LLM] Successfully parsed response — "
                f"classification: {parsed_json.get('classification')}, "
                f"severity: {parsed_json.get('severity')}"
            )
            return parsed_json

        except json.JSONDecodeError as e:
            logger.warning(f"[LLM] Failed to parse JSON response: {e}")
            logger.debug(f"[LLM] Raw content was: {content}")
            return {
                "classification": "Unknown",
                "severity": "Unknown",
                "root_cause": content,
                "solution": "Manual review required"
            }
