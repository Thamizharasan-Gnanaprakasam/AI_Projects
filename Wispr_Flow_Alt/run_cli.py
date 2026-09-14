"""
Interactive CLI & Service Runner for Wispr Flow Alternative.
Provides hotkey-driven or interactive dictation with live cursor insertion.
"""

import sys
import time
import argparse
import threading
import logging
from typing import Optional

from config import (
    DEFAULT_TONE,
    DEFAULT_LANGUAGE,
    HOTKEY,
    STT_BACKEND,
    LLM_BACKEND,
    MLX_MODEL_NAME,
)
from core.audio_recorder import AudioRecorder
from core.stt_engine import STTEngine
from core.tone_processor import ToneProcessor
from core.text_injector import inject_text_at_cursor, get_active_app_name
from core.database import save_transcription, get_history, clear_history
from core.languages import list_supported_languages, get_language_code, get_language_display_name

# Setup clean console logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("WisprAlt")

class WisprFlowAltApp:
    def __init__(
        self,
        tone: str = DEFAULT_TONE,
        language: str = DEFAULT_LANGUAGE,
        stt_backend: str = STT_BACKEND,
        llm_backend: str = LLM_BACKEND,
        auto_paste: bool = True
    ):
        self.current_tone = tone
        self.current_language = language
        self.auto_paste = auto_paste
        
        logger.info(f"Initializing STT Engine ({stt_backend})...")
        self.stt_engine = STTEngine(backend=stt_backend, model_name=MLX_MODEL_NAME)
        
        logger.info(f"Initializing Tone Processor ({llm_backend})...")
        self.tone_processor = ToneProcessor(backend=llm_backend)
        
        self.audio_recorder = AudioRecorder()
        self.is_processing = False

    def process_audio_and_inject(self, audio_data, duration: float):
        """Processes recorded audio, transcribes, polishes tone, logs to DB, and injects at cursor."""
        if audio_data is None or len(audio_data) == 0:
            print("\n⚠️ No audio detected.")
            return

        self.is_processing = True
        active_app = get_active_app_name()
        print(f"\n🎙️ Processing {duration:.1f}s of speech for [{active_app}]...")

        try:
            # 1. Transcribe with Speech-to-Text
            t0 = time.time()
            stt_result = self.stt_engine.transcribe(audio_data, language=self.current_language)
            raw_text = stt_result.get("text", "").strip()
            detected_lang = stt_result.get("language", self.current_language)
            stt_time = time.time() - t0

            if not raw_text:
                print("⚠️ No speech recognized.")
                return

            print(f"📝 Raw ({detected_lang}, {stt_time:.2f}s): {raw_text}")

            # 2. Refine tone with LLM
            t1 = time.time()
            polished_text = self.tone_processor.refine_text(
                raw_text=raw_text,
                tone=self.current_tone,
                language=detected_lang,
                target_app=active_app
            )
            llm_time = time.time() - t1
            print(f"✨ Polished [{self.current_tone}] ({llm_time:.2f}s): {polished_text}")

            # 3. Inject into active cursor
            if self.auto_paste:
                print(f"🚀 Injecting at active cursor in {active_app}...")
                success = inject_text_at_cursor(polished_text)
                if success:
                    print("✅ Injected successfully!")
                else:
                    print("⚠️ Note: Paste simulation could not reach the target app (check Accessibility permissions).")

            # 4. Save to SQLite History
            record_id = save_transcription(
                raw_text=raw_text,
                polished_text=polished_text,
                tone=self.current_tone,
                language=detected_lang,
                target_app=active_app,
                duration_seconds=duration,
                status="success"
            )
            print(f"💾 Saved to history [ID: {record_id}].")

        except Exception as e:
            logger.error(f"Error during processing: {e}", exc_info=True)
        finally:
            self.is_processing = False

    def trigger_recording_toggle(self):
        """Starts or stops recording (Toggle mode)."""
        if self.is_processing:
            print("⚠️ Still processing previous audio...")
            return

        if not self.audio_recorder.is_recording:
            print("\n🔴 RECORDING... Speak now! (Press hotkey or Enter to finish)")
            self.audio_recorder.start_recording()
        else:
            print("\n⏹️ STOPPING recording...")
            audio_data, duration = self.audio_recorder.stop_recording()
            threading.Thread(target=self.process_audio_and_inject, args=(audio_data, duration)).start()

    def start_hotkey_listener(self, hotkey_str: str = HOTKEY):
        """Starts global hotkey listener using pynput."""
        from pynput import keyboard

        print(f"\n🎯 Global hotkey active: {hotkey_str}")
        print("Switch to ANY application (Chrome, VS Code, Slack, Notes), place your cursor, and press the hotkey to speak!\n")

        def on_activate():
            self.trigger_recording_toggle()

        try:
            hotkey = keyboard.HotKey(keyboard.HotKey.parse(hotkey_str), on_activate)
            with keyboard.Listener(
                on_press=lambda k: hotkey.press(listener.canonical(k)),
                on_release=lambda k: hotkey.release(listener.canonical(k))
            ) as listener:
                listener.join()
        except Exception as e:
            print(f"⚠️ Hotkey listener notice: {e}")
            print("Note: On macOS, global hotkeys require Accessibility permissions in System Settings -> Privacy & Security -> Accessibility.")

    def select_language_interactive(self):
        """Interactive language selection menu."""
        langs = list_supported_languages()
        print("\n🌐 SELECT LANGUAGE:")
        print("-" * 40)
        for idx, lang in enumerate(langs, 1):
            is_active = "👉 (Active)" if get_language_code(self.current_language) == lang["code"] else ""
            print(f"  [{idx:2d}] {lang['name']} ({lang['code']}) {is_active}")
        print("-" * 40)
        
        try:
            choice = input(f"Enter number (1-{len(langs)}) or language code/name: ").strip()
            if not choice:
                return
            if choice.isdigit() and 1 <= int(choice) <= len(langs):
                selected = langs[int(choice) - 1]["code"]
            else:
                selected = get_language_code(choice)
            
            self.current_language = selected
            print(f"✅ Language set to: {get_language_display_name(self.current_language)} [{self.current_language}]\n")
        except Exception as e:
            print(f"Invalid input: {e}")

    def select_tone_interactive(self):
        """Interactive tone selection menu."""
        tones = self.tone_processor.list_tones()
        print("\n🎭 SELECT TONE:")
        print("-" * 40)
        for idx, t in enumerate(tones, 1):
            is_active = "👉 (Active)" if self.current_tone == t["id"] else ""
            print(f"  [{idx}] {t['name']} - {t['description']} {is_active}")
        print("-" * 40)
        
        try:
            choice = input(f"Enter number (1-{len(tones)}) or tone name: ").strip()
            if not choice:
                return
            if choice.isdigit() and 1 <= int(choice) <= len(tones):
                self.current_tone = tones[int(choice) - 1]["id"]
            else:
                self.current_tone = choice.lower()
            print(f"✅ Tone set to: [{self.current_tone}]\n")
        except Exception as e:
            print(f"Invalid input: {e}")

