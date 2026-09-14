# VoiceInk Windows Installation & Setup Guide

This guide walks you through installing, configuring permissions, and running **VoiceInk** on Windows 10 and Windows 11.

---

## 1. Installation Methods

### Method A: Download from GitHub Releases (Recommended)
1. Go to the repository's **Releases** page:
   `https://github.com/Thamizharasan-Gnanaprakasam/AI_Projects/releases`
2. Download the latest **`VoiceInk-Windows.zip`**.
3. Extract the zip file:
   - Right-click `VoiceInk-Windows.zip` and select **Extract All...**.
   - Choose a permanent destination folder (e.g., `C:\Program Files\VoiceInk` or `C:\Users\<YourUser>\AppData\Local\VoiceInk`).
4. Inside the extracted folder, you will find **`VoiceInk.exe`**.

> **Tip:** Right-click `VoiceInk.exe` -> **Send to** -> **Desktop (create shortcut)** or select **Pin to taskbar** for quick access.

---

### Method B: Build Locally on Windows
If you are on a Windows machine and wish to build directly from source:
1. Ensure **Python 3.10+** is installed from [python.org](https://www.python.org/downloads/) (make sure to check **"Add Python to PATH"** during installation).
2. Clone the repository and navigate into the project directory:
   ```cmd
   git clone https://github.com/Thamizharasan-Gnanaprakasam/AI_Projects.git
   cd AI_Projects\Wispr_Flow_Alt
   ```
3. Run the automated build script:
   ```cmd
   build_windows.bat
   ```
4. The executable folder will be compiled at: `dist\VoiceInk\VoiceInk.exe`.

---

## 2. Bypassing Windows SmartScreen ("Windows protected your PC")

Because VoiceInk is an open-source application without an expensive Microsoft Authenticode EV certificate, **Windows Defender SmartScreen** may show an alert on the first launch:

> *"Windows protected your PC: Microsoft Defender SmartScreen prevented an unrecognized app from starting."*

### How to open:
1. Click the text link **"More info"** on the blue SmartScreen popup.
2. An additional button will appear at the bottom right.
3. Click **"Run anyway"**.

*(This warning only appears the very first time you run the application).*

---

## 3. Windows System Requirements & Permissions

### 1. Microphone Permissions (Windows 10 / 11)
VoiceInk needs permission to access your audio input device:
1. Open Windows **Settings** (`Win + I`).
2. Go to **Privacy & Security** -> **Microphone**.
3. Ensure **"Microphone access"** is turned **On**.
4. Scroll down and verify that **"Let desktop apps access your microphone"** is set to **On**.

### 2. Antivirus Whitelisting (If applicable)
Third-party antivirus utilities (Norton, McAfee, Bitdefender) sometimes quarantine newly downloaded unsigned `.exe` files. If this occurs, add the `VoiceInk` folder to your antivirus exclusion list.

---

## 4. Initial Configuration (API Keys)

VoiceInk uses cloud AI models (Groq / Google Gemini) for fast speech recognition:

1. Double-click **`VoiceInk.exe`** to launch.
2. A sleek floating pill overlay will appear near the top of your screen.
3. Click the **Gear icon (Settings)**.
4. Set up your AI credentials:
   - **Groq Whisper** (Recommended for sub-second responses):
     - Create a free key at [console.groq.com](https://console.groq.com).
     - Paste it into the `GROQ_API_KEY` field.
   - **Google Gemini**:
     - Get a free key from [aistudio.google.com](https://aistudio.google.com).
     - Paste it into the `GEMINI_API_KEY` field.
5. Select your dictation language (English, Tamil, Spanish, German, etc.).
6. Click **Save Settings**.

---

## 5. Everyday Usage on Windows

| Feature | How to Use |
|---|---|
| **Toggle Dictation** | Press the global hotkey: **`Ctrl + Space`** (or **`Alt + Space`**) |
| **Instant Text Injection** | Place your cursor in any application (Word, Notepad, Slack, Chrome, VS Code). Press the hotkey, speak, and press it again — your words will automatically type at your active cursor. |
| **Dictation Studio** | Click the floating pill overlay to view your transcript history, adjust formatting, or transform tone (Casual, Professional, Bullet points). |
| **Close / Exit** | Click the Settings icon on the pill and select **Quit VoiceInk**, or close from the Windows system tray. |
