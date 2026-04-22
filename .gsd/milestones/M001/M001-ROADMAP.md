# M001: MeanVC Desktop App — Production-Ready

**Vision:** Transform the MeanVC GUI scaffold into a fully working, polished desktop application. Strip all Flet context, consolidate the codebase to a single clean entry point, wire the inference engine to real models, build a professional PySide6 UI consistent in design and behaviour, and deliver end-to-end functionality: profile management with real embedding extraction, offline voice conversion, real-time microphone conversion, and speaker similarity analysis — all backed by the actual MeanVC inference pipeline.

## Success Criteria

- python -m meanvc_gui.main launches with no import errors on macOS MPS and Linux CUDA
- Zero Flet references in any tracked Python file
- Single entry point (meanvc_gui/main.py), single theme module (meanvc_gui/components/theme.py)
- DB lives at data/meanvc.db (project root data/)
- Profile creation + audio upload + WavLM embedding extraction works end-to-end
- Offline conversion produces a real non-empty wav file
- Realtime conversion runs at RTF < 1.0 on CUDA/MPS
- Speaker similarity returns real ECAPA cosine score, not 75.0
- Settings page shows real asset status from disk
- README accurately describes asset paths, launch command, and feature status

## Slices

- [x] **S01: S01** `risk:low` `depends:[]`
  > After this: App launches from python -m meanvc_gui.main with no import errors.

- [x] **S02: S02** `risk:low` `depends:[]`
  > After this: Navigate all five pages; every page looks intentionally designed and visually consistent.

- [x] **S03: S03** `risk:high` `depends:[]`
  > After this: python -c "from meanvc_gui.core.engine import get_engine; e=get_engine(); print(e.loaded)" prints True after model load.

- [x] **S04: S04** `risk:medium` `depends:[]`
  > After this: Create 'Trump' profile, upload a 10s wav, watch progress bar, see 'Ready' badge; use it for conversion on Offline page.

- [x] **S05: S05** `risk:medium` `depends:[]`
  > After this: Convert anchor_converted.wav with Trump profile → hear Trump voice in output.

- [x] **S06: S06** `risk:high` `depends:[]`
  > After this: Speak into mic → hear converted voice; waveform animates; RTF label shows < 1.0.

- [x] **S07: S07** `risk:medium` `depends:[]`
  > After this: Compare converted output with original reference → see similarity score > 70%.

- [x] **S08: S08** `risk:low` `depends:[]`
  > After this: Settings page shows green checkmarks next to all 5 model files with file sizes.

- [x] **S09: S09** `risk:low` `depends:[]`
  > After this: Full demo walkthrough: Library → Offline → Analysis → Realtime, all functional.

## Boundary Map

Not provided.