def show_history():
    """Prints recent transcription history."""
    records = get_history(limit=20)
    if not records:
        print("No transcriptions recorded yet.")
        return

    print("\n" + "=" * 70)
    print("📜 RECENT TRANSCRIPTION HISTORY")
    print("=" * 70)
    for rec in records:
        print(f"[{rec['timestamp']}] App: {rec['target_app']} | Lang: {rec['language']} | Tone: {rec['tone']}")
        print(f"  Raw:      {rec['raw_text']}")
        print(f"  Polished: {rec['polished_text']}")
        print("-" * 70)

def show_languages():
    """Prints all supported languages."""
    langs = list_supported_languages()
    print("\n" + "=" * 55)
    print("🌐 SUPPORTED LANGUAGES (99+ supported by Whisper)")
    print("=" * 55)
    for l in langs:
        print(f"  • {l['name']:<30} [Code: {l['code']}]")
    print("=" * 55)
    print("Use '--lang auto' for automatic language detection.\n")

def main():
    parser = argparse.ArgumentParser(description="Wispr Flow Alternative for macOS")
    parser.add_argument("--tone", default=DEFAULT_TONE, help="Tone profile (smart_verbatim, casual, professional, concise, technical)")
    parser.add_argument("--lang", default=DEFAULT_LANGUAGE, help="Language (auto, or code/name like en, tamil, hi, spanish, fr)")
    parser.add_argument("--hotkey", default=HOTKEY, help="Global hotkey combination (e.g. '<ctrl>+<space>')")
    parser.add_argument("--list-languages", action="store_true", help="List all supported languages and exit")
    parser.add_argument("--history", action="store_true", help="View transcription history")
    parser.add_argument("--clear-history", action="store_true", help="Clear all stored history")
    parser.add_argument("--no-paste", action="store_true", help="Disable automatic cursor injection (print only)")
    parser.add_argument("--cli-record", action="store_true", help="Record directly from terminal using Enter key without global hotkey")
    args = parser.parse_args()

    if args.list_languages:
        show_languages()
        return

    if args.history:
        show_history()
        return

    if args.clear_history:
        clear_history()
        print("✅ Transcription history cleared.")
        return

    normalized_lang = get_language_code(args.lang)

    app = WisprFlowAltApp(
        tone=args.tone,
        language=normalized_lang,
        auto_paste=not args.no_paste
    )

    print("\n" + "=" * 60)
    print("🎙️  WISPR FLOW ALTERNATIVE (macOS)")
    print("=" * 60)
    print(f"Selected Tone:     {app.current_tone}")
    print(f"Language Mode:     {get_language_display_name(app.current_language)} [{app.current_language}]")
    print(f"Cursor Auto-Paste: {'Enabled' if app.auto_paste else 'Disabled'}")
    print("=" * 60)

    if args.cli_record:
        print("\nCommands:")
        print("  [ENTER]      : Start / Stop recording speech")
        print("  'l' + ENTER  : Change language (Auto, Tamil, English, Hindi, etc.)")
        print("  't' + ENTER  : Change tone (Professional, Casual, Concise, etc.)")
        print("  'h' + ENTER  : View transcription history")
        print("  'q' + ENTER  : Quit\n")

        while True:
            try:
                cmd = input(f"👉 [{get_language_display_name(app.current_language)}] [{app.current_tone}] Press ENTER to speak (or l/t/h/q): ").strip().lower()
                if cmd == 'q':
                    print("Goodbye!")
                    break
                elif cmd == 'l':
                    app.select_language_interactive()
                    continue
                elif cmd == 't':
                    app.select_tone_interactive()
                    continue
                elif cmd == 'h':
                    show_history()
                    continue
                
                # Start recording
                app.trigger_recording_toggle()
                input("🔴 RECORDING... Speak now! Press [ENTER] to finish speaking...")
                app.trigger_recording_toggle()
                time.sleep(0.5)
            except KeyboardInterrupt:
                print("\nExiting.")
                break
    else:
        # Default: Global Hotkey Mode
        print(f"\n💡 Note: You can also pass '--lang auto', '--lang tamil', or '--lang hindi' at startup.")
        print("Run with '--cli-record' to change language interactively in the terminal.\n")
        app.start_hotkey_listener(args.hotkey)

if __name__ == "__main__":
    main()
