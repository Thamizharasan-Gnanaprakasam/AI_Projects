"""
Configuration settings for Wispr Flow Alternative.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

IS_WINDOWS = sys.platform == "win32"

# Path resolution for standalone app bundle vs development
if getattr(sys, 'frozen', False):
    # Running inside packaged app bundle (PyInstaller)
    BASE_DIR = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    if IS_WINDOWS:
        APP_DATA_DIR = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming")) / "VoiceInk"
    else:
        APP_DATA_DIR = Path.home() / "Library" / "Application Support" / "VoiceInk"
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR = APP_DATA_DIR / "data"
    DATA_DIR.mkdir(exist_ok=True)
    ENV_PATH = APP_DATA_DIR / ".env"
    if not ENV_PATH.exists():
        bundle_env = BASE_DIR / ".env"
        if bundle_env.exists():
            import shutil
            shutil.copy(bundle_env, ENV_PATH)
        else:
            ENV_PATH.touch()
    load_dotenv(ENV_PATH)
else:
    BASE_DIR = Path(__file__).resolve().parent
    DATA_DIR = BASE_DIR / "data"
    DATA_DIR.mkdir(exist_ok=True)
    ENV_PATH = BASE_DIR / ".env"
    load_dotenv(ENV_PATH)

# ----------------- Audio Configuration -----------------
SAMPLE_RATE = int(os.getenv("WISPR_SAMPLE_RATE", "16000"))
CHANNELS = 1
SILENCE_THRESHOLD = float(os.getenv("WISPR_SILENCE_THRESHOLD", "0.015"))
SILENCE_DURATION = float(os.getenv("WISPR_SILENCE_DURATION", "4.0"))
MAX_RECORDING_SECONDS = int(os.getenv("WISPR_MAX_RECORDING_SECONDS", "300"))
NOISE_CANCELLATION_ENABLED = os.getenv("WISPR_NOISE_CANCELLATION", "true").lower() in ("1", "true", "yes")
NOISE_HIGHPASS_CUTOFF = 80.0   # Cutoff in Hz (eliminates 50/60Hz hum, HVAC, desk rumble)
NOISE_REDUCTION_PROP = 0.35    # Gentle spectral reduction (preserves speech formants)

# ----------------- Hotkey Configuration -----------------
RECORDING_MODE = os.getenv("WISPR_RECORDING_MODE", "toggle")  # "toggle" or "push_to_talk"

if IS_WINDOWS:
    DEFAULT_HOTKEY_CHOICE = os.getenv("WISPR_HOTKEY_CHOICE", "ctrl_space")
    HOTKEY = os.getenv("WISPR_HOTKEY", "ctrl_space")
    HOTKEY_OPTIONS = {
        "ctrl_space": "Control + Space (Ctrl + Space) [Recommended]",
        "alt_space": "Alt + Space (Alt + Space)",
        "ctrl_shift_v": "Ctrl + Shift + V",
        "f8": "F8 Key (Single Key)",
        "f9": "F9 Key (Single Key)",
    }
else:
    DEFAULT_HOTKEY_CHOICE = os.getenv("WISPR_HOTKEY_CHOICE", "fn")
    HOTKEY = os.getenv("WISPR_HOTKEY", "fn")
    HOTKEY_OPTIONS = {
        "fn": "Left Fn (Globe 🌐 Key) [Recommended]",
        "option_space": "Option + Space (⌥ + Space)",
        "ctrl_space": "Control + Space (⌃ + Space)",
        "cmd_shift_d": "Command + Shift + D (⌘ + ⇧ + D)",
    }

# ----------------- STT (Speech-to-Text) -----------------
if IS_WINDOWS:
    STT_BACKEND = os.getenv("WISPR_STT_BACKEND", "gemini")
    STT_CHOICE = os.getenv("WISPR_STT_CHOICE", "gemini")
    STT_OPTIONS = {
        "gemini": "Google Gemini Flash (Free API, Highest Multilingual Accuracy) [Recommended]",
        "groq": "Groq Whisper Large-v3 (Free API, Ultra-Fast 300ms Cloud)",
    }
else:
    STT_BACKEND = os.getenv("WISPR_STT_BACKEND", "gemini")
    STT_CHOICE = os.getenv("WISPR_STT_CHOICE", "gemini")
    STT_OPTIONS = {
        "gemini": "Google Gemini Flash (Free API, Highest Multilingual & Tamil Accuracy) [Recommended]",
        "mlx_full": "Local MLX Whisper Large-v3 Full (100% Offline, 32-Layer Deep)",
        "mlx_turbo": "Local MLX Whisper Large-v3 Turbo (100% Offline, Fast)",
        "groq": "Groq Whisper Large-v3 (Free API, Ultra-Fast 300ms Cloud)",
    }

def resolve_stt_settings(choice: str):
    if choice == "gemini":
        return {"backend": "gemini", "model": "gemini-2.5-flash"}
    elif choice == "groq":
        return {"backend": "groq", "model": "whisper-large-v3"}
    elif choice == "mlx_full":
        return {"backend": "mlx-whisper", "model": "mlx-community/whisper-large-v3-mlx"}
    else:  # default mlx_turbo
        return {"backend": "mlx-whisper", "model": "mlx-community/whisper-large-v3-turbo"}

MLX_MODEL_NAME = os.getenv("WISPR_MLX_MODEL", "mlx-community/whisper-large-v3-turbo")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_STT_MODEL = "whisper-large-v3"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Language: "auto" for auto-detection, or ISO code like "en", "es", "fr", "ta", "de", etc.
DEFAULT_LANGUAGE = os.getenv("WISPR_LANGUAGE", "auto")

# ----------------- Tone & LLM Polishing -----------------
# Options: "smart_verbatim", "casual", "professional", "concise", "technical"
DEFAULT_TONE = os.getenv("WISPR_TONE", "professional")
# LLM Backend: "mlx-lm" (100% native offline on Mac), "ollama" (local Ollama server), "groq" (ultra-fast free cloud API)
LLM_BACKEND = os.getenv("WISPR_LLM_BACKEND", "mlx-lm")
# MLX LLM model options:
# - "mlx-community/Qwen2.5-1.5B-Instruct-4bit" (recommended for multilingual Indic & English, ~900MB)
# - "mlx-community/Llama-3.2-3B-Instruct-4bit" (recommended for English, ~1.8GB)
MLX_LLM_MODEL = os.getenv("WISPR_MLX_LLM_MODEL", "mlx-community/Qwen2.5-1.5B-Instruct-4bit")
# Ollama settings:
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
# Groq LLM settings:
GROQ_LLM_MODEL = os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")

# ----------------- Storage & Database -----------------
DB_PATH = DATA_DIR / "transcriptions.db"
TONES_FILE = BASE_DIR / "tones" / "prompts.json"

# ----------------- Theme / Appearance -----------------
DEFAULT_THEME = os.getenv("WISPR_THEME", "system")  # "system", "dark", "light"
THEME_OPTIONS = {
    "system": "🌓 Follow System",
    "dark": "🌙 Dark Mode",
    "light": "☀️ Light Mode",
}
