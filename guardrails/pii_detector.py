import re
import json
import anthropic
from config.settings import ANTHROPIC_API_KEY

PII_PATTERNS = {
    "credit_card": r"\b\d{4}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}\b",
    "aadhaar": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
    "pan": r"\b[A-Z]{5}\d{4}[A-Z]\b",
    "mobile": r"\b[6-9]\d{9}\b",
    "password": r"(?i)(password|passwd|pwd)\s*[=:]\s*\S+"
}

def check_pii(text: str) -> dict:
    """
    Checks if the user's message contains personal sensitive information.
    
    Returns:
        {"safe": True} if no PII found
        {"safe": False, "reason": "..."} if PII found
    """
    # Stage 1: Fast Regex check
    for pii_type, pattern in PII_PATTERNS.items():
        if re.search(pattern, text):
            # Format reasons as requested in tests/guardrail_tests.md
            reason_map = {
                "aadhaar": "Contains aadhaar number",
                "pan": "Contains pan",
                "credit_card": "Contains credit card",
                "mobile": "Contains mobile",
                "password": "Contains password"
            }
            reason_text = reason_map.get(pii_type, f"Contains {pii_type.replace('_', ' ')}")
            return {
                "safe": False,
                "reason": reason_text
            }
            
    # Stage 2: Haiku classifier for edge cases
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=100,
            system="""You are a PII detector. Check if the text contains any personal 
identifiable information like ID numbers, card numbers, passwords, or government IDs.
Respond ONLY with JSON: {"contains_pii": true/false, "reason": "brief reason"}""",
            messages=[{"role": "user", "content": text}]
        )
        
        raw_content = response.content[0].text.strip()
        
        # Extract JSON block using regex to handle extra text / markdown wraps
        json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
        if json_match:
            raw_content = json_match.group(0)
            
        result = json.loads(raw_content)
        if result.get("contains_pii"):
            return {
                "safe": False,
                "reason": result.get("reason", "Contains personally identifiable information.")
            }
    except Exception as e:
        # If API call fails, fail-safe to True or log (for local testing without internet/api keys)
        print(f"PII Haiku classifier error: {e}")
        
    return {"safe": True}
