"""
GUI Entry Point for VoiceInk (macOS & Windows).
Runs the desktop application with floating overlay pill at top of screen, cross-platform global hotkeys, and glass UI.
"""

import sys
import os
import time
import threading
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QIcon

from config import DEFAULT_HOTKEY_CHOICE, BASE_DIR
from ui.main_window import MainWindow

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VoiceInkGUI")

class HotkeyManager(QObject):
    hotkey_triggered = pyqtSignal()

    def __init__(self, initial_mode: str = DEFAULT_HOTKEY_CHOICE):
        super().__init__()
        self.mode = initial_mode
        self._last_trigger_time = 0.0

    def set_mode(self, mode: str):
        self.mode = mode
        logger.info(f"Active global hotkey mode updated to: {mode}")

    def trigger(self, source: str = ""):
        """Centralized debouncer preventing rapid duplicate triggers across listeners."""
        now = time.time()
        if now - self._last_trigger_time < 0.40:
            return
        self._last_trigger_time = now
        logger.info(f"Global hotkey activated from {source} (mode: {self.mode})")
        self.hotkey_triggered.emit()

    def handle_flags_changed(self, event):
        """Monitors Left Fn (Function / Globe) key on Apple Silicon."""
        if sys.platform != "darwin":
            return
        # Keycode 63 is the Left Fn / Globe key on Apple keyboards
        if self.mode == "fn" and event.keyCode() == 63:
            flags = event.modifierFlags()
            # NSEventModifierFlagFunction = 8388608 (0x800000)
            is_fn_down = bool(flags & 8388608)
            if is_fn_down:
                self.trigger("Cocoa-Fn")

    def handle_key_down(self, event) -> bool:
        """Monitors key combinations across macOS."""
        if sys.platform != "darwin":
            return False
        try:
            from Cocoa import (
                NSAlternateKeyMask, NSControlKeyMask, NSCommandKeyMask, NSShiftKeyMask
            )
            code = event.keyCode()
            flags = event.modifierFlags()

            triggered = False

            # Option + Space (Keycode 49, Alt modifier)
            if self.mode in ("option_space", "fn") and code == 49 and (flags & NSAlternateKeyMask):
                triggered = True

            # Ctrl + Space (Keycode 49, Control modifier)
            elif self.mode == "ctrl_space" and code == 49 and (flags & NSControlKeyMask):
                triggered = True

            # Cmd + Shift + D (Keycode 2 for 'D')
            elif self.mode == "cmd_shift_d" and code == 2 and (flags & NSCommandKeyMask) and (flags & NSShiftKeyMask):
                triggered = True

            if triggered:
                self.trigger(f"Cocoa-KeyCombo-{self.mode}")
                return True
        except Exception:
            pass

        return False

def setup_native_macos_hotkeys(manager: HotkeyManager):
    """
    Registers native Apple Cocoa NSEvent global monitors for Left Fn and key combinations.
    Provides 100% reliable detection across all Mac apps without shortcut collisions or segfaults.
    """
    if sys.platform != "darwin":
        return

    try:
        from Cocoa import (
            NSEvent, NSEventMaskKeyDown, NSEventMaskFlagsChanged
        )

        def global_key_handler(event):
            try:
                manager.handle_key_down(event)
            except Exception:
                pass

        def global_flags_handler(event):
            try:
                manager.handle_flags_changed(event)
            except Exception:
                pass

        # Register global monitors (void handlers safe across all macOS versions)
        NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(NSEventMaskKeyDown, global_key_handler)
        NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(NSEventMaskFlagsChanged, global_flags_handler)

        logger.info("Registered native macOS Cocoa hotkey monitors (Left Fn & Key Combos).")
    except Exception as e:
        logger.warning(f"Could not initialize native Cocoa hotkey monitor: {e}")

