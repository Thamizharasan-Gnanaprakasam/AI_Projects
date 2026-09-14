"""
Test script to verify MLX Whisper transcription on a short generated audio snippet.
"""

import os
import sys
import numpy as np

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.stt_engine import STTEngine
from core.audio_recorder import AudioRecorder

def test_stt_on_audio():
    print("Testing MLX Whisper initialization and inference...")
    # Use whisper-tiny for fast test verification
    engine = STTEngine(backend="mlx-whisper", model_name="mlx-community/whisper-tiny")
    
    # Generate 1.5 seconds of silence/ambient tone (16kHz)
    sample_rate = 16000
    t = np.linspace(0, 1.5, int(sample_rate * 1.5), endpoint=False)
    audio = (0.01 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    
    print("Running transcription on test audio...")
    result = engine.transcribe(audio, language="auto")
    print("Transcription result:", result)
    print("STT test passed successfully!")

if __name__ == "__main__":
    test_stt_on_audio()
