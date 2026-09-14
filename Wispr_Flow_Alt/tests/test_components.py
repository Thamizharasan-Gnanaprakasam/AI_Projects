"""
Comprehensive test suite for Wispr Flow Alt core components.
"""

import os
import sys
import unittest
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.database import save_transcription, get_history, clear_history
from core.tone_processor import ToneProcessor
from core.text_injector import get_active_app_name, MACOS_NATIVE_AVAILABLE
from core.audio_recorder import AudioRecorder
from core.languages import get_language_code, get_language_display_name, list_supported_languages

class TestWisprFlowAlt(unittest.TestCase):
    def setUp(self):
        clear_history()

    def test_database_operations(self):
        """Tests saving and retrieving history in SQLite."""
        rec_id = save_transcription(
            raw_text="um hey guys we need to deploy this now",
            polished_text="Hey team, we need to deploy this immediately.",
            tone="professional",
            language="en",
            target_app="Slack",
            duration_seconds=3.5
        )
        self.assertIsNotNone(rec_id)
        
        history = get_history(limit=5)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["target_app"], "Slack")
        self.assertEqual(history[0]["tone"], "professional")
        self.assertEqual(history[0]["polished_text"], "Hey team, we need to deploy this immediately.")

        # Test search
        search_results = get_history(search="deploy")
        self.assertEqual(len(search_results), 1)

    def test_tone_processor(self):
        """Tests loading tone presets and context handling."""
        processor = ToneProcessor()
        tones = processor.list_tones()
        self.assertTrue(len(tones) >= 5)
        tone_ids = [t["id"] for t in tones]
        self.assertIn("smart_verbatim", tone_ids)
        self.assertIn("casual", tone_ids)
        self.assertIn("professional", tone_ids)
        self.assertIn("concise", tone_ids)
        self.assertIn("technical", tone_ids)

    def test_macos_text_injector_availability(self):
        """Verifies native macOS active app detection."""
        self.assertTrue(MACOS_NATIVE_AVAILABLE, "PyObjC / Quartz must be available on macOS.")
        app_name = get_active_app_name()
        print(f"Detected frontmost app: {app_name}")
        self.assertTrue(len(app_name) > 0)

    def test_language_resolution(self):
        """Tests language normalization for Auto, Tamil, Hindi, English, etc."""
        self.assertEqual(get_language_code("auto"), "auto")
        self.assertEqual(get_language_code("Auto-Detect"), "auto")
        self.assertEqual(get_language_code("Tamil"), "ta")
        self.assertEqual(get_language_code("ta"), "ta")
        self.assertEqual(get_language_code("Hindi"), "hi")
        self.assertEqual(get_language_code("hi"), "hi")
        self.assertEqual(get_language_code("English"), "en")
        self.assertIn("Tamil", get_language_display_name("ta"))
        self.assertIn("Hindi", get_language_display_name("hi"))
        self.assertIn("Auto", get_language_display_name("auto"))

    def test_audio_recorder_wav_export(self):
        """Tests audio array to WAV conversion."""
        # Generate 1 second of synthetic 440Hz sine wave (silence / audio)
        sample_rate = 16000
        t = np.linspace(0, 1, sample_rate, endpoint=False)
        synthetic_audio = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        
        wav_path = AudioRecorder.save_wav(synthetic_audio, sample_rate)
        self.assertTrue(os.path.exists(wav_path))
        self.assertTrue(os.path.getsize(wav_path) > 1000)
        os.remove(wav_path)

    def test_audio_noise_cancellation(self):
        """Tests multi-stage noise suppression (highpass + spectral gating)."""
        sample_rate = 16000
        t = np.linspace(0, 1, sample_rate, endpoint=False, dtype=np.float32)
        
        # Simulated 300Hz tone (voice formant) + 50Hz electrical hum + background white noise
        speech_formant = 0.4 * np.sin(2 * np.pi * 300 * t)
        hum_50hz = 0.3 * np.sin(2 * np.pi * 50 * t)
        ambient_noise = 0.05 * np.random.normal(0, 1, len(t)).astype(np.float32)
        noisy_audio = (speech_formant + hum_50hz + ambient_noise).astype(np.float32)

        # Process with noise cancellation enabled
        clean_audio = AudioRecorder.preprocess_audio(
            noisy_audio,
            sample_rate=sample_rate,
            enable_noise_cancellation=True,
            highpass_cutoff=80.0,
            prop_decrease=0.75
        )

        self.assertTrue(len(clean_audio) > 0)
        # Verify 50Hz hum was suppressed by checking energy below 70Hz via FFT
        fft_orig = np.abs(np.fft.rfft(noisy_audio))
        fft_clean = np.abs(np.fft.rfft(clean_audio))
        freqs = np.fft.rfftfreq(len(noisy_audio), 1.0 / sample_rate)
        
        # Find index for 50Hz
        hum_idx = np.argmin(np.abs(freqs - 50))
        # Hum energy should be significantly attenuated
        orig_hum_energy = fft_orig[hum_idx]
        clean_hum_energy = fft_clean[hum_idx] if hum_idx < len(fft_clean) else 0
        self.assertLess(clean_hum_energy, orig_hum_energy * 0.4)

    def test_language_translation_safeguard(self):
        """Tests that unwanted translation to English is detected and rejected."""
        tp = ToneProcessor()
        # Non-ASCII input with English output should trigger detection
        self.assertTrue(tp._is_unwanted_translation("வணக்கம் நீங்கள் எப்படி இருக்கிறீர்கள்", "Hello how are you doing"))
        # Non-ASCII input with native output should NOT trigger detection
        self.assertFalse(tp._is_unwanted_translation("வணக்கம் நீங்கள் எப்படி இருக்கிறீர்கள்", "வணக்கம் நீங்கள் எப்படி இருக்கிறீர்கள்"))
        # Smart verbatim preserves native script and code-mixing
        out = tp.refine_text("Hello, எப்படி இருக்கீங்க?", tone="smart_verbatim", language="ta")
        self.assertIn("எப்படி", out)

    def test_chatbot_response_prevention(self):
        """Tests that conversational chatbot responses are detected and blocked."""
        tp = ToneProcessor()
        # Chatbot canned responses must be detected
        self.assertTrue(tp._is_chatbot_response("Sure, I can help you check for beautiful images from the website."))
        self.assertTrue(tp._is_chatbot_response("Certainly! Here is what you asked for."))
        self.assertTrue(tp._is_chatbot_response("As an AI assistant, I cannot access the internet."))
        self.assertTrue(tp._is_chatbot_response("Please provide me with the website URL so I can search."))
        
        # Valid polished speech must NOT be detected as chatbot responses
        self.assertFalse(tp._is_chatbot_response("Could you please check for some beautiful images from the website?"))
        self.assertFalse(tp._is_chatbot_response("Please send the financial summary by tomorrow."))
        self.assertFalse(tp._is_chatbot_response("வணக்கம், எப்படி இருக்கீங்க?"))

if __name__ == "__main__":
    unittest.main()


