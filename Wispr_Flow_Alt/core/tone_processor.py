"""
Tone processor & Context LLM module.
Refines raw speech transcripts into selected tones and maintains continuous context.
"""

import json
import re
import logging
from typing import Dict, Any, List, Optional
import requests

from config import (
    TONES_FILE,
    LLM_BACKEND,
    DEFAULT_TONE,
    OLLAMA_HOST,
    OLLAMA_MODEL,
    GROQ_API_KEY,
    GROQ_LLM_MODEL,
    MLX_LLM_MODEL,
    GEMINI_API_KEY,
)
from core.languages import get_language_display_name

logger = logging.getLogger(__name__)

class ToneProcessor:
    def __init__(
        self,
        backend: str = LLM_BACKEND,
        tones_file: str = str(TONES_FILE),
        ollama_host: str = OLLAMA_HOST,
        ollama_model: str = OLLAMA_MODEL,
        groq_api_key: str = GROQ_API_KEY,
        groq_model: str = GROQ_LLM_MODEL,
        mlx_model_name: str = MLX_LLM_MODEL,
        gemini_api_key: str = GEMINI_API_KEY,
    ):
        self.backend = backend
        self.tones_file = tones_file
        self.ollama_host = ollama_host.rstrip("/")
        self.ollama_model = ollama_model
        self.groq_api_key = groq_api_key
        self.groq_model = groq_model
        self.mlx_model_name = mlx_model_name
        self.gemini_api_key = gemini_api_key
        self._mlx_model = None
        self._mlx_tokenizer = None
        
        # Load available tones
        self.tones = self._load_tones()
        # Rolling context window of previous utterances
        self.recent_context: List[Dict[str, str]] = []
        self.max_context_turns = 3

    def _load_tones(self) -> Dict[str, Any]:
        """Loads prompt configurations for all supported tones."""
        try:
            with open(self.tones_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading tones file: {e}")
            return {
                "smart_verbatim": {
                    "name": "Smart Verbatim",
                    "system_prompt": "Clean up speech fillers and fix punctuation while keeping exact words."
                }
            }

    def list_tones(self) -> List[Dict[str, str]]:
        """Returns metadata for all available tones."""
        return [
            {"id": key, "name": val.get("name", key), "description": val.get("description", "")}
            for key, val in self.tones.items()
        ]

    def _clean_verbatim(self, text: str) -> str:
        """Removes speech fillers and normalizes common loanwords while preserving exact code-mixing."""
        import re
        loanwords = [
            (r'(^|\s)(ஹலோ|ஹெலோ|हैலோ),?', r'\1Hello,'),
            (r'(^|\s)(ஹாய்|हाय),?', r'\1Hi,'),
            (r'(^|\s)(ஓகே|ஒகே|ओके)', r'\1OK'),
            (r'(^|\s)(தேங்க்ஸ்|थैंक्स)', r'\1Thanks'),
            (r'(^|\s)இப்படி(\s+இருக்கீ)', r'\1எப்படி\2'),
            (r'(^|\s)நானா(\s+இருக்கீ)', r'\1நல்லா\2'),
            (r'(^|\s)(ஏய் படி|ஏப்படி|எப்டி|எப்படிீ)', r'\1எப்படி'),
            (r'(^|\s)(இருக்கியுங்க|இருக்கியங்க|இருக்கிறீங்கள்|இருக்கீங்க்கே)', r'\1இருக்கீங்க'),
            (r'(^|\s)(நல்லார்க்கிறீர்கள்|நல்லார்க்கிங்க)', r'\1நல்லா இருக்கீங்க'),
        ]

        res = text
        for pat, rep in loanwords:
            res = re.sub(pat, rep, res)

        # Strip common standalone filler words
        res = re.sub(r'\b(um|uh|er|ah)\b,?\s*', '', res, flags=re.IGNORECASE)
        # Strip immediate repeated duplicate words
        res = re.sub(r'\b(\w+)\s+\1\b', r'\1', res, flags=re.IGNORECASE)
        # Normalize whitespace and double punctuation
        res = re.sub(r'\s+', ' ', res)
        res = re.sub(r',\s*,', ',', res).strip()

        # Capitalize leading letter if ascii
        if res and res[0].isascii() and res[0].isalpha():
            res = res[0].upper() + res[1:]
        return res

    @staticmethod
    def _is_unwanted_translation(input_text: str, output_text: str) -> bool:
        """
        Detects if the LLM mistakenly translated non-English speech into English.
        Covers both non-ASCII native scripts AND Latin-script non-English (Hinglish/Tanglish/Spanish/French).
        """
        if not input_text or not output_text:
            return False

        # Case 1: Native non-ASCII script in input, but pure ASCII in output
        in_non_ascii = sum(1 for c in input_text if ord(c) > 127)
        out_non_ascii = sum(1 for c in output_text if ord(c) > 127)
        if in_non_ascii >= 3 and out_non_ascii == 0:
            return True

        # Case 2: Latin-script non-English / Hinglish (e.g. "mere naam kya hai" -> "What is my name?")
        common_en = {
            'what', 'is', 'are', 'my', 'your', 'name', 'how', 'you', 'hello',
            'this', 'that', 'the', 'a', 'an', 'i', 'we', 'they', 'he', 'she', 'it',
            'can', 'will', 'do', 'does', 'did', 'have', 'has', 'had', 'to', 'in',
            'on', 'at', 'by', 'for', 'with', 'about', 'please', 'thank', 'thanks',
            'good', 'bad', 'yes', 'no', 'why', 'when', 'where', 'who'
        }
        in_words = [w.lower().strip('?,.!;:') for w in input_text.split() if w]
        out_words = [w.lower().strip('?,.!;:') for w in output_text.split() if w]

        in_en = sum(1 for w in in_words if w in common_en)
        out_en = sum(1 for w in out_words if w in common_en)
        shared = set(in_words).intersection(out_words)

        if len(in_words) >= 2 and in_en == 0 and out_en >= max(2, int(len(out_words) * 0.6)) and len(shared) == 0:
            return True

        return False

    @staticmethod
    def _is_hallucination(input_text: str, output_text: str) -> bool:
        """
        Detects if the LLM output is a hallucination that lost the user's spoken words.
        If the output shares less than 25% character n-grams or words with the input,
        it is flagged as a hallucination and reverted to clean verbatim.
        """
        if not input_text or not output_text:
            return False

        words_in = set(w.lower() for w in input_text.split() if len(w) > 1)
        words_out = set(w.lower() for w in output_text.split() if len(w) > 1)
        if words_in:
            word_sim = len(words_in.intersection(words_out)) / len(words_in)
        else:
            word_sim = 1.0

        def get_bigrams(s):
            clean = s.lower().replace(" ", "")
            return set(clean[i:i+2] for i in range(len(clean)-1))

        bg_in = get_bigrams(input_text)
        bg_out = get_bigrams(output_text)
        if bg_in:
            bg_sim = len(bg_in.intersection(bg_out)) / len(bg_in)
        else:
            bg_sim = 1.0

        similarity = max(word_sim, bg_sim)
        return similarity < 0.25

    @staticmethod
    def _is_chatbot_response(output_text: str) -> bool:
        """
        Detects if the LLM mistakenly answered a question or acted as a chatbot/assistant
        rather than polishing the dictated speech.
        """
        if not output_text:
            return False
        clean = output_text.strip()
        patterns = [
            r"^(sure|certainly|of course|i can help|as an ai|i'd be happy|i would be happy|here is|here's|i am ready|feel free to|let me know if you need)\b",
            r"\b(please provide me with|what website|what url|how can i assist|how can i help)\b",
            r"^(i cannot|i'm unable to|as a language model)\b",
        ]
        for pat in patterns:
            if re.search(pat, clean, re.IGNORECASE):
                return True
        return False

    def refine_text(
        self,
        raw_text: str,
        tone: str = DEFAULT_TONE,
        language: str = "auto",
        target_app: Optional[str] = None,
        custom_instructions: Optional[str] = None
    ) -> str:
        """
        Applies LLM tone refinement and context preservation to raw transcription.
        Falls back to raw_text if LLM is unavailable, attempts translation, or hallucinates.
        """
        cleaned_raw = raw_text.strip()
        if not cleaned_raw:
            return ""

        # Fast and zero-hallucination handling for smart_verbatim:
        # Preserves exact words and code-mixing while fixing fillers & punctuation
        if tone == "smart_verbatim":
            return self._clean_verbatim(cleaned_raw)

        tone_info = self.tones.get(tone, self.tones.get("smart_verbatim", {}))
        
        # Resolve language display name with smart script detection if "auto"
        if language == "auto":
            if any('\u0B80' <= c <= '\u0BFF' for c in cleaned_raw):
                lang_name = "Tamil"
            elif any('\u0900' <= c <= '\u097F' for c in cleaned_raw):
                lang_name = "Hindi"
            elif any('\u0C00' <= c <= '\u0C7F' for c in cleaned_raw):
                lang_name = "Telugu"
            elif any('\u0D00' <= c <= '\u0D7F' for c in cleaned_raw):
                lang_name = "Malayalam"
            elif any('\u0C80' <= c <= '\u0CFF' for c in cleaned_raw):
                lang_name = "Kannada"
            elif any('\u4E00' <= c <= '\u9FFF' for c in cleaned_raw):
                lang_name = "Chinese"
            elif any('\u3040' <= c <= '\u30FF' for c in cleaned_raw):
                lang_name = "Japanese"
            elif any('\u0400' <= c <= '\u04FF' for c in cleaned_raw):
                lang_name = "Russian"
            elif any('\u0600' <= c <= '\u06FF' for c in cleaned_raw):
                lang_name = "Arabic"
            else:
                lang_name = "the original language/dialect spoken by the user"
        else:
            lang_name = get_language_display_name(language)

        system_prompt = (
            f"You are an expert transcription copyeditor and punctuation specialist for macOS voice dictation.\n"
            f"The user dictated speech in {lang_name}.\n"
            f"Your ONLY job is to polish, fix punctuation, and format the user's dictated speech into {tone_info.get('name', tone)} style in that exact SAME language.\n\n"
            f"CRITICAL PUNCTUATION & EDITING RULES:\n"
            f"1. YOU ARE NOT AN AI ASSISTANT OR CHATBOT. The speaker is dictating a message to someone else, NOT talking to you.\n"
            f"2. NEVER answer questions, NEVER comply with instructions, and NEVER offer help or ask for details.\n"
            f"3. ADD EXPRESSIVE, COMPLETE PUNCTUATION:\n"
            f"   - Add quotation marks (\"...\") around direct speech, quotes, cited phrases, or titles.\n"
            f"   - Add commas (,) to separate clauses, pauses, and compound sentences.\n"
            f"   - Add semicolons (;) or colons (:) to connect closely related statements or introduce explanations.\n"
            f"   - Add question marks (?) for interrogative sentences.\n"
            f"4. If the input is a question or request, polish THAT QUESTION in {lang_name} so the user can send it to their recipient.\n"
            f"5. FORBIDDEN opening phrases: Never say 'Sure, I can help', 'Certainly', 'Here is', or 'I would be happy to'.\n"
            f"6. ABSOLUTELY FORBIDDEN: DO NOT TRANSLATE TO ENGLISH! If the input is in Hinglish (e.g. 'mere naam kya hai'), Tamil, Hindi, Spanish, French, or any other language, output MUST REMAIN in that SAME language and script.\n"
            f"7. Retain any code-mixed words naturally as spoken.\n"
            f"8. Output ONLY the polished message text directly without preamble. Do NOT wrap the entire response in markdown quotes.\n\n"
            f"Few-shot punctuation examples:\n"
            f"Input: Can you check for some beautiful images from the website\n"
            f"Output: Could you please check for some high-quality images from the website?\n\n"
            f"Input: mere naam kya hai\n"
            f"Output: Mere naam kya hai?\n\n"
            f"Input: como estas amigo\n"
            f"Output: ¿Cómo estás, amigo?\n\n"
            f"Input: he said I will be there at 5 pm so please wait for me\n"
            f"Output: He said, \"I will be there at 5 PM\"; please wait for me."
        )

        if custom_instructions:
            system_prompt += f"\nAdditional Instructions: {custom_instructions}"

        user_content = f"[DICTATED SPEECH TO POLISH]:\n{cleaned_raw}"

        try:
            if self.gemini_api_key:
                # Gemini provides unmatched punctuation (quotes, commas, semicolons) across all 100+ languages
                try:
                    refined = self._call_gemini(system_prompt, user_content)
                except Exception as e:
                    logger.warning(f"Gemini tone call failed ({e}), falling back to {self.backend}...")
                    if self.backend == "groq" and self.groq_api_key:
                        refined = self._call_groq(system_prompt, user_content)
                    else:
                        refined = self._call_mlx_lm(system_prompt, user_content)
            elif self.backend == "groq" and self.groq_api_key:
                refined = self._call_groq(system_prompt, user_content)
            elif self.backend == "ollama":
                refined = self._call_ollama(system_prompt, user_content)
            else:
                refined = self._call_mlx_lm(system_prompt, user_content)

            final_text = refined.strip() if refined else cleaned_raw

            # Strip leading "[POLISHED OUTPUT]:" if generated
            final_text = re.sub(r"^(\[POLISHED (OUTPUT|SPEECH)\]:?|Polished text:?)\s*", "", final_text, flags=re.IGNORECASE).strip()

            # Chatbot Response Safeguard: If the LLM tried to answer the user as an assistant
            if self._is_chatbot_response(final_text):
                logger.warning(
                    f"LLM hallucinated chatbot response ({final_text!r}). Reverting to clean verbatim speech."
                )
                final_text = self._clean_verbatim(cleaned_raw)

            # Translation Safeguard: If the LLM hallucinated an English translation, reject it!
            elif self._is_unwanted_translation(cleaned_raw, final_text):
                logger.warning(
                    f"LLM hallucinated English translation for {language} input! Reverting to clean verbatim text."
                )
                final_text = self._clean_verbatim(cleaned_raw)

            # Hallucination Safeguard: If the LLM output shares little to no content with input, reject it!
            elif self._is_hallucination(cleaned_raw, final_text):
                logger.warning(
                    f"LLM hallucinated low-fidelity output ({final_text!r} vs {cleaned_raw!r}). Reverting to clean verbatim text."
                )
                final_text = self._clean_verbatim(cleaned_raw)

            # Update rolling context
            self.recent_context.append({"text": final_text, "tone": tone})
            if len(self.recent_context) > self.max_context_turns:
                self.recent_context.pop(0)

            return final_text

        except Exception as e:
            logger.warning(f"Tone refinement failed ({e}). Returning raw transcription.")
            return cleaned_raw

    def process_utterance(
        self,
        raw_text: str,
        tone: str = DEFAULT_TONE,
        language: str = "auto",
        target_app: Optional[str] = None,
        custom_instructions: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Processes a raw transcript and returns a dict containing:
        - 'polished_text': Tone-refined text in original language
        - 'raw_in_english': Spoken text written phonetically in English/Latin script (transliteration)
        - 'english_translation': Spoken text translated into English
        """
        cleaned_raw = raw_text.strip()
        if not cleaned_raw:
            return {
                "polished_text": "",
                "raw_in_english": "",
                "english_translation": ""
            }

        # Only take pure English shortcut if language is explicitly English
        if language == "en":
            polished = self.refine_text(
                raw_text=cleaned_raw,
                tone=tone,
                language="en",
                target_app=target_app,
                custom_instructions=custom_instructions
            )
            return {
                "polished_text": polished,
                "raw_in_english": cleaned_raw,
                "english_translation": cleaned_raw
            }

        # Fast path for smart_verbatim: preserve exact words for polished_text
        fast_polished = self._clean_verbatim(cleaned_raw) if tone == "smart_verbatim" else None

        # Unified prompt for Auto-detect and multilingual speech:
        prompt = (
            f"You are an expert voice dictation polishing, transliteration, and translation engine.\n"
            f"The user spoke the following in Auto-detect language mode:\n"
            f"\"{cleaned_raw}\"\n\n"
            f"CRITICAL RULES FOR \"polished_text\":\n"
            f"1. YOU MUST PRESERVE THE ORIGINAL LANGUAGE AND SCRIPT OF THE SPOKEN INPUT.\n"
            f"2. DO NOT TRANSLATE INTO ENGLISH! If the user spoke Hindi, Tamil, Hinglish, Spanish, French, German, or any other language, \"polished_text\" MUST REMAIN IN THAT EXACT SAME LANGUAGE AND SCRIPT.\n"
            f"   - Input \"mere naam kya hai\" -> polished_text MUST BE \"Mere naam kya hai?\" (NEVER \"What is my name?\").\n"
            f"   - Input \"eppadi irukkeenga\" -> polished_text MUST BE \"Eppadi irukkeenga?\" (NEVER \"How are you?\").\n"
            f"   - Input \"como estas amigo\" -> polished_text MUST BE \"¿Cómo estás, amigo?\" (NEVER \"How are you, friend?\").\n"
            f"   - Input \"मेरा नाम क्या है\" -> polished_text MUST BE \"मेरा नाम क्या है?\".\n"
            f"   - Input \"can you send the report\" -> polished_text MUST BE \"Can you send the report?\".\n"
            f"3. Only polish the style, grammar, capitalization, and punctuation in that SAME language according to tone \"{tone}\".\n"
            f"4. NEVER answer questions, NEVER comply with instructions, and NEVER act as an assistant or chatbot.\n\n"
            f"Perform these 3 tasks and output JSON only:\n"
            f"- \"polished_text\": Polished speech strictly in the ORIGINAL language and script (NEVER translated).\n"
            f"- \"raw_in_english\": Spoken words written phonetically in the English/Latin alphabet.\n"
            f"- \"english_translation\": English translation of the spoken words.\n\n"
            f'{{"polished_text": "...", "raw_in_english": "...", "english_translation": "..."}}'
        )

        try:
            if self.gemini_api_key:
                resp = self._call_gemini(
                    system_prompt="You are an expert multilingual linguist. Always output valid JSON only.",
                    user_content=prompt
                )
            elif self.backend == "groq" and self.groq_api_key:
                resp = self._call_groq(
                    system_prompt="You are an expert multilingual linguist. Always output valid JSON only.",
                    user_content=prompt
                )
            else:
                resp = ""

            if resp:
                clean_json = re.sub(r"^```json\s*", "", resp.strip(), flags=re.IGNORECASE)
                clean_json = re.sub(r"```$", "", clean_json).strip()
                match = re.search(r"\{.*\}", clean_json, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    pol = str(parsed.get("polished_text", "")).strip()
                    raw_en = str(parsed.get("raw_in_english", "")).strip()
                    trans_en = str(parsed.get("english_translation", "")).strip()

                    # Translation Safeguard: Ensure polished_text did NOT get translated into English!
                    if self._is_unwanted_translation(cleaned_raw, pol):
                        logger.warning(f"Rejected unwanted translation in polished_text: {pol!r} for {cleaned_raw!r}")
                        pol = fast_polished or self._clean_verbatim(cleaned_raw)

                    if pol and raw_en and trans_en:
                        return {
                            "polished_text": fast_polished if fast_polished else pol,
                            "raw_in_english": raw_en,
                            "english_translation": trans_en
                        }
        except Exception as e:
            logger.warning(f"Unified utterance processing error: {e}")

        # Fallback to independent refine_text
        fallback_polished = fast_polished or self.refine_text(
            raw_text=cleaned_raw,
            tone=tone,
            language=language,
            target_app=target_app,
            custom_instructions=custom_instructions
        )
        return {
            "polished_text": fallback_polished,
            "raw_in_english": cleaned_raw,
            "english_translation": fallback_polished
        }


    def _call_mlx_lm(self, system_prompt: str, user_content: str) -> str:
        """Calls native local Apple Silicon MLX-LM model."""
        try:
            from mlx_lm import load, generate
        except ImportError:
            raise RuntimeError("mlx-lm package is not installed.")

        if self._mlx_model is None or self._mlx_tokenizer is None:
            logger.info(f"Loading local MLX LLM: {self.mlx_model_name}...")
            self._mlx_model, self._mlx_tokenizer = load(self.mlx_model_name)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        prompt = self._mlx_tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        response = generate(
            self._mlx_model,
            self._mlx_tokenizer,
            prompt=prompt,
            max_tokens=350,
            verbose=False
        )
        clean_res = response.strip()
        if (clean_res.startswith('"') and clean_res.endswith('"')) or (clean_res.startswith("'") and clean_res.endswith("'")):
            clean_res = clean_res[1:-1].strip()
        return clean_res

    def clear_context(self):
        """Resets the conversation context."""
        self.recent_context.clear()

    def _call_groq(self, system_prompt: str, user_content: str) -> str:
        """Calls Groq Chat API."""
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.groq_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.3,
            "max_tokens": 1024
        }
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        raise RuntimeError(f"Groq API error: {resp.status_code} - {resp.text}")

    def _call_gemini(self, system_prompt: str, user_content: str) -> str:
        """Calls Google Gemini Flash for rich punctuation and tone polishing."""
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        models_to_try = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3-flash-preview", "gemini-flash-latest"]
        last_error = ""

        combined_prompt = f"{system_prompt}\n\n{user_content}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": combined_prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1024
            }
        }

        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_api_key}"
            try:
                resp = requests.post(url, json=payload, timeout=12)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
                else:
                    last_error = f"{resp.status_code}: {resp.text}"
            except Exception as e:
                last_error = str(e)

        raise RuntimeError(f"Gemini tone refinement failed: {last_error}")

    def _call_ollama(self, system_prompt: str, user_content: str) -> str:
        """Calls local Ollama API."""
        url = f"{self.ollama_host}/api/chat"
        payload = {
            "model": self.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "stream": False,
            "options": {
                "temperature": 0.3
            }
        }
        resp = requests.post(url, json=payload, timeout=20)
        if resp.status_code == 200:
            return resp.json().get("message", {}).get("content", "")
        raise RuntimeError(f"Ollama API error: {resp.status_code} - {resp.text}")
