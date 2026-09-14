# Implementation Plan — Compact Interactive Floating Pill & Reliable Hotkey Speech Recognition

Enhance Wispr Flow Alternative with an ultra-compact interactive floating capsule, real-time reactive speech animations, interactive language/tone quick-switchers, and 100% reliable global hotkey dictation.

## User Review Required
> [!NOTE]
> - **Floating Capsule Sizing**: Pill dimensions reduced from `370x56` to `290x36` (over 35% height reduction), providing a true Wispr Flow / Dynamic Island feel without obstructing screens or notch areas.
> - **Hotkey Feedback**: Added native macOS sound chimes (`Tink` on recording start, `Pop` on completion) so you immediately know your mic is live without having to look at the screen.
> - **Smart Auto-Stop**: In addition to pressing the hotkey again to stop, the app now also includes optional smart silence auto-stop (1.5s of silence after speech automatically stops recording and transcribes).

---

## Proposed Changes

### 1. Interactive Compact Floating Capsule (`ui/floating_pill.py`)
- **Reduce Size**: Shrink base size to `290x36 px`, padding to `6px 10px`.
- **Reactive Waveform Animation (`WaveformVisualizer`)**:
  - Embedded 5-bar animated equalizer that dynamically dances in real-time based on incoming microphone RMS energy (`audio_level`).
  - Smooth animation states:
    - *Idle*: Dormant sleek dots/bars.
    - *Speaking/Recording*: Lively bouncing sound waves with gradient coloring.
    - *Processing*: Gentle undulating shimmer.
    - *Success*: Pulsing green confirmation.
- **Interactive Language Chip Button (`QPushButton` with `QMenu`)**:
  - Clickable chip that pops up an interactive menu with all supported languages (Auto-Detect, Tamil, English, Spanish, Hindi, French, German, etc.).
  - Instantly switches active language and syncs with `MainWindow` and `.env`.
- **Interactive Tone Chip Button (`QPushButton` with `QMenu`)**:
  - Clickable chip that pops up an interactive menu with all tones (Smart Verbatim, Casual, Professional, Concise, Technical).
  - Instantly switches active tone and syncs with `MainWindow` and `.env`.
- **Native macOS Frosted Glass Vibrancy**: Ensure `NSVisualEffectView` fits the new compact dimensions.

### 2. Stylesheet Modernization (`ui/styles.py`)
- Update `FLOATING_PILL_QSS`:
  - Compact capsule styling (`border-radius: 18px`, height 36px).
  - Chip button styles for Language and Tone with subtle hover effects and chevrons.
  - Dropdown popup menu styling (`QMenu`) with dark frosted glass appearance.

### 3. Hotkey Detection & Speech Recognition Fix (`run_gui.py`)
- **Centralized Debounce Manager**:
  - Prevent duplicate trigger events caused by simultaneous Cocoa global/local monitors and background `pynput` listener.
  - Enforce a 400ms debounce threshold.
- **Strict Mode Filtering in Pynput Listener**:
  - Ensure pynput only emits triggers when the user presses the currently selected hotkey.
- **Sound Feedback (`Cocoa.NSSound`)**:
  - Play native subtle chime on dictation start and finish.

### 4. Dictation Pipeline & Silence Detection (`ui/main_window.py`)
- **Audio Level Forwarding**:
  - Feed real-time RMS levels from `level_timer` directly into `floating_pill.set_audio_level(level)`.
- **Smart Silence Auto-Stop**:
  - While recording, detect when the user has spoken and then paused for 1.4s, automatically stopping and triggering transcription without forcing the user to hit the hotkey again if they don't want to.
- **Bidirectional Sync**:
  - Connect floating pill's `language_selected` and `tone_selected` signals to `MainWindow` slots to keep preferences completely synchronized.

---

## Verification Plan

### Automated / Manual Script Tests
1. Test floating pill widget initialization, geometry, menu population, and waveform animation rendering using PyQt headless/interactive test.
2. Test hotkey manager debouncing logic with rapid simulated events.
3. Test sound feedback and audio recording start/stop cycle.

### Visual Verification
- Launch application via `.venv/bin/python run_gui.py` and take screenshots of:
  1. The new ultra-compact floating pill in Ready state at top of screen.
  2. Language dropdown menu opened from the pill.
  3. Tone dropdown menu opened from the pill.
  4. Active speaking animation on the pill.