def start_background_pynput_listener(manager: HotkeyManager):
    """Fallback & cross-platform pynput hotkey listener matching currently active hotkey mode."""
    try:
        from pynput import keyboard

        def on_option_space():
            if manager.mode in ("option_space", "alt_space", "fn"):
                manager.trigger("pynput-Option+Space")

        def on_ctrl_space():
            if manager.mode == "ctrl_space":
                manager.trigger("pynput-Ctrl+Space")

        def on_ctrl_shift_v():
            if manager.mode == "ctrl_shift_v":
                manager.trigger("pynput-Ctrl+Shift+V")

        def on_f8():
            if manager.mode == "f8":
                manager.trigger("pynput-F8")

        def on_f9():
            if manager.mode == "f9":
                manager.trigger("pynput-F9")

        def on_cmd_shift_d():
            if manager.mode == "cmd_shift_d":
                manager.trigger("pynput-Cmd+Shift+D")

        # Global hotkey mapping covering macOS & Windows configurations
        hotkeys = {
            '<alt>+<space>': on_option_space,
            '<ctrl>+<space>': on_ctrl_space,
            '<ctrl>+<shift>+v': on_ctrl_shift_v,
            '<f8>': on_f8,
            '<f9>': on_f9,
            '<cmd>+<shift>+d': on_cmd_shift_d,
        }

        with keyboard.GlobalHotKeys(hotkeys) as h:
            h.join()
    except Exception as e:
        logger.debug(f"Pynput background listener info: {e}")

def main():
    # Set Windows taskbar explicit App ID so icon pins properly
    if sys.platform == "win32":
        try:
            import ctypes
            myappid = 'voiceink.dictation.app.1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("VoiceInk")

    # Set Application Icon and native OS Taskbar / Dock Tile Icon
    icon_png = os.path.join(str(BASE_DIR), "assets", "icon.png")
    icon_ico = os.path.join(str(BASE_DIR), "assets", "icon.ico")
    icon_icns = os.path.join(str(BASE_DIR), "assets", "icon.icns")

    if sys.platform == "win32" and os.path.exists(icon_ico):
        app.setWindowIcon(QIcon(icon_ico))
    elif os.path.exists(icon_png):
        app.setWindowIcon(QIcon(icon_png))

    # macOS Dock Icon
    if sys.platform == "darwin":
        try:
            from Cocoa import NSApplication, NSImage
            ns_app = NSApplication.sharedApplication()
            icns_target = icon_icns if os.path.exists(icon_icns) else icon_png
            if os.path.exists(icns_target):
                dock_icon = NSImage.alloc().initWithContentsOfFile_(icns_target)
                if dock_icon:
                    ns_app.setApplicationIconImage_(dock_icon)
        except Exception as e:
            logger.debug(f"macOS Dock Icon initialization notice: {e}")

    # Main Window (Dictation Studio)
    window = MainWindow()
    window.show()

    # Position ultra-compact floating pill AT THE TOP CENTER OF SCREEN
    screen = app.primaryScreen()
    screen_geo = screen.availableGeometry()
    pill = window.floating_pill
    pill.setFixedSize(350, 42)
    
    top_x = screen_geo.x() + (screen_geo.width() - pill.width()) // 2
    top_y = screen_geo.y() + (14 if sys.platform == "darwin" else 10)
    pill.move(top_x, top_y)
    pill.show()

    # Hotkey Manager with dynamic preference switching
    hotkey_manager = HotkeyManager(initial_mode=window.selected_hotkey)
    hotkey_manager.hotkey_triggered.connect(window.toggle_recording)
    window.hotkey_preference_changed.connect(hotkey_manager.set_mode)

    # 1. Native macOS Cocoa monitor (Left Fn & combos on Apple Silicon)
    if sys.platform == "darwin":
        setup_native_macos_hotkeys(hotkey_manager)

    # 2. Universal cross-platform Pynput background thread (Windows & macOS fallback)
    pynput_thread = threading.Thread(
        target=start_background_pynput_listener,
        args=(hotkey_manager,),
        daemon=True
    )
    pynput_thread.start()

    logger.info("VoiceInk GUI application started with ultra-compact floating pill at top of screen.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
