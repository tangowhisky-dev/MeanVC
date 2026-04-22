---
estimated_steps: 14
estimated_files: 1
skills_used: []
---

# T01: Rewrite library.py with full CRUD and clean theme

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

## Inputs

- `meanvc_gui/pages/library.py`
- `meanvc_gui/components/theme.py`
- `meanvc_gui/core/profile_manager.py`

## Expected Output

- `library.py fully functional with CRUD operations`
- `ProfileCard uses theme.py colors only`

## Verification

python -c 'from meanvc_gui.pages.library import LibraryPage; print("library import OK")'
