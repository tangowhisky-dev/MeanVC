---
estimated_steps: 9
estimated_files: 2
skills_used: []
---

# T02: QThread embedding worker with progress badge

1. Create EmbeddingWorker(QThread) in profile_manager.py (or a workers.py):
   - signals: progress(int), finished(dict audio_file), error(str)
   - run(): calls profile_manager.add_audio() with extraction; emits progress at 0/50/100
2. In LibraryPage._add_audio():
   - Create EmbeddingWorker, connect signals.
   - Show file's status badge as 'Extracting...' (amber) while worker runs.
   - On finished: refresh audio list, set badge to 'Ready' (green).
   - On error: set badge to 'Failed' (red), show QMessageBox.
3. Disable 'Add Audio' button while extraction in progress to prevent double-submit.

## Inputs

- `meanvc_gui/core/profile_manager.py`
- `meanvc_gui/pages/library.py`

## Expected Output

- `EmbeddingWorker class exists and works`
- `UI shows Extracting badge during extraction`

## Verification

python -c 'from meanvc_gui.core.profile_manager import EmbeddingWorker; print("worker OK")'
