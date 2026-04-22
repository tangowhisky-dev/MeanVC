# S06: Realtime Page — Live Mic-to-Speaker Conversion — UAT

**Milestone:** M001
**Written:** 2026-04-22T10:32:02.984Z

## S06 UAT

1. Open Realtime page → profile combo populated, device combos show audio devices
2. Select profile with audio → click Start → status shows 'Running…'
3. Speak into mic → converted voice plays from output device
4. RTF label shows < 1.0 on CUDA/MPS
5. Click Stop → streams terminate cleanly
6. With save-to-file checked → recording.wav created
