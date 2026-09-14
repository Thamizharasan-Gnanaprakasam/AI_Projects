"""
Automated test for GUI initialization.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication

class TestWisprGUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create offscreen QApplication for headless testing
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_main_window_init(self):
        from ui.main_window import MainWindow
        window = MainWindow()
        self.assertIsNotNone(window)
        self.assertEqual(window.windowTitle(), "VoiceInk")
        
        # Verify floating pill
        self.assertIsNotNone(window.floating_pill)
        
        # Verify dropdowns populated
        self.assertTrue(window.lang_combo.count() > 10)
        self.assertTrue(window.tone_combo.count() >= 5)
        self.assertTrue(window.hotkey_combo.count() >= 4)
        self.assertTrue(window.stt_combo.count() >= 4)

        # Verify Dictation Studio chips
        self.assertTrue(len(window.dictation_lang_chip.text()) > 0)
        self.assertTrue(len(window.dictation_tone_chip.text()) > 0)
        self.assertIn("STT", window.dictation_stt_chip.text())

        # Verify dynamic update on STT change
        gemini_idx = window.stt_combo.findData("gemini")
        window.stt_combo.setCurrentIndex(gemini_idx)
        self.assertEqual(window.selected_stt_choice, "gemini")
        self.assertEqual(window.stt_engine.backend, "gemini")
        self.assertIn("Gemini", window.dictation_stt_chip.text())
        self.assertFalse(window.gemini_key_widget.isHidden())
        self.assertTrue(window.groq_key_widget.isHidden())
        self.assertTrue(window.mlx_hint.isHidden())

        # Verify Left Fn is default hotkey
        self.assertEqual(window.selected_hotkey, "fn")
        self.assertIn("Fn", window.floating_pill.status_label.text())

        # Verify dynamic update on hotkey change
        idx = window.hotkey_combo.findData("option_space")
        window.hotkey_combo.setCurrentIndex(idx)
        self.assertEqual(window.selected_hotkey, "option_space")
        self.assertIn("⌥ Space", window.floating_pill.status_label.text())

        # Verify 8 columns in History table
        self.assertEqual(window.history_table.columnCount(), 8)
        expected_headers = [
            "Time", "Target App", "Lang", "Tone",
            "Raw Text", "Raw in English", "English Translation", "Polished Text"
        ]
        for col_idx, expected in enumerate(expected_headers):
            self.assertEqual(window.history_table.horizontalHeaderItem(col_idx).text(), expected)

if __name__ == "__main__":
    unittest.main()
