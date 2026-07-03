# prompts.py
# Unified translation prompts for literary translation style

LITERARY_SYSTEM_PROMPT = (
    "Translate the following book chapter text into smooth, natural, literary, and high-quality Arabic (Fusha). "
    "Keep the paragraph and line structure intact. The translation should feel like it is narrated by a professional Arabic audiobook speaker. "
    "Do not write any introductory notes, explanations, or concluding remarks. Only return the Arabic translation text itself."
)

def get_gemini_prompt(text: str) -> str:
    """
    Returns prompt string for Gemini API.
    """
    return f"{LITERARY_SYSTEM_PROMPT}\n\nText to translate:\n{text}"

def get_system_prompt() -> str:
    """
    Returns system prompt string for OpenAI and Claude APIs.
    """
    return LITERARY_SYSTEM_PROMPT
