---
estimated_steps: 9
estimated_files: 2
skills_used: []
---

# T01: Rewrite settings.py with real asset check and download

1. Implement DownloadWorker(QThread): signals progress(str), finished(), error(str).
2. run(): calls subprocess.Popen(['python', 'download_ckpt.py'], cwd=project_root, stdout=PIPE, stderr=STDOUT); reads line-by-line, emits progress(line) for each tqdm output line.
3. Rewrite meanvc_gui/pages/settings.py:
   - Device section: current device label + QComboBox override + Apply button.
   - Model Assets section: QListWidget with per-asset rows showing name, path, status (✓ present / ✗ missing), size_mb.
   - Refresh button (calls check_assets(), repopulates list).
   - Download Missing button (primary, disabled if all present): spawns DownloadWorker.
   - Progress text area showing download output lines.
4. On startup: main.py calls check_assets(); if any missing, shows QMessageBox warning 'Missing model assets' with 'Open Settings' button.

## Inputs

- `meanvc_gui/pages/settings.py`
- `meanvc_gui/core/engine.py`
- `meanvc_gui/main.py`

## Expected Output

- `settings.py shows real asset status`
- `DownloadWorker runs download_ckpt.py in background`

## Verification

python -c 'from meanvc_gui.pages.settings import SettingsPage; print("settings import OK")'
