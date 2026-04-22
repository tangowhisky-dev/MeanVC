---
estimated_steps: 9
estimated_files: 2
skills_used: []
---

# T03: Profile export/import zip

1. Implement ProfileManager.export_profile(profile_id, output_zip_path):
   - Creates zip with: manifest.json (version, profile metadata) + audio/ + embeddings/.
   - manifest.json: {version:1, profile:{id,name,description}, audio_files:[{filename,duration,is_default,embedding_file}]}
2. Implement ProfileManager.import_profile(zip_path) → dict:
   - Extract zip to temp dir, read manifest, create new profile in DB.
   - Copy audio and embedding files to data/profiles/{new_id}/.
   - Return new profile dict.
3. Wire Export button to file save dialog + export_profile().
4. Add Import button in library header → file open dialog + import_profile() + refresh list.

## Inputs

- `meanvc_gui/core/profile_manager.py`

## Expected Output

- `export_profile() creates valid zip`
- `import_profile() restores profile with audio files`

## Verification

python -c "
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
