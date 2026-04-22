# DECISIONS — MeanVC

Append-only register of architectural and pattern decisions.

---

## D001 — Flet as GUI framework *(superseded by D011)*
**Scope:** architecture
**Decision:** Use Flet (Python + Flutter) for the desktop GUI.
**Choice:** Flet
**Rationale:** [Original plan — see D011 for what was actually built.]
**Revisable:** N/A — superseded.

---

## D002 — Zero-shot inference, no per-profile training
**Scope:** architecture
**Decision:** MeanVC profiles contain only reference audio + pre-extracted embeddings. No training loop.
**Choice:** Zero-shot only
**Rationale:** MeanVC's DiT model is pre-trained on a large corpus. Per-profile fine-tuning is not supported by this architecture. This simplifies the app dramatically vs rvc-web.
**Revisable:** No — this is a fundamental property of the MeanVC model.

---

## D003 — Pre-extract speaker embeddings on audio upload
**Scope:** profile system
**Decision:** Run WavLM ECAPA-TDNN on audio upload, save embedding as `.pt` file. Load `.pt` at inference time.
**Choice:** Pre-extract and cache
**Rationale:** WavLM-Large is ~1.3GB and slow to load. Re-running it on every conversion adds 200-400ms latency. Caching the 256-dim embedding is negligible storage (~1KB per file).
**Revisable:** Yes — if model is already loaded in memory for other purposes, re-extraction cost is trivial.

---

## D004 — uv venv at ~/.meanvc (no conda)
**Scope:** environment
**Decision:** Use `uv venv ~/.meanvc --python 3.11` as the Python environment.
**Choice:** uv venv
**Rationale:** Conda has commercial licensing restrictions. uv is MIT-licensed, faster, and produces self-contained venvs. Consistent with rvc-web migration.
**Revisable:** Yes — if uv has aarch64 issues, fall back to python -m venv.

---

## D005 — SQLite for profile metadata (sync, not aiosqlite)
**Scope:** database
**Decision:** Use synchronous `sqlite3` (stdlib) for the GUI, not aiosqlite.
**Choice:** sqlite3 (sync)
**Rationale:** PySide6 event handlers run on the Qt main thread. aiosqlite requires an asyncio event loop which Qt does not natively run. Heavy DB operations (embedding extraction) happen in QThread workers and can use sqlite3 directly.
**Revisable:** Yes — if a FastAPI backend is added later, switch to aiosqlite.

---

## D006 — Inference via convert.py API, not subprocess
**Scope:** engine integration
**Decision:** Import and call `convert.py` functions directly from `engine.py`, not via subprocess.
**Choice:** Direct import
**Rationale:** No subprocess stdout parsing bugs (rvc-web lesson). Models are loaded once and kept in memory. Subprocess would require re-loading 4 models (~2GB) per conversion.
**Revisable:** No — subprocess adds latency and complexity with no benefit for a desktop app.

---

## D007 — Single shared model instance, loaded once
**Scope:** engine
**Decision:** Load DiT, Vocos, ASR, WavLM once at app startup (or first conversion), keep in memory.
**Choice:** Singleton engine
**Rationale:** Model loading takes ~5-15s. Users expect instant conversion after first load. Memory footprint (~2-4GB) is acceptable on any modern machine capable of running MeanVC.
**Revisable:** Yes — add lazy loading per page if startup time is unacceptable.

---

## D008 — Profile export format: zip with manifest.json v1
**Scope:** profile portability
**Decision:** Export = zip containing `manifest.json` + `audio/` + `embeddings/` + `prompt/`. No model checkpoints.
**Choice:** zip manifest-v1 (audio + embeddings only)
**Rationale:** MeanVC uses a shared base model — there are no per-profile checkpoint files to export. The entire profile is just audio + cached embeddings. This makes exports tiny (10–50MB) vs rvc-web's 400–500MB.
**Revisable:** Yes — if per-profile fine-tuning is added in future.

---

## D009 — Realtime steps=1 default, offline steps=2 default
**Scope:** inference quality/speed
**Decision:** Realtime conversion uses 1 denoising step by default. Offline uses 2.
**Choice:** steps=1 (RT), steps=2 (offline)
**Rationale:** At steps=1, RTF < 0.3 on CUDA. At steps=2, RTF ~0.5. Realtime requires RTF < 1.0 with headroom. Offline has no latency constraint so the extra step is worth it.
**Revisable:** Yes — expose as user-configurable slider.

---

## D010 — ECAPA-TDNN cosine similarity for analysis page
**Scope:** analysis
**Decision:** Speaker similarity = cosine similarity between ECAPA-TDNN embeddings of converted output vs reference audio.
**Choice:** ECAPA cosine similarity
**Rationale:** Same approach as rvc-web analysis page. ECAPA-TDNN is already downloaded as part of asset set. Cosine similarity in embedding space correlates well with perceptual speaker identity.
**Revisable:** Yes — could add UTMOS-style MOS scorer for quality assessment.

---

## Decisions Table

| # | When | Scope | Decision | Choice | Rationale | Revisable? | Made By |
|---|------|-------|----------|--------|-----------|------------|---------|
| D001 |  | architecture | GUI framework selection — Flet vs PySide6 | PySide6 (Qt6) | Implementation was completed in PySide6, not Flet as originally planned in D001. PySide6 offers richer widget set (QCharts for analysis, QMediaPlayer, native file dialogs), better realtime waveform control via QPainter, and more predictable threading via QThread/signals-slots. D001 Flet decision is superseded by this. | No — codebase is fully PySide6 | agent |
