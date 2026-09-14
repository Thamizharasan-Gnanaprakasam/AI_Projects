"""
Speech-to-Text (STT) Engine.
Supports local Apple Silicon MLX Whisper and ultra-fast Groq Whisper API.
"""

import os
import tempfile
import logging
from typing import Dict, Any, Optional, Union
import numpy as np
from scipy.io import wavfile

from config import (
    STT_BACKEND,
    MLX_MODEL_NAME,
    GROQ_API_KEY,
    GROQ_STT_MODEL,
    GEMINI_API_KEY,
    DEFAULT_LANGUAGE,
    SAMPLE_RATE,
)
from core.languages import get_language_code, get_language_display_name, get_language_prompt
from core.audio_recorder import AudioRecorder

logger = logging.getLogger(__name__)

class STTEngine:
    def __init__(
        self,
        backend: str = STT_BACKEND,
        model_name: str = MLX_MODEL_NAME,
        groq_api_key: str = GROQ_API_KEY,
        gemini_api_key: str = GEMINI_API_KEY,
    ):
        self.backend = backend
        self.model_name = model_name
        self.groq_api_key = groq_api_key
        self.gemini_api_key = gemini_api_key

    def transcribe(
        self,
        audio_input: Union[str, np.ndarray],
        language: str = DEFAULT_LANGUAGE
    ) -> Dict[str, Any]:
        """
        Transcribes audio to text.
        audio_input: path to wav file OR numpy float32 array (16kHz).
        language: "auto" for automatic detection, or ISO code (e.g., "en", "es", "ta", "fr").
        
        Returns:
            {"text": str, "language": str}
        """
        # Ensure we have both numpy representation and file path where needed
        audio_np: Optional[np.ndarray] = None
        audio_path: Optional[str] = None
        temp_wav_path: Optional[str] = None

        if isinstance(audio_input, np.ndarray):
            audio_np = audio_input.astype(np.float32)
        elif isinstance(audio_input, str):
            audio_path = audio_input
            # Attempt to read into numpy directly using scipy as fallback if ffmpeg is missing
            try:
                sr, data = wavfile.read(audio_path)
                if data.dtype == np.int16:
                    audio_np = (data / 32768.0).astype(np.float32)
                elif data.dtype == np.int32:
                    audio_np = (data / 2147483648.0).astype(np.float32)
                else:
                    audio_np = data.astype(np.float32)
            except Exception as e:
                logger.debug(f"Could not load audio file via scipy ({e}), will use audio_path.")

        try:
            # Route to appropriate backend
            if self.backend == "gemini" and self.gemini_api_key:
                if not audio_path:
                    temp_wav_path = self._save_temp_wav(audio_np)
                    audio_path = temp_wav_path
                return self._transcribe_gemini(audio_path, language)

            elif self.backend == "groq" and self.groq_api_key:
                if not audio_path:
                    temp_wav_path = self._save_temp_wav(audio_np)
                    audio_path = temp_wav_path
                return self._transcribe_groq(audio_path, language)

            else:
                # Default to local Apple Silicon mlx-whisper
                input_for_mlx = audio_np if audio_np is not None else audio_path
                return self._transcribe_mlx(input_for_mlx, language)

        finally:
            if temp_wav_path and os.path.exists(temp_wav_path):
                try:
                    os.remove(temp_wav_path)
                except OSError:
                    pass

    @staticmethod
    def _save_temp_wav(audio_np: np.ndarray) -> str:
        """Saves numpy audio array to a temporary 16kHz WAV file."""
        clipped = np.clip(audio_np, -1.0, 1.0)
        int16_data = (clipped * 32767).astype(np.int16)
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wavfile.write(temp_file.name, SAMPLE_RATE, int16_data)
        temp_file.close()
        return temp_file.name

    def _transcribe_mlx(self, audio_input: Union[str, np.ndarray], language: str) -> Dict[str, Any]:
        """Transcribe using Apple Silicon mlx-whisper with anti-hallucination settings."""
        try:
            import mlx_whisper
        except ImportError:
            raise RuntimeError("mlx-whisper is not installed in the environment.")

        # If input is numpy array, ensure it is preprocessed and normalized
        if isinstance(audio_input, np.ndarray):
            audio_input = AudioRecorder.preprocess_audio(audio_input)

        # Normalize language: if 'auto', pass None to let whisper automatically detect language
        lang_code = get_language_code(language)
        lang_arg = None if lang_code == "auto" else lang_code

        logger.info(f"Running mlx-whisper with model: {self.model_name}, lang: {lang_arg or 'auto-detect'}...")
        
        transcribe_kwargs = {
            "path_or_hf_repo": self.model_name,
            "task": "transcribe",  # Explicitly transcribe in the spoken/selected language, never translate!
            "condition_on_previous_text": False,
            "temperature": 0.0,
            "compression_ratio_threshold": 2.4,
            "no_speech_threshold": 0.6,
        }
        
        # Prime Whisper's tokenizer with vocabulary (and code-mixing for auto mode)
        prompt = get_language_prompt(lang_code)
        if prompt:
            transcribe_kwargs["initial_prompt"] = prompt

        if lang_arg:
            transcribe_kwargs["language"] = lang_arg

        result = mlx_whisper.transcribe(audio_input, **transcribe_kwargs)
        
        raw_text = result.get("text", "").strip()
        detected_language = result.get("language", lang_code)

        # Clean token repetition loops, special tokens, and acoustic confusions
        raw_text = self._clean_transcript(raw_text, lang_code)
        
        return {
            "text": raw_text,
            "language": detected_language,
            "segments": result.get("segments", [])
        }

    def _transcribe_gemini(self, audio_path: str, language: str) -> Dict[str, Any]:
        """Transcribe using Google Gemini 2.0 Flash Audio REST API (free tier, state-of-the-art accuracy)."""
        import base64
        import requests

        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set. Please add your free key in Settings or .env.")

        with open(audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")

        lang_code = get_language_code(language)
        lang_display = get_language_display_name(language)

        if lang_code == "auto":
            instruction = (
                "Listen to this audio carefully. The user may be speaking from a distance or across the room. "
                "Carefully listen through room acoustics, reverberation, and lower volume. "
                "Accurately identify the spoken language (such as Tamil, Hindi, Spanish, French, German, Japanese, Chinese, or English). "
                "Transcribe the spoken speech verbatim in the exact native script of the spoken language "
                "(for example Tamil in Tamil script தமிழ், Hindi in Devanagari script हिन्दी, English in English, or colloquial code-mixed Tanglish/Hinglish if spoken that way). "
                "STRICT RULES:\n"
                "- Output ONLY the exact transcribed words in their native script.\n"
                "- Do NOT default to English if the user is speaking another language from a distance.\n"
                "- Do NOT translate into English or any other language.\n"
                "- Do NOT reply to questions or act like an assistant.\n"
                "- Do NOT add quotes, markdown formatting, or preamble."
            )
        else:
            instruction = (
                f"Listen to this audio carefully. The user may be speaking from a distance or across the room in {lang_display}.\n"
                f"Transcribe the spoken speech verbatim in {lang_display} native script.\n"
                "STRICT RULES:\n"
                f"- Output ONLY the exact transcribed words in {lang_display}.\n"
                "- Do NOT translate into English or any other language.\n"
                "- Do NOT reply to questions or act like an assistant.\n"
                "- Do NOT add quotes, markdown formatting, or preamble."
            )

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": "audio/wav",
                                "data": audio_b64
                            }
                        },
                        {
                            "text": instruction
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 1024
            }
        }

        # Models to try in order of priority (fastest non-exhausted models)
        models_to_try = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3-flash-preview", "gemini-flash-latest"]
        last_error = ""

        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_api_key}"
            try:
                resp = requests.post(url, json=payload, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_text = ""
                    try:
                        raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    except (KeyError, IndexError):
                        logger.warning(f"Unexpected Gemini response structure: {data}")

                    # Post-clean transcript
                    raw_text = self._clean_transcript(raw_text, lang_code)

                    return {
                        "text": raw_text,
                        "language": lang_code,
                        "segments": []
                    }
                else:
                    last_error = f"{resp.status_code}: {resp.text}"
                    logger.warning(f"Gemini model {model} returned {resp.status_code}, trying fallback...")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Gemini request failed for model {model}: {e}")

        raise RuntimeError(f"Gemini STT failed: {last_error}")

    def _transcribe_groq(self, audio_path: str, language: str) -> Dict[str, Any]:
        """Transcribe using Groq Cloud Whisper API (ultra-fast, free tier available)."""
        import requests
        
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY is not set.")

        headers = {
            "Authorization": f"Bearer {self.groq_api_key}"
        }
        
        lang_code = get_language_code(language)
        data = {
            "model": GROQ_STT_MODEL,
            "response_format": "verbose_json"
        }
        if lang_code != "auto":
            data["language"] = lang_code

        with open(audio_path, "rb") as f:
            files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
            response = requests.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers=headers,
                data=data,
                files=files,
                timeout=30
            )

        if response.status_code != 200:
            raise RuntimeError(f"Groq STT failed: {response.status_code} - {response.text}")

        res_json = response.json()
        raw_text = res_json.get("text", "").strip()
        raw_text = self._clean_transcript(raw_text, lang_code)

        return {
            "text": raw_text,
            "language": res_json.get("language", language),
            "segments": res_json.get("segments", [])
        }

    @staticmethod
    def _clean_transcript(text: str, lang_code: str = "auto") -> str:
        """Removes token loop artifacts, Whisper tags, and normalizes acoustic distortions."""
        if not text:
            return ""

        import re
        # Remove Whisper internal special tokens like <|ta|>, <|transcribe|>, <|notimestamps|>
        text = re.sub(r'<\|[a-zA-Z0-9_.-]+\|>', '', text)

        # Collapse token repetition loops (e.g. "ard,ard,ard,ard" or "word word word word")
        text = re.sub(r'(\b\w+[,.]?\s*)\1{3,}', r'\1', text)

        # Sanitize script and colloquial acoustic substitutions
        if lang_code in ("ta", "auto"):
            text = STTEngine._sanitize_indic_script(text, "ta")
            # Acoustic confusions in colloquial Tamil
            text = re.sub(r'(^|\s)இப்படி(\s+இருக்கீ)', r'\1எப்படி\2', text)
            text = re.sub(r'(^|\s)நானா(\s+இருக்கீ)', r'\1நல்லா\2', text)
            text = re.sub(r'(^|\s)ஏப்படி(\s+|$|[.,?!])', r'\1எப்படி\2', text)
            text = re.sub(r'இருக்கியங்க(ளா)?', r'இருக்கீங்க\1', text)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @staticmethod
    def _sanitize_indic_script(text: str, lang_code: str) -> str:
        """
        Guarantees that if Tamil was spoken or selected, any Devanagari/Hindi subwords
        accidentally emitted by Whisper are converted to proper Tamil script.
        """
        if not text:
            return text

        if lang_code in ("ta", "auto"):
            has_devanagari = any('\u0900' <= c <= '\u097F' for c in text)
            if has_devanagari:
                devanagari_to_tamil = {
                    'अ': 'அ', 'ஆ': 'ஆ', 'இ': 'இ', 'ई': 'ஈ', 'उ': 'உ', 'ऊ': 'ஊ', 'ए': 'எ', 'ऐ': 'ஐ', 'ओ': 'ஒ', 'औ': 'ஔ',
                    'क': 'க', 'ख': 'க', 'ग': 'க', 'घ': 'க', 'ङ': 'ங',
                    'च': 'ச', 'छ': 'ச', 'ज': 'ஜ', 'झ': 'ச', 'ञ': 'ஞ',
                    'ट': 'ட', 'ठ': 'ட', 'ड': 'ட', 'ढ': 'ட', 'ण': 'ண',
                    'त': 'த', 'थ': 'த', 'द': 'த', 'ध': 'த', 'न': 'ந',
                    'प': 'ப', 'फ': 'ப', 'ब': 'ப', 'भ': 'ப', 'म': 'ம',
                    'य': 'ய', 'ர': 'ர', 'ल': 'ல', 'व': 'வ', 'श': 'ஶ', 'ष': 'ஷ', 'स': 'ஸ', 'ह': 'ஹ',
                    'ळ': 'ள', 'ழ': 'ழ', 'ற': 'ற', 'ன': 'ன',
                    'ा': 'ா', 'ि': 'ி', 'ी': 'ீ', 'ु': 'ு', 'ू': 'ூ', 'े': 'ே', 'ै': 'ை', 'ो': 'ொ', 'ौ': 'ௌ',
                    '्': '்', 'ं': 'ம்', 'ः': 'ஃ',
                    'ड़': 'ட', 'ढ़': 'ட', 'फ़': 'ப', 'ज़': 'ஜ', 'ग़': 'க',
                    'ड': 'ட', 'ी': 'ீ', 'े': 'ே', 'ं': 'ங்',
                    '़': '',
                }
                import re
                text = ''.join(devanagari_to_tamil.get(c, c) for c in text)
                text = re.sub(r'இப[ட|டி|ட़]+', 'எப்படி', text)
                text = re.sub(r'இரக[ீ|ி]+[எ|ஏ]*[ந|ங]*[க|கே|கோ]*[ே|ை]*', 'இருக்கீங்க', text)
                text = re.sub(r'நல்லா', 'நல்லா', text)
                text = re.sub(r'தா$', 'டா', text)

        return text
