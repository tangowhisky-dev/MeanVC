# S04: Library Page — Full CRUD + Embedding Extraction

**Goal:** Rewrite the Library page with complete CRUD: create/rename/delete profiles, upload audio with real embedding extraction in a QThread worker with progress, set default reference, show per-file embedding status badge, export/import profile zip.
**Demo:** Create 'Trump' profile, upload a 10s wav, watch progress bar, see 'Ready' badge; use it for conversion on Offline page.

## Must-Haves

- Profile CRUD works; embedding extraction shows progress; status badge shows Ready/Extracting/Failed; export produces valid zip; import restores profile.

## Proof Level

- This slice proves: Create profile, upload wav, confirm .pt exists at data/profiles/{id}/embeddings/{fid}.pt; delete profile confirms disk cleanup.

## Integration Closure

Offline and Realtime pages read profile list; Library emits profile_selected signal consumed by app.current_profile_changed.

## Verification

- Embedding extraction duration logged; file size logged on upload.

## Tasks

- [x] **T01: Rewrite library.py with full CRUD and clean theme** `est:1.5h`
  Rewrite meanvc_gui/pages/library.py using S02 theme components:
1. Layout: left panel (profile list, 280px) + right panel (profile detail + audio files).
2. Profile list: scrollable list of ProfileCards (name, file count, duration badge, embedding status icon).
3. Header: 'Voice Profiles' title + '+ New Profile' primary button.
4. Profile detail panel:
   - Profile name (editable inline on double-click), description, stats.
   - 'Use for Conversion' button that emits app.current_profile_changed.
   - 'Export Profile' button, 'Delete Profile' danger button.
5. Audio files sub-panel:
   - List of audio files: filename, duration, status badge (Ready=green/Extracting=amber/Failed=red/Pending=gray).
   - Add Audio button, Remove button per file, Set as Default star button.
   - File drag-and-drop accepted on the panel.
6. Wire _new_profile(), _delete_profile(), _add_audio(), _remove_audio(), _set_default().
7. Import COLORS only from meanvc_gui.components.theme — no modern_theme references.
  - Files: `meanvc_gui/pages/library.py`
  - Verify: python -c 'from meanvc_gui.pages.library import LibraryPage; print("library import OK")'

- [x] **T02: QThread embedding worker with progress badge** `est:45m`
  1. Create EmbeddingWorker(QThread) in profile_manager.py (or a workers.py):
   - signals: progress(int), finished(dict audio_file), error(str)
   - run(): calls profile_manager.add_audio() with extraction; emits progress at 0/50/100
2. In LibraryPage._add_audio():
   - Create EmbeddingWorker, connect signals.
   - Show file's status badge as 'Extracting...' (amber) while worker runs.
   - On finished: refresh audio list, set badge to 'Ready' (green).
   - On error: set badge to 'Failed' (red), show QMessageBox.
3. Disable 'Add Audio' button while extraction in progress to prevent double-submit.
  - Files: `meanvc_gui/core/profile_manager.py`, `meanvc_gui/pages/library.py`
  - Verify: python -c 'from meanvc_gui.core.profile_manager import EmbeddingWorker; print("worker OK")'

- [x] **T03: Profile export/import zip** `est:45m`
  1. Implement ProfileManager.export_profile(profile_id, output_zip_path):
   - Creates zip with: manifest.json (version, profile metadata) + audio/ + embeddings/.
   - manifest.json: {version:1, profile:{id,name,description}, audio_files:[{filename,duration,is_default,embedding_file}]}
2. Implement ProfileManager.import_profile(zip_path) → dict:
   - Extract zip to temp dir, read manifest, create new profile in DB.
   - Copy audio and embedding files to data/profiles/{new_id}/.
   - Return new profile dict.
3. Wire Export button to file save dialog + export_profile().
4. Add Import button in library header → file open dialog + import_profile() + refresh list.
  - Files: `meanvc_gui/core/profile_manager.py`, `meanvc_gui/pages/library.py`
  - Verify: python -c "
import sys, tempfile, os; sys.path.insert(0,'')
from meanvc_gui.core.profile_manager import get_profile_manager
pm = get_profile_manager()
p = pm.create_profile('test_export')
with tempfile.TemporaryDirectory() as d:
    zip_path = os.path.join(d, 'test.zip')
    pm.export_profile(p['id'], zip_path)
    assert os.path.exists(zip_path), 'zip not created'
    print('export OK')
pm.delete_profile(p['id'])
"

## Files Likely Touched

- meanvc_gui/pages/library.py
- meanvc_gui/core/profile_manager.py
