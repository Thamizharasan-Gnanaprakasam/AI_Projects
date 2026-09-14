"""
Floating Pill Widget for Wispr Flow Alt.
A sleek, true capsule / stadium-shaped, draggable, always-on-top pill overlay with:
1. Authentic rounded pill geometry (semicircular ends, 335x40px).
2. Permanent on-top visibility across all macOS apps and Spaces.
3. Decoupled from minimized parent app (clicking pill never unminimizes parent).
4. Real-time animated 5-bar sound equalizer reacting to voice volume.
5. Quick-switch dropdown menus for Language and Tone directly on the pill.
"""

import math
import random
from PyQt6.QtCore import (
    Qt, QPoint, QRectF, QTimer, pyqtSignal,
    QPropertyAnimation, QEasingCurve, QEvent
)
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QMenu
)
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QAction, QCursor

from ui.styles import FLOATING_PILL_QSS
from core.languages import list_supported_languages


class WaveformVisualizer(QWidget):
    """
    Mini 5-bar reactive audio equalizer widget.
    Animates in real-time when the user speaks, pulses when processing, and stays sleek when idle.
    """
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(38, 20)
        self.num_bars = 5
        self.bar_heights = [3.5] * self.num_bars
        self.target_heights = [3.5] * self.num_bars
        self.state = "idle"  # "idle", "recording", "processing", "success"
        self._anim_phase = 0.0

        # 30 FPS smooth physics interpolation timer
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(33)
        self.anim_timer.timeout.connect(self._animate_step)
        self.anim_timer.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()

    def set_state(self, state: str):
        self.state = state
        if state == "idle":
            self.target_heights = [3.5] * self.num_bars
        elif state == "success":
            self.target_heights = [12.0, 14.0, 16.0, 14.0, 12.0]
        self.update()

    def set_audio_level(self, level: float):
        """Called with RMS volume level 0..100 while user is speaking."""
        if self.state != "recording":
            return
        
        # Responsive scaling: level is 0..100
        norm = min(1.0, max(0.0, level / 28.0))
        weights = [0.75, 1.2, 1.5, 1.15, 0.8]
        
        for i in range(self.num_bars):
            jitter = random.uniform(0.85, 1.2) if norm > 0.05 else 1.0
            h = 3.5 + norm * 12.5 * weights[i] * jitter
            self.target_heights[i] = min(16.0, max(3.5, h))

    def _animate_step(self):
        self._anim_phase += 0.20
        
        if self.state == "processing":
            # Undulating sine wave animation
            for i in range(self.num_bars):
                wave = math.sin(self._anim_phase + i * 0.9)
                self.bar_heights[i] = 4.0 + (wave + 1.0) * 4.5
            self.update()
            return

        # Natural breathing animation when recording (even during pauses)
        if self.state == "recording":
            for i in range(self.num_bars):
                breath = 4.0 + math.sin(self._anim_phase * 1.8 + i * 1.1) * 1.8
                self.target_heights[i] = max(breath, self.target_heights[i] * 0.82)

        # Smooth exponential decay / lerp towards target heights
        changed = False
        lerp_speed = 0.65 if self.state == "recording" else 0.25
        for i in range(self.num_bars):
            diff = self.target_heights[i] - self.bar_heights[i]
            if abs(diff) > 0.1:
                self.bar_heights[i] += diff * lerp_speed
                changed = True
            else:
                self.bar_heights[i] = self.target_heights[i]

        if changed or self.state == "recording":
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bar_width = 3.5
        spacing = 3.5
        total_width = self.num_bars * bar_width + (self.num_bars - 1) * spacing
        start_x = (self.width() - total_width) / 2.0
        center_y = self.height() / 2.0

        for i in range(self.num_bars):
            h = max(3.5, min(16.0, self.bar_heights[i]))
            x = start_x + i * (bar_width + spacing)
            y = center_y - (h / 2.0)
            rect = QRectF(x, y, bar_width, h)

            if self.state == "recording":
                # Vibrant warm voice wave gradient
                color = QColor(244, 63, 94) if (i % 2 == 0) else QColor(239, 68, 68)
            elif self.state == "processing":
                # Electric indigo/cyan
                color = QColor(129, 140, 248)
            elif self.state == "success":
                # Emerald confirmation
                color = QColor(52, 211, 153)
            else:
                # Dormant sleek indigo
                color = QColor(99, 102, 241, 140)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(rect, 1.75, 1.75)


