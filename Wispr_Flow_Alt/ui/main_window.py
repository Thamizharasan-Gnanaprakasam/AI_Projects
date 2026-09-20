"""
Main Application Window for Wispr Flow Alt.
Full-featured GUI for interactive dictation testing, tone tuning, and history review.
"""

import sys
import os
import time
import threading
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QTextEdit, QCheckBox, QTabWidget,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QProgressBar, QMessageBox, QApplication
)

from config import (
    DEFAULT_TONE, DEFAULT_LANGUAGE, HOTKEY, STT_BACKEND, STT_CHOICE, STT_OPTIONS,
    LLM_BACKEND, MLX_MODEL_NAME, MLX_LLM_MODEL,
    NOISE_CANCELLATION_ENABLED, DEFAULT_HOTKEY_CHOICE, HOTKEY_OPTIONS,
    GEMINI_API_KEY, GROQ_API_KEY, resolve_stt_settings, BASE_DIR, ENV_PATH,
    DEFAULT_THEME, THEME_OPTIONS
)
from core.audio_recorder import AudioRecorder
from core.stt_engine import STTEngine
from core.tone_processor import ToneProcessor
from core.text_injector import inject_text_at_cursor, get_active_app_name
from core.database import save_transcription, get_history, delete_transcription, clear_history
from core.languages import list_supported_languages, get_language_code, get_language_display_name
from ui.styles import DARK_THEME_QSS, LIGHT_THEME_QSS
from ui.floating_pill import FloatingPill

def play_system_sound(name: str):
    """Plays native system chimes for instant user confirmation."""
    try:
        if sys.platform == "darwin":
            from Cocoa import NSSound
            sound = NSSound.soundNamed_(name)
            if sound:
                sound.play()
        elif sys.platform == "win32":
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        else:
            from PyQt6.QtWidgets import QApplication
            QApplication.beep()
    except Exception:
        pass

def get_short_hotkey_badge(mode: str) -> str:
    """Returns ultra-compact hotkey representation for the floating pill."""
    mapping = {
        "fn": "Fn",
        "option_space": "⌥ Space",
        "ctrl_space": "Ctrl+Space",
        "alt_space": "Alt+Space",
        "ctrl_shift_v": "Ctrl+Shift+V",
        "f8": "F8",
        "f9": "F9",
        "cmd_shift_d": "⌘⇧D"
    }
    return mapping.get(mode, "Ctrl+Space" if sys.platform == "win32" else "Fn")

def update_env_variable(key: str, value: str):
    """Safely updates or adds a key-value pair in .env."""
    env_path = ENV_PATH
    lines = []
    found = False
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f'{key}="{value}"\n')
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f'{key}="{value}"\n')

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

class WorkerSignals(QObject):
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    audio_level = pyqtSignal(float)
    processing_started = pyqtSignal(float)
    transcription_complete = pyqtSignal(dict)
    processing_error = pyqtSignal(str)

