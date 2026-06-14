from backend.llm.groq_client import GroqLLM


llm = GroqLLM()

log = """
distributed transaction failure after retry exhaustion
database node unreachable during payment processing
"""

result = llm.analyze_log(log)

print("\nLLM RESPONSE:\n")

print(result)
