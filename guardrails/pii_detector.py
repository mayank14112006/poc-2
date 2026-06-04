import re
import json
import anthropic
from config.settings import ANTHROPIC_API_KEY

def redact_pii(text: str) -> str:
    """
    Redacts obvious PII with placeholders.
    """
    # 1. Credit Card (16 digits, check first to avoid overlap with 12-digit Aadhaar)
    text = re.sub(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b", "[REDACTED_CARD]", text)
    
    # 2. Aadhaar (12 digits)
    text = re.sub(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b", "[REDACTED_AADHAAR]", text)
    
    # 3. PAN
    text = re.sub(r"\b[a-zA-Z]{5}\d{4}[a-zA-Z]\b", "[REDACTED_PAN]", text)
    
    # 4. Indian Mobile Numbers
    text = re.sub(r"(?:\+91[ -]?)?[6-9](?:\d[ -]?){9}\b", "[REDACTED_MOBILE]", text)
    
    # 5. Password formats
    def pwd_replacer(match):
        prefix = match.group(1)
        return f"{prefix} [REDACTED_PASSWORD]"
        
    text = re.sub(r"(?i)\b((?:my\s+)?(?:password|passwd|pwd)\s*(?:is|[:=]))\s*(\S+)", pwd_replacer, text)
    
    return text

def check_pii(text: str) -> dict:
    """
    Checks if the user's message contains personal sensitive information.
    Fail closed: blocks if anything goes wrong.
    """
    # Stage 1: Fast Regex check
    # Check Credit Card first to avoid 12-digit substring matching in 16-digit cards
    if re.search(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b", text):
        return {"safe": False, "reason": "Contains credit card"}
        
    # Check Aadhaar
    if re.search(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b", text):
        return {"safe": False, "reason": "Contains aadhaar number"}
        
    # Check PAN
    if re.search(r"\b[a-zA-Z]{5}\d{4}[a-zA-Z]\b", text):
        return {"safe": False, "reason": "Contains pan"}
        
    # Check Mobile
    if re.search(r"(?:\+91[ -]?)?[6-9](?:\d[ -]?){9}\b", text):
        return {"safe": False, "reason": "Contains mobile"}
        
    # Check Password
    if re.search(r"(?i)\b(?:my\s+)?(?:password|passwd|pwd)\s*(?:is|[:=])\s*\S+", text):
        return {"safe": False, "reason": "Contains password"}

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
        print(f"PII Haiku classifier error: {e}")
        # FAIL CLOSED
        return {
            "safe": False,
            "reason": "Safety check unavailable. Please try again later."
        }
        
    return {"safe": True}

