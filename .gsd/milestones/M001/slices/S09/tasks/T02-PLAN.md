---
estimated_steps: 12
estimated_files: 1
skills_used: []
---

# T02: Rewrite README.md

Rewrite README.md from scratch:
1. Header: title, badges (arXiv, HuggingFace, Demo).
2. Features list.
3. Getting Started:
   - Environment setup: conda OR uv venv (both options).
   - Download models: python download_ckpt.py (assets go to assets/ckpt/ and assets/wavLM/) — not src/ckpt/.
   - WavLM manual download with correct destination (assets/wavLM/).
4. CLI Usage: convert.py with examples.
5. Desktop App (PySide6): pip install -r meanvc_gui/requirements.txt; python -m meanvc_gui.main.
6. Feature overview table (Library, Offline, Realtime, Analysis, Settings).
7. Training section (existing content).
8. Citation, license, contact.

## Inputs

- `README.md`

## Expected Output

- `README.md accurate and complete`

## Verification

grep -n 'src/ckpt\|meanvc_gui/data' README.md | wc -l | awk '{exit $1>0}'
