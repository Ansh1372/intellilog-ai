import json
import re
import logging

logger = logging.getLogger(__name__)


class RegexEngine:

    def __init__(self, rules_path="data/regex_rules.json"):
        logger.info(f"[REGEX] Initializing RegexEngine with rules: {rules_path}")

        try:
            with open(rules_path, "r") as file:
                self.rules = json.load(file)
            logger.info(f"[REGEX] Loaded {len(self.rules)} regex rules successfully")

        except FileNotFoundError:
            logger.error(f"[REGEX] Rules file not found: {rules_path}")
            self.rules = []

        except json.JSONDecodeError as e:
            logger.error(f"[REGEX] Invalid JSON in rules file: {e}")
            self.rules = []

        except Exception as e:
            logger.error(f"[REGEX] Unexpected error loading rules: {e}")
            self.rules = []

    def classify(self, log_text: str) -> dict:
        logger.debug(f"[REGEX] Classifying log: {log_text[:80]}...")

        if not self.rules:
            logger.warning("[REGEX] No rules loaded — skipping regex stage")
            return {"matched": False}

        for rule in self.rules:
            try:
                pattern = rule["pattern"]

                if re.search(pattern, log_text):
                    logger.info(
                        f"[REGEX] Match found — classification: {rule['classification']}, "
                        f"severity: {rule['severity']}"
                    )
                    return {
                        "matched": True,
                        "classification": rule["classification"],
                        "severity": rule["severity"],
                        "solution": rule["solution"],
                        "source": "regex"
                    }

            except re.error as e:
                logger.error(f"[REGEX] Invalid regex pattern '{rule.get('pattern')}': {e}")
                continue

            except KeyError as e:
                logger.error(f"[REGEX] Rule missing required field: {e}")
                continue

        logger.debug("[REGEX] No regex match found")
        return {"matched": False}