class MainWindow(QMainWindow):
    hotkey_preference_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoiceInk")
        self.resize(980, 720)
        self.setMinimumSize(900, 650)
        self.setStyleSheet(DARK_THEME_QSS)

        # Set Application Icon
        icon_path = os.path.join(BASE_DIR, "assets", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.selected_hotkey = DEFAULT_HOTKEY_CHOICE
        self.selected_stt_choice = STT_CHOICE
        self.current_theme = DEFAULT_THEME

        # System theme listener
        app_inst = QApplication.instance()
        if app_inst and hasattr(app_inst.styleHints(), "colorSchemeChanged"):
            app_inst.styleHints().colorSchemeChanged.connect(self.on_system_theme_changed)

        # Core Engines
        initial_stt = resolve_stt_settings(self.selected_stt_choice)
        self.stt_engine = STTEngine(
            backend=initial_stt["backend"],
            model_name=initial_stt["model"],
            groq_api_key=GROQ_API_KEY,
            gemini_api_key=GEMINI_API_KEY,
        )
        self.tone_processor = ToneProcessor(
            backend=LLM_BACKEND,
            mlx_model_name=MLX_LLM_MODEL,
            gemini_api_key=GEMINI_API_KEY,
            groq_api_key=GROQ_API_KEY
        )
        self.audio_recorder = AudioRecorder()
        
        # Signals
        self.signals = WorkerSignals()
        self.signals.recording_started.connect(self.on_recording_started)
        self.signals.recording_stopped.connect(self.on_recording_stopped)
        self.signals.audio_level.connect(self.on_audio_level)
        self.signals.processing_started.connect(self.on_processing_started)
        self.signals.transcription_complete.connect(self.on_transcription_complete)
        self.signals.processing_error.connect(self.on_processing_error)

        # Floating Pill
        self.floating_pill = FloatingPill()
        if os.path.exists(icon_path):
            self.floating_pill.setWindowIcon(QIcon(icon_path))
        self.floating_pill.toggle_recording_requested.connect(self.toggle_recording)
        self.floating_pill.language_selected.connect(self.on_pill_language_selected)
        self.floating_pill.tone_selected.connect(self.on_pill_tone_selected)
        self.floating_pill.update_hotkey_label(get_short_hotkey_badge(self.selected_hotkey))

        # Level monitor timer and VAD tracking
        self._speech_detected = False
        self._silence_start_time = None
        self._recording_start_time = 0.0

        self.level_timer = QTimer(self)
        self.level_timer.setInterval(50)
        self.level_timer.timeout.connect(self.check_audio_level)

        self.init_comboboxes()
        self.init_ui()
        self.on_language_changed()
        self.on_tone_changed()
        self.load_history()

    def init_comboboxes(self):
        """Initializes preference dropdowns before UI setup."""
        # STT Engine & Model Selector
        self.stt_combo = QComboBox()
        for key, label in STT_OPTIONS.items():
            self.stt_combo.addItem(label, key)
        idx = self.stt_combo.findData(self.selected_stt_choice)
        if idx >= 0:
            self.stt_combo.setCurrentIndex(idx)
        self.stt_combo.currentIndexChanged.connect(self.on_stt_changed)

        # Language Selector
        self.lang_combo = QComboBox()
        for lang in list_supported_languages():
            self.lang_combo.addItem(f"{lang['name']} ({lang['code']})", lang['code'])
        idx = self.lang_combo.findData(DEFAULT_LANGUAGE)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self.on_language_changed)

        # Tone Selector
        self.tone_combo = QComboBox()
        for tone in self.tone_processor.list_tones():
            self.tone_combo.addItem(f"{tone['name']}", tone['id'])
        idx = self.tone_combo.findData(DEFAULT_TONE)
        if idx >= 0:
            self.tone_combo.setCurrentIndex(idx)
        self.tone_combo.currentIndexChanged.connect(self.on_tone_changed)

        # Hotkey Selector
        self.hotkey_combo = QComboBox()
        for key, label in HOTKEY_OPTIONS.items():
            self.hotkey_combo.addItem(label, key)
        idx = self.hotkey_combo.findData(self.selected_hotkey)
        if idx >= 0:
            self.hotkey_combo.setCurrentIndex(idx)
        self.hotkey_combo.currentIndexChanged.connect(self.on_hotkey_changed)

    def init_ui(self):
        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        # ----------------- Top Header Bar -----------------
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_path = os.path.join(BASE_DIR, "assets", "icon.png")
        if os.path.exists(icon_path):
            logo_label = QLabel(self)
            pix = QPixmap(icon_path).scaled(42, 42, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pix)
            logo_label.setFixedSize(42, 42)
            header_layout.addWidget(logo_label)

        title_vbox = QVBoxLayout()
        self.title_label = QLabel("VoiceInk", self)
        self.title_label.setProperty("class", "headerTitle")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFFFFF;")
        self.subtitle_label = QLabel("AI-Powered Voice Dictation • Multilingual • Contextual Tone Refining", self)
        self.subtitle_label.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_vbox.addWidget(self.title_label)
        title_vbox.addWidget(self.subtitle_label)

        header_layout.addLayout(title_vbox)
        header_layout.addStretch()

        self.pill_toggle_btn = QPushButton("Toggle Floating Pill", self)
        self.pill_toggle_btn.setProperty("class", "secondaryBtn")
        self.pill_toggle_btn.clicked.connect(self.toggle_pill_visibility)
        header_layout.addWidget(self.pill_toggle_btn)

        # Quick Theme Selector in Header
        self.header_theme_combo = QComboBox(self)
        self.header_theme_combo.addItem("🌓 System", "system")
        self.header_theme_combo.addItem("🌙 Dark", "dark")
        self.header_theme_combo.addItem("☀️ Light", "light")
        self.header_theme_combo.setToolTip("App Appearance: Follow System, Dark, or Light Mode")
        self.header_theme_combo.currentIndexChanged.connect(self.on_header_theme_changed)
        header_layout.addWidget(self.header_theme_combo)

        self.status_badge = QLabel("🟢 Ready", self)
        self.status_badge.setStyleSheet("background-color: rgba(16, 185, 129, 0.15); color: #34D399; padding: 4px 12px; border-radius: 6px; font-weight: 600;")
        header_layout.addWidget(self.status_badge)

        main_layout.addLayout(header_layout)

        # ----------------- Tabs -----------------
        self.tab_widget = QTabWidget(self)
        self.tab_widget.setElideMode(Qt.TextElideMode.ElideNone)
        
        # Tab 1: Live Dictation
        dictation_tab = QWidget()
        self.setup_dictation_tab(dictation_tab)
        self.tab_widget.addTab(dictation_tab, "🎙️ Dictation Studio")

        # Tab 2: History
        history_tab = QWidget()
        self.setup_history_tab(history_tab)
        self.tab_widget.addTab(history_tab, "📜 Transcription History")

        # Tab 3: Settings & Diagnostics
        settings_tab = QWidget()
        self.setup_settings_tab(settings_tab)
        self.tab_widget.addTab(settings_tab, "⚙️ Settings & Info")

        main_layout.addWidget(self.tab_widget)

        # Apply initial theme
        self.apply_theme(self.current_theme, save_preference=False)

    def setup_dictation_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(14)

        # Top Control Strip: Active status chips & toggles
        control_card = QFrame(parent)
        control_card.setObjectName("controlCard")
        control_layout = QHBoxLayout(control_card)
        control_layout.setContentsMargins(12, 8, 12, 8)
        control_layout.setSpacing(12)

        # Language Chip
        lang_text = self.lang_combo.currentText().split("(")[0].strip()
        self.dictation_lang_chip = QLabel(f"🌐 {lang_text}", control_card)
        self.dictation_lang_chip.setProperty("class", "prefChip")
        control_layout.addWidget(self.dictation_lang_chip)

        # Tone Chip
        tone_text = self.tone_combo.currentText().split("/")[0].strip()
        self.dictation_tone_chip = QLabel(f"🎨 {tone_text}", control_card)
        self.dictation_tone_chip.setProperty("class", "prefChip")
        control_layout.addWidget(self.dictation_tone_chip)

        # STT Model Chip
        stt_short = self.get_short_stt_label(self.selected_stt_choice)
        self.dictation_stt_chip = QLabel(f"🧠 {stt_short}", control_card)
        self.dictation_stt_chip.setProperty("class", "prefChip")
        control_layout.addWidget(self.dictation_stt_chip)

        # Settings Shortcut Button
        self.settings_shortcut_btn = QPushButton("⚙️ Settings", control_card)
        self.settings_shortcut_btn.setProperty("class", "settingsBtnSmall")
        self.settings_shortcut_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_shortcut_btn.setToolTip("Configure Language, Tone, and Global Hotkey in Settings")
        self.settings_shortcut_btn.clicked.connect(lambda: self.tab_widget.setCurrentIndex(2))
        control_layout.addWidget(self.settings_shortcut_btn)

        control_layout.addStretch()

        # Auto-paste checkbox
        self.auto_paste_cb = QCheckBox("Inject at Cursor", control_card)
        self.auto_paste_cb.setChecked(True)
        self.auto_paste_cb.setCursor(Qt.CursorShape.PointingHandCursor)

        # Noise Cancellation checkbox
        self.noise_cancel_cb = QCheckBox("🔕 Noise Cancel", control_card)
        self.noise_cancel_cb.setObjectName("noiseCancelCb")
        self.noise_cancel_cb.setChecked(NOISE_CANCELLATION_ENABLED)
        self.noise_cancel_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.noise_cancel_cb.toggled.connect(self.on_noise_cancellation_toggled)

        control_layout.addWidget(self.auto_paste_cb)
        control_layout.addSpacing(8)
        control_layout.addWidget(self.noise_cancel_cb)

        layout.addWidget(control_card)

        # Center Section: Big Record Button & Audio Level Meter
        center_card = QFrame(parent)
        center_card.setObjectName("centerCard")
        center_layout = QVBoxLayout(center_card)
        center_layout.setContentsMargins(18, 18, 18, 18)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.record_btn = QPushButton("🎙️", center_card)
        self.record_btn.setObjectName("recordBtn")
        self.record_btn.setFixedSize(84, 84)
        self.record_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.record_btn.clicked.connect(self.toggle_recording)

        self.record_instruction = QLabel(self.get_record_instruction_text(), center_card)
        self.record_instruction.setStyleSheet("font-size: 13px; font-weight: 600; color: #94A3B8; margin-top: 10px;")

        # Audio Volume Level Bar
        self.level_bar = QProgressBar(center_card)
        self.level_bar.setRange(0, 100)
        self.level_bar.setValue(0)
        self.level_bar.setTextVisible(False)
        self.level_bar.setFixedHeight(6)
        self.level_bar.setFixedWidth(280)
        self.level_bar.setStyleSheet("""
            QProgressBar {
                background-color: #242938;
                border-radius: 3px;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #6366F1);
                border-radius: 3px;
            }
        """)

        center_layout.addWidget(self.record_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self.record_instruction, alignment=Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self.level_bar, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(center_card)

        # Output Section: Dual Cards (Raw Transcription vs Polished Output)
        output_layout = QHBoxLayout()

        # Left: Raw Transcription
        raw_box = QFrame(parent)
        raw_box.setObjectName("rawBox")
        raw_vbox = QVBoxLayout(raw_box)
        raw_vbox.setContentsMargins(14, 12, 14, 12)
        raw_header = QHBoxLayout()
        self.raw_title = QLabel("📝 Raw Speech (STT)", raw_box)
        self.raw_title.setStyleSheet("font-weight: 700; color: #CBD5E1; font-size: 13px;")
        self.copy_raw_btn = QPushButton("Copy", raw_box)
        self.copy_raw_btn.setProperty("class", "secondaryBtn")
        self.copy_raw_btn.clicked.connect(lambda: self.copy_to_clipboard(self.raw_text_edit.toPlainText()))
        raw_header.addWidget(self.raw_title)
        raw_header.addStretch()
        raw_header.addWidget(self.copy_raw_btn)

        self.raw_text_edit = QTextEdit(raw_box)
        self.raw_text_edit.setPlaceholderText("Raw speech transcription will appear here...")
        self.raw_text_edit.setReadOnly(False)
        raw_vbox.addLayout(raw_header)
        raw_vbox.addWidget(self.raw_text_edit)

        # Right: Polished Output
        polished_box = QFrame(parent)
        polished_box.setObjectName("polishedBox")
        polished_vbox = QVBoxLayout(polished_box)
        polished_vbox.setContentsMargins(14, 12, 14, 12)
        polished_header = QHBoxLayout()
        self.polished_title = QLabel("✨ Polished Output", polished_box)
        self.polished_title.setStyleSheet("font-weight: 700; color: #818CF8; font-size: 13px;")
        self.copy_polished_btn = QPushButton("Copy", polished_box)
        self.copy_polished_btn.setProperty("class", "secondaryBtn")
        self.copy_polished_btn.clicked.connect(lambda: self.copy_to_clipboard(self.polished_text_edit.toPlainText()))
        polished_header.addWidget(self.polished_title)
        polished_header.addStretch()
        polished_header.addWidget(self.copy_polished_btn)

        self.polished_text_edit = QTextEdit(polished_box)
        self.polished_text_edit.setPlaceholderText("Refined text matching selected tone will appear here and inject at cursor...")
        self.polished_text_edit.setReadOnly(False)
        polished_vbox.addLayout(polished_header)
        polished_vbox.addWidget(self.polished_text_edit)

        output_layout.addWidget(raw_box)
        output_layout.addWidget(polished_box)

        layout.addLayout(output_layout)

    def setup_history_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(10)

        # History Toolbar: Search & Actions
        toolbar = QHBoxLayout()
        self.history_search = QLineEdit(parent)
        self.history_search.setPlaceholderText("🔍 Search transcription history...")
        self.history_search.textChanged.connect(self.filter_history)

        self.refresh_btn = QPushButton("Refresh", parent)
        self.refresh_btn.setProperty("class", "secondaryBtn")
        self.refresh_btn.clicked.connect(self.load_history)

        self.clear_btn = QPushButton("Clear All", parent)
        self.clear_btn.setProperty("class", "secondaryBtn")
        self.clear_btn.setStyleSheet("color: #F87171; border-color: rgba(239, 68, 68, 0.4);")
        self.clear_btn.clicked.connect(self.clear_all_history)

        toolbar.addWidget(self.history_search)
        toolbar.addWidget(self.refresh_btn)
        toolbar.addWidget(self.clear_btn)
        layout.addLayout(toolbar)

        # Table (8 Columns: Time, Target App, Lang, Tone, Raw Text, Raw in English, English Translation, Polished Text)
        self.history_table = QTableWidget(parent)
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels([
            "Time", "Target App", "Lang", "Tone",
            "Raw Text", "Raw in English", "English Translation", "Polished Text"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setColumnWidth(0, 75)   # Time
        self.history_table.setColumnWidth(1, 95)   # Target App
        self.history_table.setColumnWidth(2, 55)   # Lang
        self.history_table.setColumnWidth(3, 85)   # Tone
        self.history_table.setColumnWidth(4, 150)  # Raw Text
        self.history_table.setColumnWidth(5, 150)  # Raw in English
        self.history_table.setColumnWidth(6, 165)  # English Translation
        layout.addWidget(self.history_table)

    def setup_settings_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Card 1: Dictation Preferences
        pref_card = QFrame(parent)
        pref_card.setObjectName("prefCard")
        pref_layout = QVBoxLayout(pref_card)
        pref_layout.setContentsMargins(18, 16, 18, 16)
        pref_layout.setSpacing(14)

        pref_title = QLabel("🎙️ Dictation Preferences & STT Models", pref_card)
        pref_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #F8FAFC;")
        pref_layout.addWidget(pref_title)

        # STT Engine & Model row
        stt_row = QHBoxLayout()
        stt_lbl = QLabel("Speech-to-Text Model:", pref_card)
        stt_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #E2E8F0; min-width: 170px;")
        self.stt_combo.setStyleSheet("min-width: 360px; padding: 6px 12px;")
        stt_row.addWidget(stt_lbl)
        stt_row.addWidget(self.stt_combo)
        stt_row.addStretch()
        pref_layout.addLayout(stt_row)

        # Gemini API Key Panel
        self.gemini_key_widget = QWidget(pref_card)
        gemini_layout = QVBoxLayout(self.gemini_key_widget)
        gemini_layout.setContentsMargins(0, 2, 0, 4)
        gemini_input_row = QHBoxLayout()
        gemini_lbl = QLabel("Google Gemini API Key:", self.gemini_key_widget)
        gemini_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #A78BFA; min-width: 170px;")
        self.gemini_key_input = QLineEdit(self.gemini_key_widget)
        self.gemini_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_key_input.setText(self.stt_engine.gemini_api_key)
        self.gemini_key_input.setPlaceholderText("Paste your free Gemini key (AIzaSy...)")
        self.gemini_key_input.setStyleSheet("min-width: 260px; padding: 6px 10px;")
        self.save_gemini_key_btn = QPushButton("Save Key", self.gemini_key_widget)
        self.save_gemini_key_btn.setProperty("class", "secondaryBtn")
        self.save_gemini_key_btn.clicked.connect(self.save_gemini_key)
        gemini_input_row.addWidget(gemini_lbl)
        gemini_input_row.addWidget(self.gemini_key_input)
        gemini_input_row.addWidget(self.save_gemini_key_btn)
        gemini_input_row.addStretch()
        gemini_layout.addLayout(gemini_input_row)

        gemini_hint = QLabel("⚡ <b>100% Free:</b> Get your free API key at <a href='https://aistudio.google.com/app/apikey' style='color: #818CF8;'>aistudio.google.com/app/apikey</a> (15 RPM, 1,500 RPD free). Maximum probability for Tamil, Tanglish, and 100+ languages.", self.gemini_key_widget)
        gemini_hint.setStyleSheet("font-size: 12px; color: #94A3B8; margin-top: 2px;")
        gemini_hint.setOpenExternalLinks(True)
        gemini_layout.addWidget(gemini_hint)
        pref_layout.addWidget(self.gemini_key_widget)

        # Groq API Key Panel
        self.groq_key_widget = QWidget(pref_card)
        groq_layout = QVBoxLayout(self.groq_key_widget)
        groq_layout.setContentsMargins(0, 2, 0, 4)
        groq_input_row = QHBoxLayout()
        groq_lbl = QLabel("Groq Cloud API Key:", self.groq_key_widget)
        groq_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #38BDF8; min-width: 170px;")
        self.groq_key_input = QLineEdit(self.groq_key_widget)
        self.groq_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.groq_key_input.setText(self.stt_engine.groq_api_key)
        self.groq_key_input.setPlaceholderText("Paste your free Groq key (gsk_...)")
        self.groq_key_input.setStyleSheet("min-width: 260px; padding: 6px 10px;")
        self.save_groq_key_btn = QPushButton("Save Key", self.groq_key_widget)
        self.save_groq_key_btn.setProperty("class", "secondaryBtn")
        self.save_groq_key_btn.clicked.connect(self.save_groq_key)
        groq_input_row.addWidget(groq_lbl)
        groq_input_row.addWidget(self.groq_key_input)
        groq_input_row.addWidget(self.save_groq_key_btn)
        groq_input_row.addStretch()
        groq_layout.addLayout(groq_input_row)

        groq_hint = QLabel("⚡ <b>100% Free:</b> Get your free key at <a href='https://console.groq.com/keys' style='color: #38BDF8;'>console.groq.com/keys</a> for ultra-fast 300ms cloud Whisper Large-v3.", self.groq_key_widget)
        groq_hint.setStyleSheet("font-size: 12px; color: #94A3B8; margin-top: 2px;")
        groq_hint.setOpenExternalLinks(True)
        groq_layout.addWidget(groq_hint)
        pref_layout.addWidget(self.groq_key_widget)

        # MLX Offline Hint
        self.mlx_hint = QLabel("🔒 <b>100% On-Device & Private:</b> Runs locally on Apple Silicon Metal GPU / Neural Engine without any internet or API key.", pref_card)
        self.mlx_hint.setStyleSheet("font-size: 12px; color: #34D399; margin-top: 2px;")
        pref_layout.addWidget(self.mlx_hint)

        self.update_api_key_visibility(self.selected_stt_choice)

        # Spoken Language row
        lang_row = QHBoxLayout()
        lang_lbl = QLabel("Spoken Language:", pref_card)
        lang_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #E2E8F0; min-width: 170px;")
        self.lang_combo.setStyleSheet("min-width: 260px; padding: 6px 12px;")
        lang_row.addWidget(lang_lbl)
        lang_row.addWidget(self.lang_combo)
        lang_row.addStretch()
        pref_layout.addLayout(lang_row)

        # Refinement Tone row
        tone_row = QHBoxLayout()
        tone_lbl = QLabel("Refinement Tone:", pref_card)
        tone_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #E2E8F0; min-width: 170px;")
        self.tone_combo.setStyleSheet("min-width: 260px; padding: 6px 12px;")
        tone_row.addWidget(tone_lbl)
        tone_row.addWidget(self.tone_combo)
        tone_row.addStretch()
        pref_layout.addLayout(tone_row)

        # Global Hotkey row
        hotkey_row = QHBoxLayout()
        hotkey_lbl = QLabel("Global Dictation Hotkey:", pref_card)
        hotkey_lbl.setStyleSheet("font-size: 13px; font-weight: 600; min-width: 170px;")
        self.hotkey_combo.setStyleSheet("min-width: 320px; padding: 6px 12px;")
        hotkey_row.addWidget(hotkey_lbl)
        hotkey_row.addWidget(self.hotkey_combo)
        hotkey_row.addStretch()
        pref_layout.addLayout(hotkey_row)

        # App Theme / Appearance row
        theme_row = QHBoxLayout()
        theme_lbl = QLabel("App Appearance:", pref_card)
        theme_lbl.setStyleSheet("font-size: 13px; font-weight: 600; min-width: 170px;")
        self.settings_theme_combo = QComboBox(pref_card)
        self.settings_theme_combo.addItem("🌓 Follow System", "system")
        self.settings_theme_combo.addItem("🌙 Dark Mode", "dark")
        self.settings_theme_combo.addItem("☀️ Light Mode", "light")
        self.settings_theme_combo.setStyleSheet("min-width: 260px; padding: 6px 12px;")
        self.settings_theme_combo.currentIndexChanged.connect(self.on_settings_theme_changed)
        theme_row.addWidget(theme_lbl)
        theme_row.addWidget(self.settings_theme_combo)
        theme_row.addStretch()
        pref_layout.addLayout(theme_row)

        hotkey_desc = QLabel("💡 Press your selected hotkey anywhere across your apps (VS Code, Chrome, Notes, Slack) to start and stop dictation. Left Fn (Globe 🌐) enables rapid one-touch dictation.", pref_card)
        hotkey_desc.setStyleSheet("font-size: 12px; color: #94A3B8; margin-top: 4px;")
        hotkey_desc.setWordWrap(True)
        pref_layout.addWidget(hotkey_desc)

        layout.addWidget(pref_card)

        # Card 2: Hardware & Engine Configuration
        info_card = QFrame(parent)
        info_card.setObjectName("infoCard")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(18, 16, 18, 16)
        info_layout.setSpacing(10)

        info_title = QLabel("Hardware & Engine Configuration", info_card)
        info_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #F8FAFC;")
        info_layout.addWidget(info_title)

        self.stt_info_label = QLabel(f"• Speech-to-Text Model: <b>{self.stt_engine.model_name}</b> ({self.stt_engine.backend})", info_card)
        self.llm_info_label = QLabel(f"• Tone Refinement Model: <b>{MLX_LLM_MODEL}</b> (Local MLX-LM)", info_card)
        self.hotkey_info_label = QLabel(f"• Active Hotkey: <b>{HOTKEY_OPTIONS.get(self.selected_hotkey, self.selected_hotkey)}</b>", info_card)
        self.noise_info_label = QLabel("• Noise Cancellation: <b>Gentle Spectral</b> (80Hz Cutoff, Speech Formants Preserved)", info_card)
        self.privacy_info_label = QLabel("• Privacy & Security: <b>Zero Data Retention</b>", info_card)
        
        for lbl in (self.stt_info_label, self.llm_info_label, self.hotkey_info_label, self.noise_info_label, self.privacy_info_label):
            lbl.setStyleSheet("font-size: 13px; color: #CBD5E1;")
            info_layout.addWidget(lbl)

        layout.addWidget(info_card)
        layout.addStretch()

    def get_record_instruction_text(self) -> str:
        hotkey_display = HOTKEY_OPTIONS.get(self.selected_hotkey, "Left Fn")
        short_key = hotkey_display.split("[")[0].strip()
        return f"Click to Speak or Press {short_key}"

    # ----------------- Dictation & Recording Logic -----------------
    def toggle_recording(self):
        if self.audio_recorder.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        self._speech_detected = False
        self._silence_start_time = None
        self._recording_start_time = time.time()
        play_system_sound("Tink")

        try:
            self.audio_recorder.start_recording()
        except Exception as e:
            logger.error(f"Failed to start audio recording: {e}", exc_info=True)
            err_msg = str(e)
            if "Invalid sample rate" in err_msg or "Invalid number of channels" in err_msg or "-9997" in err_msg or "-9998" in err_msg:
                user_msg = "Microphone format unsupported. Check Windows Sound Control Panel."
            elif "-9996" in err_msg or "No audio input devices" in err_msg or "No default input device" in err_msg:
                user_msg = "No microphone found. Please connect an audio input device."
            elif "-9999" in err_msg or "Unanticipated host error" in err_msg or "access" in err_msg.lower():
                user_msg = "Microphone access denied. Check Windows Privacy > Microphone."
            else:
                user_msg = f"Microphone error: {e}"
            self.signals.processing_error.emit(user_msg)
            return

        self.signals.recording_started.emit()
        self.level_timer.start()

    def stop_recording(self):
        if not self.audio_recorder.is_recording:
            return
        self.level_timer.stop()
        self.level_bar.setValue(0)
        play_system_sound("Pop")

        try:
            audio_data, duration = self.audio_recorder.stop_recording()
        except Exception as e:
            logger.error(f"Error stopping recording: {e}", exc_info=True)
            self.signals.processing_error.emit(f"Microphone error: {e}")
            return

        self.signals.recording_stopped.emit()

        if audio_data is not None and len(audio_data) > 0:
            threading.Thread(target=self.process_audio_worker, args=(audio_data, duration), daemon=True).start()

    def check_audio_level(self):
        """Monitors microphone level for waveform animation and progress bar."""
        if not self.audio_recorder.is_recording:
            return
        if not self.audio_recorder.audio_queue.empty():
            try:
                chunk = self.audio_recorder.audio_queue.queue[-1]
                rms = float(import_np_rms(chunk))
                
                # Dynamic audio level scaling (noise floor ~0.001, normal voice ~0.008..0.035)
                if rms > 0.0012:
                    level = min(100, max(0, int((rms - 0.0012) * 3200)))
                else:
                    level = 0

                self.signals.audio_level.emit(level)
                self.floating_pill.set_audio_level(level)

                now = time.time()
                # Safety timeout (90 seconds max per dictation utterance)
                if (now - self._recording_start_time) > 90.0:
                    self.stop_recording()
                    return

            except Exception:
                pass

    def process_audio_worker(self, audio_data, duration: float):
        self.signals.processing_started.emit(duration)
        active_app = get_active_app_name()
        current_lang = self.lang_combo.currentData()
        current_tone = self.tone_combo.currentData()

        try:
            # Pre-check API key if cloud engine is selected
            if self.stt_engine.backend == "gemini" and not self.stt_engine.gemini_api_key:
                self.signals.processing_error.emit("Gemini selected, but no API key is saved. Please paste your free key in Settings & Info or switch to Local MLX Whisper.")
                return
            if self.stt_engine.backend == "groq" and not self.stt_engine.groq_api_key:
                self.signals.processing_error.emit("Groq selected, but no API key is saved. Please paste your free key in Settings & Info or switch to Local MLX Whisper.")
                return

            # 1. Transcribe with Selected STT Engine (Gemini / MLX / Groq)
            t0 = time.time()
            stt_res = self.stt_engine.transcribe(audio_data, language=current_lang)
            raw_text = stt_res.get("text", "").strip()
            detected_lang = stt_res.get("language", current_lang)
            stt_dur = time.time() - t0

            if not raw_text:
                self.signals.processing_error.emit("No speech was detected.")
                return

            # 2. Refine with Tone Processor, Transliterate, and Translate
            t1 = time.time()
            processed_res = self.tone_processor.process_utterance(
                raw_text=raw_text,
                tone=current_tone,
                language=detected_lang,
                target_app=active_app
            )
            polished_text = processed_res.get("polished_text", raw_text)
            raw_in_english = processed_res.get("raw_in_english", raw_text)
            english_translation = processed_res.get("english_translation", polished_text)
            llm_dur = time.time() - t1

            # 3. Inject at active cursor if enabled
            if self.auto_paste_cb.isChecked():
                inject_text_at_cursor(polished_text)

            # 4. Save to Database
            save_transcription(
                raw_text=raw_text,
                raw_in_english=raw_in_english,
                english_translation=english_translation,
                polished_text=polished_text,
                tone=current_tone,
                language=detected_lang,
                target_app=active_app,
                duration_seconds=duration
            )

            # Signal completion
            self.signals.transcription_complete.emit({
                "raw_text": raw_text,
                "raw_in_english": raw_in_english,
                "english_translation": english_translation,
                "polished_text": polished_text,
                "detected_lang": detected_lang,
                "target_app": active_app,
                "duration": duration,
                "stt_dur": stt_dur,
                "llm_dur": llm_dur,
            })

        except Exception as e:
            self.signals.processing_error.emit(str(e))

    # ----------------- UI Slots -----------------
    def on_stt_changed(self):
        choice = self.stt_combo.currentData()
        self.selected_stt_choice = choice
        settings = resolve_stt_settings(choice)
        self.stt_engine.backend = settings["backend"]
        self.stt_engine.model_name = settings["model"]
        
        self.update_api_key_visibility(choice)
        short_label = self.get_short_stt_label(choice)
        if hasattr(self, 'dictation_stt_chip'):
            self.dictation_stt_chip.setText(f"🧠 {short_label}")
        if hasattr(self, 'stt_info_label'):
            self.stt_info_label.setText(f"• Speech-to-Text Model: <b>{self.stt_engine.model_name}</b> ({self.stt_engine.backend})")
        
        update_env_variable("WISPR_STT_CHOICE", choice)
        update_env_variable("WISPR_STT_BACKEND", settings["backend"])
        update_env_variable("WISPR_MLX_MODEL", settings["model"])

    def update_api_key_visibility(self, choice: str):
        if hasattr(self, 'gemini_key_widget'):
            self.gemini_key_widget.setVisible(choice == "gemini")
        if hasattr(self, 'groq_key_widget'):
            self.groq_key_widget.setVisible(choice == "groq")
        if hasattr(self, 'mlx_hint'):
            self.mlx_hint.setVisible(choice in ("mlx_turbo", "mlx_full"))

    def save_gemini_key(self):
        key = self.gemini_key_input.text().strip()
        self.stt_engine.gemini_api_key = key
        self.tone_processor.gemini_api_key = key
        update_env_variable("GEMINI_API_KEY", key)
        QMessageBox.information(self, "Key Saved", "Google Gemini API key saved to .env and activated successfully!")

    def save_groq_key(self):
        key = self.groq_key_input.text().strip()
        self.stt_engine.groq_api_key = key
        self.tone_processor.groq_api_key = key
        update_env_variable("GROQ_API_KEY", key)
        QMessageBox.information(self, "Key Saved", "Groq API key saved to .env and activated successfully!")

    @staticmethod
    def get_short_stt_label(choice: str) -> str:
        if choice == "gemini":
            return "STT: Gemini Flash"
        elif choice == "groq":
            return "STT: Groq Large-v3"
        elif choice == "mlx_full":
            return "STT: MLX Large-v3 Full"
        else:
            return "STT: MLX Large-v3 Turbo"

    def on_recording_started(self):
        self.status_badge.setText("🔴 Recording...")
        self.status_badge.setStyleSheet("background-color: rgba(239, 68, 68, 0.2); color: #F87171; padding: 4px 12px; border-radius: 6px; font-weight: bold;")
        self.record_btn.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #EF4444, stop:1 #DC2626); border: 3px solid rgba(248, 113, 113, 0.7);")
        self.record_instruction.setText("Listening... Speak naturally (Click to finish)")
        self.floating_pill.set_recording_state(True)

    def on_recording_stopped(self):
        self.status_badge.setText("⚡ Processing...")
        self.status_badge.setStyleSheet("background-color: rgba(99, 102, 241, 0.2); color: #818CF8; padding: 4px 12px; border-radius: 6px; font-weight: 600;")
        self.record_btn.setStyleSheet("")
        self.floating_pill.set_processing_state()

    def on_audio_level(self, level: float):
        self.level_bar.setValue(int(level))

    def on_processing_started(self, duration: float):
        self.record_instruction.setText(f"Polishing {duration:.1f}s of audio...")

    def on_transcription_complete(self, data: dict):
        self.raw_text_edit.setPlainText(data["raw_text"])
        self.polished_text_edit.setPlainText(data["polished_text"])
        self.raw_title.setText(f"📝 Raw Speech ({data['detected_lang']}, {data['stt_dur']:.2f}s)")
        self.polished_title.setText(f"✨ Polished Output ({data['llm_dur']:.2f}s)")

        self.status_badge.setText("🟢 Ready")
        self.status_badge.setStyleSheet("background-color: rgba(16, 185, 129, 0.15); color: #34D399; padding: 4px 12px; border-radius: 6px; font-weight: 600;")
        self.record_instruction.setText(self.get_record_instruction_text())
        self.floating_pill.set_success_state(f"Injected in {data['target_app']}")
        self.load_history()

    def on_processing_error(self, err_msg: str):
        self.level_timer.stop()
        self.level_bar.setValue(0)
        self.record_btn.setStyleSheet("")
        self.status_badge.setText("⚠️ Error")
        self.status_badge.setStyleSheet("background-color: rgba(239, 68, 68, 0.2); color: #F87171; padding: 4px 12px; border-radius: 6px; font-weight: 600;")
        self.record_instruction.setText(f"{err_msg}")
        self.floating_pill.set_recording_state(False)

    def on_language_changed(self):
        lang_code = self.lang_combo.currentData()
        display_name = get_language_display_name(lang_code)
        short_lang = self.lang_combo.currentText().split("(")[0].strip()
        if hasattr(self, 'dictation_lang_chip'):
            self.dictation_lang_chip.setText(f"🌐 Language: {short_lang}")
        self.floating_pill.current_lang_code = lang_code
        self.floating_pill.update_badges(display_name, self.tone_combo.currentText())
        update_env_variable("WISPR_LANGUAGE", lang_code)

    def on_tone_changed(self):
        tone_name = self.tone_combo.currentText()
        tone_id = self.tone_combo.currentData()
        short_tone = tone_name.split("/")[0].strip()
        if hasattr(self, 'dictation_tone_chip'):
            self.dictation_tone_chip.setText(f"🎨 Tone: {short_tone}")
        self.floating_pill.current_tone_id = tone_id
        self.floating_pill.update_badges(self.lang_combo.currentText(), tone_name)
        update_env_variable("WISPR_TONE", tone_id)

    def on_pill_language_selected(self, lang_code: str):
        idx = self.lang_combo.findData(lang_code)
        if idx >= 0:
            self.lang_combo.blockSignals(True)
            self.lang_combo.setCurrentIndex(idx)
            self.lang_combo.blockSignals(False)
        update_env_variable("WISPR_LANGUAGE", lang_code)
        display_name = get_language_display_name(lang_code)
        if hasattr(self, 'dictation_lang_chip'):
            self.dictation_lang_chip.setText(f"🌐 Language: {display_name}")

    def on_pill_tone_selected(self, tone_id: str):
        idx = self.tone_combo.findData(tone_id)
        if idx >= 0:
            self.tone_combo.blockSignals(True)
            self.tone_combo.setCurrentIndex(idx)
            self.tone_combo.blockSignals(False)
        update_env_variable("WISPR_TONE", tone_id)
        tone_name = self.tone_combo.currentText()
        short_tone = tone_name.split("/")[0].strip()
        if hasattr(self, 'dictation_tone_chip'):
            self.dictation_tone_chip.setText(f"🎨 Tone: {short_tone}")

    def on_hotkey_changed(self):
        self.selected_hotkey = self.hotkey_combo.currentData()
        self.record_instruction.setText(self.get_record_instruction_text())
        hotkey_display = HOTKEY_OPTIONS.get(self.selected_hotkey, "Fn Key")
        self.floating_pill.update_hotkey_label(get_short_hotkey_badge(self.selected_hotkey))
        if hasattr(self, 'hotkey_info_label'):
            self.hotkey_info_label.setText(f"• Active Hotkey: <b>{hotkey_display}</b>")
        self.hotkey_preference_changed.emit(self.selected_hotkey)

    def toggle_pill_visibility(self):
        if self.floating_pill.isVisible():
            self.floating_pill.hide()
            self.pill_toggle_btn.setText("Show Floating Pill")
        else:
            self.floating_pill.show()
            self.pill_toggle_btn.setText("Hide Floating Pill")

    def on_noise_cancellation_toggled(self, checked: bool):
        self.audio_recorder.set_noise_cancellation(checked)
        update_env_variable("WISPR_NOISE_CANCELLATION", "true" if checked else "false")

    # ----------------- Appearance / Theme Logic -----------------
    def apply_theme(self, theme_mode: str, save_preference: bool = True):
        """Applies dark, light, or dynamic macOS system appearance."""
        if theme_mode == "system":
            app_inst = QApplication.instance()
            is_dark = (app_inst.styleHints().colorScheme() == Qt.ColorScheme.Dark) if app_inst else True
        elif theme_mode == "dark":
            is_dark = True
        else:
            is_dark = False

        self.setStyleSheet(DARK_THEME_QSS if is_dark else LIGHT_THEME_QSS)

        if hasattr(self, "title_label"):
            self.title_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {'#FFFFFF' if is_dark else '#0F172A'};")
        if hasattr(self, "subtitle_label"):
            self.subtitle_label.setStyleSheet(f"font-size: 12px; color: {'#94A3B8' if is_dark else '#64748B'};")

        if hasattr(self, "floating_pill"):
            self.floating_pill.set_theme(not is_dark)

        idx = {"system": 0, "dark": 1, "light": 2}.get(theme_mode, 0)
        if hasattr(self, "header_theme_combo"):
            self.header_theme_combo.blockSignals(True)
            self.header_theme_combo.setCurrentIndex(idx)
            self.header_theme_combo.blockSignals(False)

        if hasattr(self, "settings_theme_combo"):
            self.settings_theme_combo.blockSignals(True)
            self.settings_theme_combo.setCurrentIndex(idx)
            self.settings_theme_combo.blockSignals(False)

        if save_preference:
            self.current_theme = theme_mode
            update_env_variable("WISPR_THEME", theme_mode)

    def on_header_theme_changed(self, index: int):
        mode = self.header_theme_combo.itemData(index)
        if mode:
            self.apply_theme(mode, save_preference=True)

    def on_settings_theme_changed(self, index: int):
        mode = self.settings_theme_combo.itemData(index)
        if mode:
            self.apply_theme(mode, save_preference=True)

    def on_system_theme_changed(self):
        if self.current_theme == "system":
            self.apply_theme("system", save_preference=False)

    def copy_to_clipboard(self, text: str):
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)

    # ----------------- History Logic -----------------
    def load_history(self, search: Optional[str] = None):
        records = get_history(limit=50, search=search)
        self.history_table.setRowCount(len(records))
        for row_idx, r in enumerate(records):
            time_str = r['timestamp'].split("T")[-1][:8] if "T" in r['timestamp'] else r['timestamp']
            
            item_time = QTableWidgetItem(time_str)
            item_app = QTableWidgetItem(r.get('target_app') or 'App')
            item_lang = QTableWidgetItem(r.get('language') or 'auto')
            item_tone = QTableWidgetItem(r.get('tone') or '')
            
            raw_text = r.get('raw_text') or ''
            raw_in_en = r.get('raw_in_english') or raw_text
            eng_trans = r.get('english_translation') or r.get('polished_text') or ''
            pol_text = r.get('polished_text') or ''

            item_raw = QTableWidgetItem(raw_text)
            item_raw.setToolTip(raw_text)

            item_raw_en = QTableWidgetItem(raw_in_en)
            item_raw_en.setToolTip(raw_in_en)

            item_trans = QTableWidgetItem(eng_trans)
            item_trans.setToolTip(eng_trans)

            item_pol = QTableWidgetItem(pol_text)
            item_pol.setToolTip(pol_text)

            self.history_table.setItem(row_idx, 0, item_time)
            self.history_table.setItem(row_idx, 1, item_app)
            self.history_table.setItem(row_idx, 2, item_lang)
            self.history_table.setItem(row_idx, 3, item_tone)
            self.history_table.setItem(row_idx, 4, item_raw)
            self.history_table.setItem(row_idx, 5, item_raw_en)
            self.history_table.setItem(row_idx, 6, item_trans)
            self.history_table.setItem(row_idx, 7, item_pol)

    def filter_history(self, query: str):
        self.load_history(search=query.strip() or None)

    def clear_all_history(self):
        reply = QMessageBox.question(self, "Clear History", "Are you sure you want to delete all transcription history?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            clear_history()
            self.load_history()

def import_np_rms(chunk) -> float:
    import numpy as np
    return float(np.sqrt(np.mean(chunk**2)))
