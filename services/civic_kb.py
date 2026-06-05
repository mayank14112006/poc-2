from pathlib import Path

_kb_content = None

def load_kb() -> str:
    global _kb_content
    if _kb_content is None:
        kb_path = Path(__file__).parent.parent / "data" / "civic_kb.md"
        _kb_content = kb_path.read_text(encoding="utf-8")
    return _kb_content

def build_system_prompt() -> str:
    kb = load_kb()
    return f"""You are a helpful citizen services assistant for Pragati Nagar Nigam, 
a municipal corporation in India. You help citizens with questions about civic services.

Only answer questions related to the following civic services. If asked anything else, 
politely say you can only help with municipal services.

KNOWLEDGE BASE:
{kb}

Always be polite, clear, and concise. If you don't know something, say so honestly.
Do not make up fees, dates, or procedures not listed above."""
