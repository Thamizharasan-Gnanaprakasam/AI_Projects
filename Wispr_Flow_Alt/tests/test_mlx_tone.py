"""
Test script to verify native MLX-LM local tone refinement on Apple Silicon.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.tone_processor import ToneProcessor

def test_local_tone_refinement():
    print("Initializing ToneProcessor with local MLX-LM...")
    # Use ultra-fast compact Qwen2.5 model for rapid test
    processor = ToneProcessor(
        backend="mlx-lm",
        mlx_model_name="mlx-community/Qwen2.5-0.5B-Instruct-4bit"
    )

    raw_speech = "um hey john like we gotta reschedule the sync tomorrow cause the deployment is running late you know"
    
    print(f"\nRaw Input: {raw_speech}\n")
    
    for tone in ["smart_verbatim", "casual", "professional", "concise"]:
        print(f"--- Testing tone: {tone} ---")
        polished = processor.refine_text(raw_speech, tone=tone, language="en")
        print(f"Result [{tone}]:\n{polished}\n")

if __name__ == "__main__":
    test_local_tone_refinement()