class FloatingPill(QWidget):
    """
    Ultra-compact Wispr Flow true capsule pill.
    Always on top, never hides on app switch, decoupled from minimized parent window.
    """
    toggle_recording_requested = pyqtSignal()
    language_selected = pyqtSignal(str)   # emits lang_code
    tone_selected = pyqtSignal(str)       # emits tone_id

    def __init__(self, parent=None):
        super().__init__(parent=None)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._drag_start = QPoint()
        self._window_pos = QPoint()
        self._is_dragging = False
        self.is_recording = False
        self._is_processing = False
        self.hotkey_label = "Fn"
        self.current_lang_code = "auto"
        self.current_tone_id = "smart_verbatim"
        self.is_light_mode = False
        self._opacity_anim = None
        self.setWindowOpacity(0.35)

        self.init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self._configure_macos_window()

    def _configure_macos_window(self):
        """
        Configures native Cocoa NSPanel properties:
        1. setHidesOnDeactivate(False): Keeps pill permanently visible when switching apps.
        2. styleMask |= 128 (NSWindowStyleMaskNonactivatingPanel): Clicking pill never restores/unminimizes MainWindow.
        3. setLevel(NSPopUpMenuWindowLevel): Always stays on top above all other application windows.
        4. setCollectionBehavior(CanJoinAllSpaces | Stationary): Stays visible across virtual desktops and Mission Control.
        """
        try:
            import objc
            from Cocoa import NSPopUpMenuWindowLevel
            nswin = objc.objc_object(c_void_p=int(self.winId())).window()
            nswin.setHidesOnDeactivate_(False)
            nswin.setLevel_(NSPopUpMenuWindowLevel)
            # 1: NSWindowCollectionBehaviorCanJoinAllSpaces, 16: Stationary, 64: IgnoresCycle
            nswin.setCollectionBehavior_(1 | 16 | 64)
            # 128: NSWindowStyleMaskNonactivatingPanel
            mask = nswin.styleMask()
            nswin.setStyleMask_(mask | 128)
            # Enable free dragging by clicking anywhere on window background
            nswin.setMovableByWindowBackground_(True)
        except Exception:
            pass

    def init_ui(self):
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setStyleSheet(FLOATING_PILL_QSS)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 12, 4)
        layout.setSpacing(8)

        # 0. Tactile Drag Grip Indicator
        self.grip_label = QLabel("⠿", self)
        self.grip_label.setObjectName("pillGrip")
        self.grip_label.setCursor(Qt.CursorShape.OpenHandCursor)
        self.grip_label.setToolTip("Click & drag to freely move the pill anywhere")
        self.grip_label.setStyleSheet("color: rgba(255, 255, 255, 0.45); font-size: 13px; padding-left: 2px;")
        self.grip_label.installEventFilter(self)

        # 1. Clickable Mic Icon Button
        self.mic_btn = QPushButton("🎙️", self)
        self.mic_btn.setObjectName("pillMicBtn")
        self.mic_btn.setFixedSize(24, 24)
        self.mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_btn.clicked.connect(self.toggle_recording_requested.emit)

        # 2. Animated Sound Wave Visualizer
        self.waveform = WaveformVisualizer(self)
        self.waveform.setCursor(Qt.CursorShape.OpenHandCursor)
        self.waveform.installEventFilter(self)

        # 3. Compact Status Text
        self.status_label = QLabel(self.hotkey_label, self)
        self.status_label.setObjectName("pillStatus")
        self.status_label.setCursor(Qt.CursorShape.OpenHandCursor)
        self.status_label.installEventFilter(self)

        # 4. Interactive Language Chip Button
        self.lang_btn = QPushButton("Auto ▾", self)
        self.lang_btn.setObjectName("pillLangBtn")
        self.lang_btn.setFixedHeight(22)
        self.lang_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_btn.setToolTip("Click to quickly change dictation language")
        self.lang_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(99, 102, 241, 0.22);
                color: #C7D2FE;
                border: 1px solid rgba(99, 102, 241, 0.45);
                border-radius: 11px;
                padding: 0px 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 0.42);
                border: 1px solid rgba(129, 140, 248, 0.75);
                color: #FFFFFF;
            }
        """)
        self.lang_btn.clicked.connect(self.show_language_menu)

        # 5. Interactive Tone Chip Button
        self.tone_btn = QPushButton("Verbatim ▾", self)
        self.tone_btn.setObjectName("pillToneBtn")
        self.tone_btn.setFixedHeight(22)
        self.tone_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tone_btn.setToolTip("Click to quickly change AI tone refinement")
        self.tone_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(16, 185, 129, 0.18);
                color: #6EE7B7;
                border: 1px solid rgba(16, 185, 129, 0.40);
                border-radius: 11px;
                padding: 0px 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(16, 185, 129, 0.38);
                border: 1px solid rgba(52, 211, 153, 0.75);
                color: #FFFFFF;
            }
        """)
        self.tone_btn.clicked.connect(self.show_tone_menu)

        layout.addWidget(self.grip_label)
        layout.addWidget(self.mic_btn)
        layout.addWidget(self.waveform)
        layout.addWidget(self.status_label)
        layout.addWidget(self.lang_btn)
        layout.addWidget(self.tone_btn)

        self.setFixedSize(350, 42)

    def paintEvent(self, event):
        """Paints an authentic rounded pill (stadium shape) with subpixel antialiasing."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = QRectF(1.0, 1.0, self.width() - 2.0, self.height() - 2.0)
        radius = (self.height() - 2.0) / 2.0  # Perfect semicircular pill ends

        if self.is_recording:
            # Active recording crimson glow
            painter.setBrush(QBrush(QColor(36, 16, 24, 245)))
            painter.setPen(QPen(QColor(239, 68, 68, 200), 1.5))
        elif self._is_processing:
            # Polishing electric indigo glow
            painter.setBrush(QBrush(QColor(22, 24, 44, 245)))
            painter.setPen(QPen(QColor(129, 140, 248, 180), 1.4))
        else:
            if getattr(self, "is_light_mode", False):
                # Sleek frosted light glass
                painter.setBrush(QBrush(QColor(255, 255, 255, 245)))
                painter.setPen(QPen(QColor(0, 0, 0, 40), 1.2))
            else:
                # Sleek dark frosted glass
                painter.setBrush(QBrush(QColor(16, 21, 35, 245)))
                painter.setPen(QPen(QColor(255, 255, 255, 45), 1.2))

        painter.drawRoundedRect(rect, radius, radius)

    # ----------------- Interactive Menus -----------------
    def show_language_menu(self):
        """Displays a sleek dark popup menu listing all supported languages."""
        menu = QMenu(None)
        menu.setObjectName("pillDropdown")
        menu.setStyleSheet(FLOATING_PILL_QSS)

        quick_langs = [
            ("auto", "🌐 Auto-Detect"),
            ("ta", "🇮🇳 Tamil (தமிழ்)"),
            ("en", "🇬🇧 English"),
            ("hi", "🇮🇳 Hindi (हिन्दी)"),
            ("es", "🇪🇸 Spanish"),
            ("fr", "🇫🇷 French"),
            ("de", "🇩🇪 German"),
            ("ja", "🇯🇵 Japanese"),
            ("zh", "🇨🇳 Chinese"),
        ]

        for code, label in quick_langs:
            action = QAction(label, menu)
            if code == self.current_lang_code:
                action.setText(f"✓ {label}")
            action.triggered.connect(lambda checked, c=code, l=label: self._select_language(c, l))
            menu.addAction(action)

        menu.addSeparator()

        more_menu = menu.addMenu("More Languages...")
        more_menu.setObjectName("pillDropdown")
        more_menu.setStyleSheet(FLOATING_PILL_QSS)
        all_langs = list_supported_languages()
        for l_item in all_langs:
            code = l_item["code"]
            name = l_item["name"]
            act = QAction(f"{name} ({code})", more_menu)
            if code == self.current_lang_code:
                act.setText(f"✓ {name} ({code})")
            act.triggered.connect(lambda checked, c=code, n=name: self._select_language(c, n))
            more_menu.addAction(act)

        # Map button position to screen global position
        pos = self.lang_btn.mapToGlobal(QPoint(0, self.lang_btn.height() + 4))
        menu.exec(pos)

    def _select_language(self, code: str, label: str):
        self.current_lang_code = code
        clean_name = label.replace("✓", "").strip()
        short = clean_name.split("(")[0].replace("🇮🇳", "").replace("🇬🇧", "").replace("🌐", "").replace("🇪🇸", "").replace("🇫🇷", "").replace("🇩🇪", "").replace("🇯🇵", "").replace("🇨🇳", "").strip()
        self.lang_btn.setText(f"{short} ▾")
        self.language_selected.emit(code)

    def show_tone_menu(self):
        """Displays a sleek popup menu listing available AI refinement tones."""
        menu = QMenu(None)
        menu.setObjectName("pillDropdown")
        menu.setStyleSheet(FLOATING_PILL_QSS)

        tones = [
            ("smart_verbatim", "🎯 Smart Verbatim", "Cleans filler words while preserving exact meaning"),
            ("casual", "💬 Casual", "Relaxed, natural, conversational"),
            ("professional", "👔 Professional", "Executive, polished, email & doc ready"),
            ("concise", "⚡ Concise", "Bullet points and tight brevity"),
            ("technical", "💻 Technical", "Precise code & engineering terms"),
        ]

        for tid, tname, desc in tones:
            action = QAction(tname, menu)
            if tid == self.current_tone_id:
                action.setText(f"✓ {tname}")
            action.setToolTip(desc)
            action.triggered.connect(lambda checked, t=tid, n=tname: self._select_tone(t, n))
            menu.addAction(action)

        pos = self.tone_btn.mapToGlobal(QPoint(0, self.tone_btn.height() + 4))
        menu.exec(pos)

    def _select_tone(self, tone_id: str, label: str):
        self.current_tone_id = tone_id
        clean = label.replace("✓", "").replace("🎯", "").replace("💬", "").replace("👔", "").replace("⚡", "").replace("💻", "").strip()
        short = clean.split()[0]
        self.tone_btn.setText(f"{short} ▾")
        self.tone_selected.emit(tone_id)

    # ----------------- Visual States & Animation -----------------
    def set_audio_level(self, level: float):
        """Streams real-time microphone volume to waveform visualizer."""
        self.waveform.set_audio_level(level)

    def set_recording_state(self, recording: bool):
        self.is_recording = recording
        self._is_processing = False
        if recording:
            self._fade_to_opacity(1.0)
            self.mic_btn.setText("🔴")
            self.waveform.set_state("recording")
            self.status_label.setText("Listening...")
            self.status_label.setStyleSheet("color: #F87171; font-weight: 700;")
        else:
            self.mic_btn.setText("🎙️")
            self.waveform.set_state("idle")
            self.status_label.setText(self.hotkey_label)
            status_color = "#0F172A" if getattr(self, "is_light_mode", False) else "#F1F5F9"
            self.status_label.setStyleSheet(f"color: {status_color}; font-weight: 600;")
            pos = self.mapFromGlobal(QCursor.pos())
            if not self.rect().contains(pos):
                self._fade_to_opacity(0.35)
        self.update()

    def set_theme(self, is_light: bool):
        """Switches floating pill styling between dark frosted and light frosted glass."""
        self.is_light_mode = is_light
        if is_light:
            if hasattr(self, "grip_label"):
                self.grip_label.setStyleSheet("color: rgba(0, 0, 0, 0.35); font-size: 13px; padding-left: 2px;")
            if not self.is_recording and not self._is_processing:
                self.status_label.setStyleSheet("color: #0F172A; font-weight: 600;")
            self.lang_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(99, 102, 241, 0.12);
                    color: #4338CA;
                    border: 1px solid rgba(99, 102, 241, 0.35);
                    border-radius: 11px;
                    padding: 0px 8px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(99, 102, 241, 0.25);
                    border: 1px solid rgba(79, 70, 229, 0.65);
                    color: #312E81;
                }
            """)
            self.tone_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(16, 185, 129, 0.12);
                    color: #047857;
                    border: 1px solid rgba(16, 185, 129, 0.35);
                    border-radius: 11px;
                    padding: 0px 8px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(16, 185, 129, 0.25);
                    border: 1px solid rgba(5, 150, 105, 0.65);
                    color: #064E3B;
                }
            """)
        else:
            if not self.is_recording and not self._is_processing:
                self.status_label.setStyleSheet("color: #F1F5F9; font-weight: 600;")
            self.lang_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(99, 102, 241, 0.22);
                    color: #C7D2FE;
                    border: 1px solid rgba(99, 102, 241, 0.45);
                    border-radius: 11px;
                    padding: 0px 8px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(99, 102, 241, 0.42);
                    border: 1px solid rgba(129, 140, 248, 0.75);
                    color: #FFFFFF;
                }
            """)
            self.tone_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(16, 185, 129, 0.18);
                    color: #6EE7B7;
                    border: 1px solid rgba(16, 185, 129, 0.40);
                    border-radius: 11px;
                    padding: 0px 8px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(16, 185, 129, 0.38);
                    border: 1px solid rgba(52, 211, 153, 0.75);
                    color: #FFFFFF;
                }
            """)
        self.update()

    def set_processing_state(self):
        self.is_recording = False
        self._is_processing = True
        self._fade_to_opacity(1.0)
        self.mic_btn.setText("⚡")
        self.waveform.set_state("processing")
        self.status_label.setText("Polishing...")
        self.status_label.setStyleSheet("color: #818CF8; font-weight: 600;")
        self.update()

    def set_success_state(self, message: str = "Done"):
        self.is_recording = False
        self._is_processing = False
        self.mic_btn.setText("✅")
        self.waveform.set_state("success")
        short_msg = "Injected!" if "Injected" in message else "Done"
        self.status_label.setText(short_msg)
        self.status_label.setStyleSheet("color: #34D399; font-weight: 600;")
        self.update()

        def _restore_idle():
            self.set_recording_state(False)
            pos = self.mapFromGlobal(QCursor.pos())
            if not self.rect().contains(pos):
                self._fade_to_opacity(0.35)

        QTimer.singleShot(2000, _restore_idle)

    def update_hotkey_label(self, hotkey_label: str):
        self.hotkey_label = hotkey_label
        if not self.is_recording and not self._is_processing:
            self.status_label.setText(self.hotkey_label)

    def update_badges(self, language_name: str, tone_name: str):
        clean_lang = language_name.split("(")[0].strip() if "(" in language_name else language_name
        self.lang_btn.setText(f"{clean_lang} ▾")
        
        clean_tone = tone_name.split("/")[0].replace("Smart", "").strip() if "/" in tone_name else tone_name.replace("Smart", "").strip()
        short_tone = clean_tone.split()[0] if clean_tone else "Tone"
        self.tone_btn.setText(f"{short_tone} ▾")

    # ----------------- Hover Transparency & Transitions -----------------
    def _fade_to_opacity(self, target: float):
        """Smoothly animates window opacity between transparent idle and full hover visibility."""
        if not hasattr(self, "_opacity_anim") or self._opacity_anim is None:
            self._opacity_anim = QPropertyAnimation(self, b"windowOpacity")
            self._opacity_anim.setDuration(180)
            self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._opacity_anim.stop()
        self._opacity_anim.setStartValue(self.windowOpacity())
        self._opacity_anim.setEndValue(target)
        self._opacity_anim.start()

    def enterEvent(self, event):
        """Elevates pill to 100% crisp visibility on mouse hover."""
        super().enterEvent(event)
        self._fade_to_opacity(1.0)

    def leaveEvent(self, event):
        """Fades pill to subtle transparent glass when mouse leaves, unless active."""
        super().leaveEvent(event)
        pos = self.mapFromGlobal(QCursor.pos())
        if not self.rect().contains(pos):
            if not self.is_recording and not self._is_processing:
                self._fade_to_opacity(0.35)

    # ----------------- Drag Mechanics & Event Filtering -----------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint()
            self._window_pos = self.frameGeometry().topLeft()
            self._is_dragging = True
            self._has_dragged = False
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._is_dragging:
            curr = event.globalPosition().toPoint()
            delta = curr - self._drag_start
            if delta.manhattanLength() > 2:
                self._has_dragged = True
            self.move(self._window_pos + delta)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()

    def eventFilter(self, obj, event):
        """Allows dragging from status label, waveform, or grip while keeping click-to-record intact."""
        if obj in (self.status_label, self.waveform, getattr(self, "grip_label", None)):
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._drag_start = event.globalPosition().toPoint()
                    self._window_pos = self.frameGeometry().topLeft()
                    self._is_dragging = True
                    self._has_dragged = False
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)
                    return True
            elif event.type() == QEvent.Type.MouseMove:
                if self._is_dragging and (event.buttons() & Qt.MouseButton.LeftButton):
                    curr = event.globalPosition().toPoint()
                    delta = curr - self._drag_start
                    if delta.manhattanLength() > 2:
                        self._has_dragged = True
                    self.move(self._window_pos + delta)
                    return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if self._is_dragging:
                    self._is_dragging = False
                    self.setCursor(Qt.CursorShape.OpenHandCursor)
                    if not getattr(self, "_has_dragged", False) and obj != getattr(self, "grip_label", None):
                        self.toggle_recording_requested.emit()
                    return True
        return super().eventFilter(obj, event)
