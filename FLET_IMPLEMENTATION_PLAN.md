# MeanVC Desktop App - Implementation Plan
# Based on Flet Framework

## Project Overview
- **Target:** Desktop-only voice conversion app (Windows/macOS/Linux)
- **Tech Stack:** Python + Flet + flet-audio + PyTorch
- **Device Support:** CUDA / MPS / CPU

---

## Phase 1: Project Setup (Day 1)

### 1.1 Dependencies
```txt
flet>=0.28.0
flet-audio>=0.28.0
torch>=2.0
torchaudio
numpy
sounddevice
Pillow
```

### 1.2 File Structure
```
meanvc_gui/
├── main.py              # Entry point: ft.app()
├── app.py              # Main application class
├── pages/
│   ├── __init__.py
│   ├── library.py     # Profile management
│   ├── realtime.py   # Real-time VC
│   ├── offline.py    # Batch conversion
│   ├── analysis.py   # Speaker similarity
│   └── settings.py  # Config & assets
├── components/
│   ├── __init__.py
│   ├── waveform.py  # Waveform generator
│   ├── theme.py    # Dark theme config
│   └── controls.py # Reusable UI components
├── core/
│   ├── __init__.py
│   ├── engine.py   # MeanVC inference wrapper
│   ├── device.py  # Device detection
│   └── assets.py  # Asset downloader
└── tests/
    ├── test_device.py
    ├── test_engine.py
    └── test_waveform.py
```

---

## Phase 2: Core Infrastructure (Day 1-2)

### 2.1 Theme & Navigation
- Dark theme (matching rvc-web cyan/zinc)
- NavigationRail with 5 destinations
- Device status indicator (bottom of nav)

### 2.2 Device Detection
- Detect CUDA/MPS/CPU availability
- Auto-select best device
- Manual override option

### 2.3 Engine Wrapper
- Load DiT, WavLM, Vocos models
- Offline conversion method
- Real-time streaming method

---

## Phase 3: Page Implementation

### 3.1 Settings Page (Easiest - start here)
| Component | Flet Widget |
|-----------|-------------|
| Device selector | RadioGroup with 3 options |
| Asset list | ListView with status icons |
| Download button | ElevatedButton + ProgressBar |
| About | Text |

### 3.2 Offline Page (Day 2-3)
| Component | Flet Widget |
|-----------|-------------|
| Source file | FilePicker |
| Reference file | FilePicker |
| Model select | Dropdown (200ms/160ms) |
| Steps slider | Slider (1-10) |
| Convert button | ElevatedButton |
| Progress | ProgressBar + status |
| Result audio | Audio (flet-audio) |
| Waveform | Generated PNG as Image |

### 3.3 Analysis Page (Day 3-4)
| Component | Flet Widget |
|-----------|-------------|
| File A/B selectors | FilePicker |
| Analyze button | ElevatedButton |
| Similarity bar | BarChart (native!) |
| Quality labels | Text |
| Comparison chart | LineChart (native!) |
| Metrics table | DataTable |

### 3.4 Library Page (Day 4-5)
| Component | Flet Widget |
|-----------|-------------|
| Profile cards | Container + Column |
| Status badge | Chip |
| Audio list | ListView |
| Add audio | FilePicker |
| Actions | Row of IconButton |

### 3.5 Realtime Page (Most Complex - Day 5-7)
| Component | Flet Widget |
|-----------|-------------|
| Input/Output device | Dropdown |
| Profile select | Dropdown |
| Sliders | Pitch, Index, Protect |
| Noise toggle | Switch |
| Waveforms | Generated Images |
| Start/Stop button | ElevatedButton (toggle) |
| Save toggle | Switch |

---

## Phase 4: Key Technical Solutions

### 4.1 Waveform Generation
- Generate peaks from audio data
- Create PNG using PIL/simple drawing
- Display as ft.Image

### 4.2 Realtime Audio Processing
- sounddevice for mic input
- Background thread processing
- Buffer management with ~50ms chunks

### 4.3 Device Enumeration
- sounddevice.query_devices()
- Input/output separation

---

## Phase 5: Testing Checklist

| Test | Platform | Expected |
|------|----------|----------|
| App launch | Win/Mac/Linux | Opens without error |
| Device detection | All | Shows CUDA/MPS/CPU |
| Offline conversion | All | Produces audio |
| Audio playback | All | Plays via flet-audio |
| Analysis charts | All | Shows bar chart |
| Realtime input | Win/Linux | Captures audio |
| Realtime conversion | Win/Linux | Processes realtime |

---

## Summary Timeline

| Day | Deliverable |
|-----|-------------|
| 1 | Project setup + theme + navigation |
| 2 | Settings page + device detection |
| 3 | Offline page + engine wrapper |
| 4 | Analysis page + charts |
| 5 | Library page |
| 6-7 | Realtime page + testing |

**Total: ~7 days**