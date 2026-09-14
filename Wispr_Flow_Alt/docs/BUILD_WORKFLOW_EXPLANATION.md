# GitHub Actions Workflow Explanation (`build.yml`)

This document provides a comprehensive, section-by-section explanation of the continuous integration and automated build pipeline configured in [`.github/workflows/build.yml`](file:///Users/thamizharasangnanaprakasam/Documents/GitHub/Technical/AI_Projects/.github/workflows/build.yml).

---

## 1. Overview & Architecture

PyInstaller compiles Python scripts into platform-specific machine code binaries. Because **cross-compilation is not supported by PyInstaller** (a macOS machine cannot build Windows `.exe` files, and a Windows machine cannot build macOS `.app` bundles), the CI pipeline uses GitHub-hosted virtual machines running native operating systems:

```
                  ┌─────────────────────────────────────┐
                  │ Push / Tag / Manual Workflow Trigger│
                  └──────────────────┬──────────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 │                                       │
                 ▼                                       ▼
       ┌────────────────────┐                 ┌────────────────────┐
       │   macos-14 Runner  │                 │ windows-latest     │
       │   (Apple Silicon)  │                 │ (Windows Server)   │
       │                    │                 │                    │
       │ • Python 3.11      │                 │ • Python 3.11      │
       │ • Install PyObjC   │                 │ • Install PyQt/pynput│
       │ • PyInstaller Spec │                 │ • PyInstaller Spec │
       │ • Codesign ad-hoc  │                 │ • Python Zip pack  │
       │ • VoiceInk.app zip │                 │ • VoiceInk.exe zip │
       └─────────┬──────────┘                 └─────────┬──────────┘
                 │                                       │
                 └───────────────────┬───────────────────┘
                                     │
                                     ▼
                      ┌─────────────────────────────┐
                      │    Publish GitHub Release   │
                      │  (ubuntu-latest orchestrator│
                      │   tags/releases as v1.0.0)  │
                      └─────────────────────────────┘
```

---

## 2. Trigger Configuration

```yaml
on:
  push:
    branches: [ main, master ]
    tags: [ 'v*' ]
  pull_request:
    branches: [ main, master ]
  workflow_dispatch:
```

- **`push.branches`**: Runs the build automatically whenever code is pushed to `main` or `master`.
- **`push.tags: ['v*']`**: Automatically triggers release builds when a version tag (like `v1.0.0`, `v1.1.0`) is pushed.
- **`pull_request`**: Verifies that any incoming PR builds cleanly before merging.
- **`workflow_dispatch`**: Enables manual "Run workflow" execution from the GitHub Actions web UI with a single click.

---

## 3. Permissions

```yaml
permissions:
  contents: write
```

- Grants GitHub Actions permission to publish releases, create git tags, and upload binary assets (`VoiceInk-Windows.zip`, `VoiceInk-macOS.zip`) to the repository's GitHub Releases tab.

---

## 4. The Build Matrix Job (`build`)

```yaml
jobs:
  build:
    name: Build VoiceInk on ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    defaults:
      run:
        working-directory: Wispr_Flow_Alt
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: macos-14
            platform: macos
            asset_name: VoiceInk-macOS
          - os: windows-latest
            platform: windows
            asset_name: VoiceInk-Windows
```

### Key Elements:
1. **`defaults.run.working-directory: Wispr_Flow_Alt`**:
   - Because the root repository is `AI_Projects` and VoiceInk source code is in `Wispr_Flow_Alt`, this ensures every command runs directly inside the project subfolder without repetitive `cd` commands.
2. **`macos-14`**:
   - Runs on native Apple Silicon (M1/M2/M3 ARM64 architecture), ensuring full binary compatibility with Apple Silicon hardware.
3. **`windows-latest`**:
   - Runs on standard 64-bit Windows virtual machines.
4. **`fail-fast: false`**:
   - If one platform experiences a transient issue, the other platform continues building without being cancelled.

---

## 5. Step-by-Step Breakdown

### Step 1: Repository Checkout
```yaml
- name: Check out repository
  uses: actions/checkout@v4
```
Clones the repository files into the runner workspace.

---

### Step 2: Python Environment Setup
```yaml
- name: Set up Python 3.11
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'
    cache: 'pip'
    cache-dependency-path: 'Wispr_Flow_Alt/requirements.txt'
```
- Installs Python 3.11 (optimal stability for PyQt6, sounddevice, and numpy).
- Enables pip package caching using `requirements.txt` to accelerate subsequent builds.

---

### Step 3: Platform Dependency Installation
```yaml
- name: Install dependencies (macOS)
  if: runner.os == 'macOS'
  run: |
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    python -m pip install pyinstaller

- name: Install dependencies (Windows)
  if: runner.os == 'Windows'
  run: |
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    python -m pip install pyinstaller
```
- Upgrades `pip` to avoid legacy wheel installation issues.
- Installs platform-conditional packages:
  - macOS installs `pyobjc`, `pynput`, `PyQt6`, `sounddevice`, etc.
  - Windows automatically skips macOS-specific libraries and installs Windows-compatible packages.
- Installs `pyinstaller`.

---

### Step 4: Environment File Fallback
```yaml
- name: Ensure fallback .env exists
  shell: bash
  run: |
    if [ ! -f .env ]; then
      if [ -f .env.example ]; then
        cp .env.example .env
      else
        touch .env
      fi
    fi
```
- **Why this is critical**: The `.env` file contains sensitive local credentials and is ignored by `.gitignore`. Without this step, clean checkouts in CI lack `.env`, causing packaging specifications that bundle `.env` to throw `FileNotFoundError`.

---

### Step 5: macOS Bundle Packaging (.app)
```yaml
- name: Build macOS App (.app)
  if: runner.os == 'macOS'
  run: |
    xattr -cr . || true
    python -m PyInstaller --clean -y VoiceInk.spec
    xattr -cr dist/VoiceInk.app || true
    codesign --force --deep --sign - dist/VoiceInk.app || true
    cd dist
    ditto -c -k --sequesterRsrc --keepParent VoiceInk.app VoiceInk-macOS.zip
```
- **`xattr -cr`**: Removes Apple extended metadata attributes (such as `com.apple.FinderInfo`) that cause codesign warnings.
- **`PyInstaller VoiceInk.spec`**: Compiles the source files, UI templates, sounds, and icons into a macOS `.app` bundle at `dist/VoiceInk.app`.
- **`codesign --force --deep --sign -`**: Applies an ad-hoc local signature so macOS recognizes the bundle integrity.
- **`ditto`**: Uses Apple's native archival tool to preserve file permissions, symbolic links, and resource forks into `VoiceInk-macOS.zip`.

---

### Step 6: Windows Executable Packaging (.exe)
```yaml
- name: Build Windows App (.exe)
  if: runner.os == 'Windows'
  run: |
    python -m PyInstaller --clean -y VoiceInk_win.spec
    python -c "import shutil; shutil.make_archive('dist/VoiceInk-Windows', 'zip', 'dist/VoiceInk')"
```
- **`PyInstaller VoiceInk_win.spec`**: Compiles the application into a standalone folder `dist\VoiceInk\` containing `VoiceInk.exe` along with Qt DLLs and audio backends.
- **`python -c "import shutil; ..."`**: Compresses the folder into `VoiceInk-Windows.zip` using Python's standard library, avoiding PowerShell encoding quirks.

---

### Step 7: Artifact Upload
```yaml
- name: Upload Build Artifacts
  uses: actions/upload-artifact@v4
  with:
    name: ${{ matrix.asset_name }}
    path: |
      Wispr_Flow_Alt/dist/VoiceInk-*.zip
    retention-days: 14
```
Stores the compiled zip files in the GitHub Actions run summary for 14 days.

---

## 6. The Release Job (`release`)

```yaml
release:
  name: Publish GitHub Release
  needs: build
  if: github.event_name == 'push' && (github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/'))
  runs-on: ubuntu-latest
  permissions:
    contents: write
```

- **`needs: build`**: Waits until both macOS and Windows runners complete successfully.
- **`softprops/action-gh-release@v2`**:
  - Gathers both `VoiceInk-Windows.zip` and `VoiceInk-macOS.zip`.
  - Publishes them to the **GitHub Releases** page under release tag `v1.0.0` (or the pushed tag).
  - Provides direct, permanent download links with standard browser download support (no authentication or cookie restrictions).
