"""
Cross-Platform active cursor text injector (macOS & Windows).
Injects text seamlessly at the active cursor position across any application
using clipboard swap with instant clipboard state restoration.
"""

import sys
import time
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"

# macOS Native setup
if IS_MACOS:
    try:
        from AppKit import NSPasteboard, NSPasteboardTypeString, NSWorkspace
        from Quartz import (
            CGEventCreateKeyboardEvent,
            CGEventSetFlags,
            CGEventPost,
            kCGHIDEventTap,
            kCGEventFlagMaskCommand,
        )
        MACOS_NATIVE_AVAILABLE = True
    except ImportError:
        MACOS_NATIVE_AVAILABLE = False
else:
    MACOS_NATIVE_AVAILABLE = False

# Virtual keycode for 'v' on macOS standard keyboards
KEY_CODE_V = 9

def get_active_app_name() -> str:
    """Returns the name or title of the currently active frontmost application."""
    if IS_MACOS:
        if not MACOS_NATIVE_AVAILABLE:
            return "Unknown"
        try:
            app = NSWorkspace.sharedWorkspace().frontmostApplication()
            return app.localizedName() if app else "Unknown"
        except Exception as e:
            logger.debug(f"Failed to get macOS frontmost app: {e}")
            return "Unknown"

    elif IS_WINDOWS:
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.strip()
            return title if title else "Active Window"
        except Exception as e:
            logger.debug(f"Failed to get Windows active window title: {e}")
            return "Active Window"

    return "Unknown"

def inject_text_at_cursor(text: str, restore_clipboard: bool = True) -> bool:
    """
    Injects text directly at the active cursor position across any application
    on macOS (via CoreGraphics Cmd+V) and Windows (via pynput Ctrl+V).
    """
    if not text:
        return False

    # ----------------- macOS Implementation -----------------
    if IS_MACOS:
        if not MACOS_NATIVE_AVAILABLE:
            logger.error("macOS PyObjC / Quartz libraries not available.")
            return False

        pasteboard = NSPasteboard.generalPasteboard()
        
        # 1. Backup old clipboard string
        old_text: Optional[str] = None
        try:
            old_text = pasteboard.stringForType_(NSPasteboardTypeString)
        except Exception as e:
            logger.debug(f"Could not read old clipboard content: {e}")

        try:
            # 2. Put target text on clipboard
            pasteboard.clearContents()
            pasteboard.setString_forType_(text, NSPasteboardTypeString)

            # Brief settle time
            time.sleep(0.02)

            # 3. Trigger Cmd + V (down and up events)
            event_down = CGEventCreateKeyboardEvent(None, KEY_CODE_V, True)
            CGEventSetFlags(event_down, kCGEventFlagMaskCommand)
            CGEventPost(kCGHIDEventTap, event_down)

            event_up = CGEventCreateKeyboardEvent(None, KEY_CODE_V, False)
            CGEventSetFlags(event_up, kCGEventFlagMaskCommand)
            CGEventPost(kCGHIDEventTap, event_up)

            # 4. Wait for the receiving app to consume the paste event
            time.sleep(0.06)

            # 5. Restore old clipboard if desired
            if restore_clipboard:
                pasteboard.clearContents()
                if old_text is not None:
                    pasteboard.setString_forType_(old_text, NSPasteboardTypeString)

            return True
        except Exception as e:
            logger.error(f"Failed to inject text at cursor on macOS: {e}")
            return False

    # ----------------- Windows Implementation -----------------
    elif IS_WINDOWS:
        try:
            import ctypes
            from ctypes import wintypes
            from pynput.keyboard import Controller, Key

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            CF_UNICODETEXT = 13
            GMEM_MOVEABLE = 0x0002

            def win32_get_clipboard() -> Optional[str]:
                for _ in range(5):
                    if user32.OpenClipboard(None):
                        break
                    time.sleep(0.01)
                else:
                    return None
                try:
                    h_mem = user32.GetClipboardData(CF_UNICODETEXT)
                    if not h_mem:
                        return None
                    kernel32.GlobalLock.restype = ctypes.c_wchar_p
                    ptr = kernel32.GlobalLock(h_mem)
                    val = str(ptr) if ptr else None
                    kernel32.GlobalUnlock(h_mem)
                    return val
                finally:
                    user32.CloseClipboard()

            def win32_set_clipboard(content: str) -> bool:
                data = content.encode('utf-16le') + b'\x00\x00'
                h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
                if not h_mem:
                    return False
                kernel32.GlobalLock.restype = ctypes.c_void_p
                ptr = kernel32.GlobalLock(h_mem)
                if not ptr:
                    kernel32.GlobalFree(h_mem)
                    return False
                ctypes.memmove(ptr, data, len(data))
                kernel32.GlobalUnlock(h_mem)

                for _ in range(5):
                    if user32.OpenClipboard(None):
                        break
                    time.sleep(0.01)
                else:
                    kernel32.GlobalFree(h_mem)
                    return False

                try:
                    user32.EmptyClipboard()
                    user32.SetClipboardData(CF_UNICODETEXT, h_mem)
                    return True
                finally:
                    user32.CloseClipboard()

            old_text = win32_get_clipboard() if restore_clipboard else None
            
            # Put target text on clipboard thread-safely
            if not win32_set_clipboard(text):
                logger.warning("Failed setting clipboard via Win32 API.")
                return False

            time.sleep(0.04)

            # Simulate Ctrl + V
            keyboard_ctrl = Controller()
            with keyboard_ctrl.pressed(Key.ctrl):
                keyboard_ctrl.tap('v')

            # Wait for receiving app to consume the paste event
            time.sleep(0.08)

            # Restore original clipboard
            if restore_clipboard and old_text is not None:
                def _restore():
                    time.sleep(0.20)
                    try:
                        win32_set_clipboard(old_text)
                    except Exception:
                        pass
                threading.Thread(target=_restore, daemon=True).start()

            return True
        except Exception as e:
            logger.error(f"Failed to inject text at cursor on Windows: {e}")
            return False

    # Fallback
    logger.warning(f"Unsupported platform for text injection: {sys.platform}")
    return False
