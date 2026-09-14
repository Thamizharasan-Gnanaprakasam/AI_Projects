# VoiceInk macOS Installation & Setup Guide

This guide walks you through installing, configuring permissions, and running **VoiceInk** on macOS (Apple Silicon & Intel).

---

## 1. Installation Methods

### Method A: Download from GitHub Releases (Recommended)
1. Go to the repository's **Releases** page:
   `https://github.com/Thamizharasan-Gnanaprakasam/AI_Projects/releases`
2. Under the latest release, download **`VoiceInk-macOS.zip`**.
3. Double-click the zip file to extract **`VoiceInk.app`**.
4. Drag and drop **`VoiceInk.app`** into your **Applications** folder (`/Applications`).

---

### Method B: Build Locally on macOS
If you prefer building directly from source:
```bash
git clone https://github.com/Thamizharasan-Gnanaprakasam/AI_Projects.git
cd AI_Projects/Wispr_Flow_Alt

# Build using the included packaging script
./build_app.sh
```
The output bundle will be created at: `dist/VoiceInk.app`.

---

## 2. Bypassing macOS Gatekeeper ("App Not Opened" Warning)

Because VoiceInk is an open-source tool built without an annual paid ($99/year) Apple Developer certificate, macOS Gatekeeper displays a security popup on the first run:

> *"VoiceInk" Not Opened: Apple could not verify "VoiceInk" is free of malware that may harm your Mac...*

### Quickest Fix (One-Line Terminal Command)
Open your macOS **Terminal** and run:

- If VoiceInk is in Applications:
  ```bash
  xattr -cr /Applications/VoiceInk.app
  ```
- If VoiceInk is in the project's `dist` folder:
  ```bash
  xattr -cr dist/VoiceInk.app
  ```

*This command strips Apple's internet quarantine attribute (`com.apple.quarantine`), allowing the app to launch directly.*

---

### Alternative GUI Method (Through System Settings)
1. When the "Not Opened" popup appears, click **Done** (do **not** click Move to Trash).
2. Open **System Settings** on your Mac.
3. Click **Privacy & Security** in the sidebar.
4. Scroll down to the **Security** section.
5. You will see: *"VoiceInk was blocked from use because it is not from an identified developer."*
6. Click **Open Anyway**, enter your Mac password or Touch ID, and confirm **Open**.

---

## 3. Required macOS Permissions

VoiceInk requires two essential macOS permissions to function as a system-wide voice dictation tool:

### 1. Microphone Access
- **Why it is needed**: To record your voice when you press the hotkey.
- **How to grant**: macOS will display a permission prompt when you first record. Click **OK**.
- *Manual path:* `System Settings > Privacy & Security > Microphone > Enable VoiceInk`.

### 2. Accessibility Permissions
- **Why it is needed**: 
  - To listen for the global hotkey (e.g., `Fn`, `Ctrl+Space`, or `Right Option`) even when VoiceInk is in the background.
  - To paste/inject transcribed text directly at your active cursor across other applications.
- **How to grant**:
  1. Go to `System Settings > Privacy & Security > Accessibility`.
  2. Click the `+` button.
  3. Select **VoiceInk.app** from `/Applications`.
  4. Toggle the switch to **On**.

---

## 4. Initial Configuration (API Keys)

VoiceInk supports ultra-fast cloud transcription (Groq / Gemini) and local Apple Silicon MLX models:

1. Launch **VoiceInk**.
2. Click the **Settings (gear icon)** on the floating pill or in the Dictation Studio.
3. Choose your preferred AI backend:
   - **Groq Whisper** (Recommended for sub-second cloud transcription):
     - Get a free API key at [console.groq.com](https://console.groq.com)
     - Paste your `GROQ_API_KEY` in Settings.
   - **Google Gemini**:
     - Get a free key at [aistudio.google.com](https://aistudio.google.com)
     - Enter your `GEMINI_API_KEY`.
   - **Local MLX Whisper** (Apple Silicon only):
     - Runs completely offline on your Mac's Neural Engine.
4. Select your primary dictation language (English, Tamil, Spanish, French, etc.).
5. Click **Save Settings**.

---

## 5. Everyday Usage & Shortcuts

| Action | Shortcut / Interaction |
|---|---|
| **Toggle Voice Recording** | Press the configured hotkey (Default: `Left Fn` / `Globe` key on Mac keyboards, or `Ctrl+Space`) |
| **Instant Text Injection** | Stop speaking or press the hotkey again; the transcribed text automatically types at your active cursor |
| **Dictation Studio** | Click the floating overlay pill to expand the studio for editing, history, and tone customization |
| **Quit Application** | Click the Settings icon -> **Quit VoiceInk**, or close from the menu bar / Dock |
