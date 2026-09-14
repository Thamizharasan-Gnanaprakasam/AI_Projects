"""
Language definitions and mapping for Wispr Flow Alt.
Supports Auto-detect and 99+ Whisper-supported languages.
"""

from typing import Dict, List, Optional

# Prominently featured languages + Auto-detect
POPULAR_LANGUAGES: Dict[str, str] = {
    "auto": "Auto Detect (Automatic)",
    "en": "English",
    "ta": "Tamil (தமிழ்)",
    "hi": "Hindi (हिन्दी)",
    "es": "Spanish (Español)",
    "fr": "French (Français)",
    "de": "German (Deutsch)",
    "zh": "Chinese (中文)",
    "ja": "Japanese (日本語)",
    "ko": "Korean (한국어)",
    "ar": "Arabic (العربية)",
    "pt": "Portuguese (Português)",
    "it": "Italian (Italiano)",
    "ru": "Russian (Русский)",
    "te": "Telugu (తెలుగు)",
    "ml": "Malayalam (മലയാളം)",
    "kn": "Kannada (ಕನ್ನಡ)",
    "mr": "Marathi (मराठी)",
    "bn": "Bengali (বাংলা)",
    "gu": "Gujarati (ગુજરાતી)",
    "pa": "Punjabi (ਪੰਜਾਬੀ)",
    "ur": "Urdu (اردو)",
}

# Conversational prompts to anchor language script and enable natural code-mixing
LANGUAGE_PROMPTS: Dict[str, str] = {
    "ta": "வணக்கம், எப்படி இருக்கீங்க? நல்லா இருக்கீங்களா. Hello, how are you.",
    "hi": "नमस्ते, आप कैसे हैं? सब ठीक है. Hello, how are you.",
    "te": "నమస్కారం, మీరు ఎలా ఉన్నారు? Hello, how are you.",
    "ml": "നമസ്കാരം, സുഖമാണോ? Hello, how are you.",
    "kn": "ನಮಸ್ಕಾರ, ಹೇಗಿದ್ದೀರಾ? Hello, how are you.",
    "mr": "नमस्कार, तुम्ही कसे आहात? Hello, how are you.",
    "bn": "নমস্কার, কেমন আছেন? Hello, how are you.",
    "gu": "નમસ્તે, તમે કેમ છો? Hello, how are you.",
    "pa": "ਸਤਿ ਸ਼੍ਰੀ ਅਕਾਲ, ਤੁਸੀਂ ਕਿਵੇਂ ਹੋ? Hello, how are you.",
    "ur": "السلام علیکم، آپ کیسے ہیں؟ Hello, how are you.",
    "es": "Hola, ¿cómo estás? Buenos días. Hello.",
    "fr": "Bonjour, comment allez-vous ? Bonne journée. Hello.",
    "de": "Guten Tag, wie geht es Ihnen? Hello.",
    "zh": "你好，最近怎么样？ Hello.",
    "ja": "こんにちは、お元気ですか？ Hello.",
    "ko": "안녕하세요, 잘 지내시나요? Hello.",
    "ar": "مرحبا، كيف حالك؟ Hello.",
    "ru": "Здравствуйте, как ваши дела? Hello.",
    "en": "Hello, how are you doing today? Yeah, okay."
}



# Auto mode prompt: neutral style
AUTO_LANGUAGE_PROMPT = None

def get_language_prompt(code: str) -> Optional[str]:
    """
    Returns None to avoid prompt contamination.
    Feeding conversational sentences as initial_prompt causes Whisper decoders
    to loop on suffix tokens and hallucinate prompt words.
    """
    return None

def get_language_code(input_str: str) -> str:
    """
    Normalizes any user-provided string (e.g. 'Tamil', 'ta', 'Auto', 'auto', 'English')
    into a valid Whisper language code or 'auto'.
    """
    cleaned = (input_str or "auto").strip().lower()
    
    if cleaned in ("auto", "automatic", "detect", "auto-detect", "none"):
        return "auto"

    # Direct match on code
    if cleaned in POPULAR_LANGUAGES:
        return cleaned

    # Match on language name or substring
    for code, name in POPULAR_LANGUAGES.items():
        if cleaned in name.lower():
            return code

    # Fallback to the code as entered
    return cleaned

def get_language_display_name(code: str) -> str:
    """Returns human-readable name for a language code."""
    normalized = get_language_code(code)
    return POPULAR_LANGUAGES.get(normalized, f"Language ({code})")

def list_supported_languages() -> List[Dict[str, str]]:
    """Returns list of language options for UI/CLI selectors."""
    return [{"code": code, "name": name} for code, name in POPULAR_LANGUAGES.items()]
