# REQUIREMENTS — MeanVC

## Active Requirements

| ID | Class | Description | Why | Source |
|----|-------|-------------|-----|--------|
| R001 | functional | User can create a voice profile by uploading one or more WAV/MP3 reference audio files | Identity of a target speaker must be capturable without training | architecture |
| R002 | functional | Speaker embeddings are extracted and cached on audio upload, not at inference time | WavLM-Large is ~1.3GB; re-running per conversion adds unacceptable latency | architecture |
| R003 | functional | User can convert a source audio file to a target profile (offline inference) | Core use case | architecture |
| R004 | functional | Offline conversion output is saved as WAV PCM file | Lossless, universally compatible | architecture |
| R005 | functional | User can perform real-time voice conversion using microphone input | Streaming VC is a key MeanVC capability | architecture |
| R006 | functional | Real-time conversion works at RTF < 0.8 on CUDA hardware (headroom for processing jitter) | Must sustain real-time without glitches | architecture |
| R007 | functional | User can select input and output audio devices for realtime conversion | Different machines have different device layouts | architecture |
| R008 | functional | Analysis page compares converted output vs reference audio using speaker similarity score | User needs to verify conversion quality | architecture |
| R009 | functional | Profile library shows all profiles with audio count, duration, and embedding status | User needs to manage multiple target voices | architecture |
| R010 | functional | Profile can be exported as a zip archive and imported on another machine | Portability between machines | architecture |
| R011 | functional | App checks for required model assets on startup and shows clear download instructions if missing | Missing assets cause cryptic errors deep in TorchScript | rvc-web lesson |
| R012 | functional | User can download missing assets from within the app (Settings page) | Reduces setup friction | architecture |
| R013 | non-functional | App runs on macOS (MPS), Linux CUDA, Linux CPU without code changes | Cross-platform requirement | architecture |
| R014 | non-functional | Device selection is automatic (CUDA > MPS > CPU) with manual override option | User should not need to configure device for basic use | architecture |
| R015 | non-functional | Model loading happens once at startup (or first use); all subsequent conversions use cached models | User expects near-instant conversion after first load | architecture |
| R016 | non-functional | Background threads handle all inference; Flet event loop never blocked | Flet UI must remain responsive during conversion | architecture |
| R017 | non-functional | Python environment uses uv venv at ~/.meanvc (no conda dependency) | Conda has commercial licensing restrictions | architecture |
| R018 | operational | install.sh / install.bat set up the uv environment and install all dependencies | Reproducible one-command setup | architecture |
| R019 | operational | Per-file load errors during batch conversion are logged with full exception details, not silently swallowed | rvc-web lesson: silent swallow causes "0 results" confusion | rvc-web lesson |
| R020 | functional | Realtime conversion supports steps=1 (fastest) and steps=2 (balanced) selectable by user | RTF budget differs by hardware | architecture |
| R021 | functional | Offline conversion supports steps=1 through steps=10 | Quality vs speed tradeoff for non-realtime use | architecture |
| R022 | functional | Speaker embedding input is capped at 10 seconds to prevent WavLM OOM on long reference files | WavLM-Large O(T²) attention; long files cause OOM | rvc-web lesson |
| R023 | non-functional | aarch64 Linux (DGX Spark) is a supported platform | Primary development hardware | architecture |

## Deferred

| ID | Class | Description | Why Deferred |
|----|-------|-------------|--------------|
| R024 | functional | Per-profile fine-tuning / adapter training | Not supported by base MeanVC architecture; future work |
| R025 | functional | UTMOS MOS quality scoring in analysis page | ECAPA similarity is sufficient for v1; UTMOS adds complexity |
| R026 | functional | Batch export of multiple profiles | Nice-to-have; single profile export covers primary use case |
