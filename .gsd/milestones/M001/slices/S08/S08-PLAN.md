# S08: Settings Page — Real Asset Check + Download

**Goal:** Replace hardcoded asset status strings with real path existence checks. Add download button that runs download_ckpt.py in a QThread. Show file sizes. Warn at startup if any asset missing.
**Demo:** Settings page shows green checkmarks next to all 5 model files with file sizes.

## Must-Haves

- All 5 assets checked by real os.path.exists(); download runs in background; startup modal if missing.

## Proof Level

- This slice proves: Delete one asset → red status shown; click Download → fills → status turns green.

## Integration Closure

Engine.load() raises AssetsMissingError caught by main window; routes to Settings page. Settings page calls engine.check_assets() for display.

## Verification

- Asset check logged at startup.

## Tasks

- [x] **T01: Rewrite settings.py with real asset check and download** `est:1h`
  1. Implement DownloadWorker(QThread): signals progress(str), finished(), error(str).
2. run(): calls subprocess.Popen(['python', 'download_ckpt.py'], cwd=project_root, stdout=PIPE, stderr=STDOUT); reads line-by-line, emits progress(line) for each tqdm output line.
3. Rewrite meanvc_gui/pages/settings.py:
   - Device section: current device label + QComboBox override + Apply button.
   - Model Assets section: QListWidget with per-asset rows showing name, path, status (✓ present / ✗ missing), size_mb.
   - Refresh button (calls check_assets(), repopulates list).
   - Download Missing button (primary, disabled if all present): spawns DownloadWorker.
   - Progress text area showing download output lines.
4. On startup: main.py calls check_assets(); if any missing, shows QMessageBox warning 'Missing model assets' with 'Open Settings' button.
  - Files: `meanvc_gui/pages/settings.py`, `meanvc_gui/main.py`
  - Verify: python -c 'from meanvc_gui.pages.settings import SettingsPage; print("settings import OK")'

## Files Likely Touched

- meanvc_gui/pages/settings.py
- meanvc_gui/main.py
