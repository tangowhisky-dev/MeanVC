"""
VCRunner — real-time voice conversion QThread.

Ports the run_rt.py inference loop into a Qt-friendly worker.
Audio I/O uses sounddevice with ring buffers; inference runs in this
thread.

Usage:
    runner = VCRunner(
        profile_id="...",
        input_device=None,   # None = system default
        output_device=None,
        steps=1,
        save_path=None,      # set to a .wav path to record output
    )
    runner.chunk_rtf.connect(lambda rtf: print(f"RTF={rtf:.3f}"))
    runner.start()
    ...
    runner.stop()
    runner.wait()
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from collections import deque

import numpy as np
import torch
import torchaudio

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))


class VCRunner(QThread):
    """Real-time voice conversion loop."""

    chunk_rtf   = Signal(float)   # RTF per processed chunk
    status      = Signal(str)     # status/info messages
    error       = Signal(str)     # fatal errors
    underrun     = Signal(int)     # cumulative underrun count

    # Streaming constants (must match run_rt.py)
    _DECODING_CHUNK    = 5
    _NUM_LEFT_CHUNKS   = 2
    _SUBSAMPLING       = 4
    _CONTEXT           = 7
    _SAMPLES_CACHE_LEN = 720
    _VC_KV_CACHE_MAX   = 100
    _VOCODER_OVERLAP   = 3

    def __init__(
        self,
        profile_id: str,
        input_device: int | None = None,
        output_device: int | None = None,
        steps: int = 1,
        save_path: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._profile_id    = profile_id
        self._input_device  = input_device
        self._output_device = output_device
        self._steps         = max(1, min(steps, 2))  # cap at 2 for RT
        self._save_path     = save_path
        self._stop_flag     = False
        self._underruns     = 0

        # Ring buffers
        self._in_buf:  deque[np.ndarray] = deque()
        self._out_buf: deque[np.ndarray] = deque()
        self._lock = threading.Lock()

    def stop(self) -> None:
        """Signal the thread to stop and return."""
        self._stop_flag = True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_ref_path(self) -> str | None:
        """Return the default reference audio path for the profile."""
        if _PROJECT_ROOT not in sys.path:
            sys.path.insert(0, _PROJECT_ROOT)
        from meanvc_gui.core.profile_manager import get_profile_manager
        pm = get_profile_manager()
        ref = pm.get_default_reference(self._profile_id)
        if ref and ref.get("file_path") and os.path.isfile(ref["file_path"]):
            return ref["file_path"]
        return None

    def _extract_fbanks(self, samples: np.ndarray) -> torch.Tensor:
        import torchaudio.compliance.kaldi as kaldi
        wav_scaled = samples * (1 << 15)
        return kaldi.fbank(
            torch.from_numpy(wav_scaled).unsqueeze(0),
            frame_length=25.0,
            frame_shift=10.0,
            snip_edges=True,
            num_mel_bins=80,
            energy_floor=0.0,
            dither=0.0,
            sample_frequency=16000,
        ).unsqueeze(0).float()

    # ------------------------------------------------------------------
    # Main thread
    # ------------------------------------------------------------------

    def run(self) -> None:
        try:
            self._run_inner()
        except Exception as exc:
            logger.exception("[VCRunner] Fatal error")
            self.error.emit(str(exc))

    def _run_inner(self) -> None:
        import sounddevice as sd

        # -- Load models via engine (already loaded if user converted before) --
        from meanvc_gui.core.engine import get_engine
        engine = get_engine()
        if not engine.loaded:
            self.status.emit("Loading models…")
            engine.load()

        models = engine.get_models()
        asr    = models["asr"]
        vc     = models["dit"]   # note: run_rt uses TorchScript 'vc' ≡ engine's 'dit'
        vocos  = models["vocos"]
        sv     = models["sv"]
        mel_fn = models["mel"]
        device = models["device"]

        # Note: run_rt.py loads a TorchScript vc model (meanvc_200ms.pt), while
        # engine.py loads the safetensors DiT.  For realtime we need the
        # TorchScript model because it uses the .forward() signature expected
        # by run_rt's inference_one_chunk (positional vc(x, t_t, r_t, ...)).
        # Load TorchScript separately if not already loaded.
        _vc_pt = os.path.join(_PROJECT_ROOT, "assets", "ckpt", "meanvc_200ms.pt")
        if os.path.isfile(_vc_pt):
            vc_ts = torch.jit.load(_vc_pt, map_location=device)
            vc_ts.eval()
        else:
            # Fallback: use DiT nn.Module (may have signature mismatch — log warning)
            logger.warning("[VCRunner] meanvc_200ms.pt not found; using DiT nn.Module — check call signature")
            vc_ts = vc

        # -- Load reference speaker --
        ref_path = self._get_ref_path()
        if not ref_path:
            self.error.emit("No reference audio found for the selected profile. Add audio in Library first.")
            return

        self.status.emit("Preparing speaker embedding…")
        wav, sr = torchaudio.load(ref_path)
        if wav.shape[0] > 1:
            wav = wav.mean(dim=0, keepdim=True)
        if sr != 16000:
            wav = torchaudio.transforms.Resample(sr, 16000)(wav)
        max_sv = 10 * 16000
        sv_wav = wav[:, :max_sv].to(device)
        with torch.no_grad():
            spk_emb = sv(sv_wav)  # [1, 256]

        max_prompt = 500 * 160
        prompt_wav = wav[:, :max_prompt].to(device)
        with torch.no_grad():
            prompt_mel = mel_fn(prompt_wav).transpose(1, 2)  # [1, T, 80]

        # -- Streaming parameters --
        stride         = self._SUBSAMPLING * self._DECODING_CHUNK
        decoding_window = (self._DECODING_CHUNK - 1) * self._SUBSAMPLING + self._CONTEXT
        req_cache       = self._DECODING_CHUNK * self._NUM_LEFT_CHUNKS
        CHUNK           = 160 * stride  # 3200 samples = 200ms
        vc_chunk        = self._DECODING_CHUNK * 4
        voc_overlap     = self._VOCODER_OVERLAP
        voc_wav_overlap = (voc_overlap - 1) * 160
        down_lin        = torch.linspace(1, 0, voc_wav_overlap).numpy()
        up_lin          = torch.linspace(0, 1, voc_wav_overlap).numpy()

        if self._steps == 1:
            timesteps = torch.tensor([1.0, 0.0])
        else:
            timesteps = torch.tensor([1.0, 0.8, 0.0])

        # Cache state
        samples_cache:   np.ndarray | None = None
        att_cache = torch.zeros((0, 0, 0, 0))
        cnn_cache = torch.zeros((0, 0, 0, 0))
        asr_offset = 0
        enc_cache: torch.Tensor | None = None
        vc_offset  = 0
        vc_cache:  torch.Tensor | None = None
        vc_kv      = None
        voc_cache: torch.Tensor | None = None
        last_wav:  np.ndarray | None = None

        saved_chunks: list[np.ndarray] = []

        # -- Sounddevice I/O callbacks --

        def input_cb(indata, frames, time_info, status):
            if status:
                logger.debug(f"[VCRunner] sd input status: {status}")
            with self._lock:
                self._in_buf.append(indata[:, 0].copy())

        def output_cb(outdata, frames, time_info, status):
            if status:
                self._underruns += 1
                self.underrun.emit(self._underruns)
            with self._lock:
                if self._out_buf:
                    chunk = self._out_buf.popleft()
                    n = min(len(chunk), frames)
                    outdata[:n, 0] = chunk[:n]
                    if n < frames:
                        outdata[n:, 0] = 0
                else:
                    outdata[:, 0] = 0

        in_stream  = sd.InputStream(
            device     = self._input_device,
            channels   = 1,
            samplerate = 16000,
            blocksize  = CHUNK,
            callback   = input_cb,
        )
        out_stream = sd.OutputStream(
            device     = self._output_device,
            channels   = 1,
            samplerate = 16000,
            blocksize  = CHUNK,
            callback   = output_cb,
        )

        self.status.emit("Running…")

        with in_stream, out_stream:
            in_stream.start()
            out_stream.start()

            while not self._stop_flag:
                # Wait for a full chunk in the input buffer
                with self._lock:
                    if not self._in_buf:
                        pass
                    else:
                        samples = self._in_buf.popleft()
                if self._in_buf or len(getattr(self, '_last', b'')) == 0:
                    time.sleep(0.005)
                    continue

                with self._lock:
                    if not self._in_buf:
                        time.sleep(0.005)
                        continue
                    samples = self._in_buf.popleft()

                t0 = time.time()

                with torch.no_grad():
                    # Accumulate context
                    if samples_cache is None:
                        ctx = samples
                    else:
                        ctx = np.concatenate((samples_cache, samples))
                    samples_cache = ctx[-self._SAMPLES_CACHE_LEN:]

                    fbanks = self._extract_fbanks(ctx)

                    enc_out, att_cache, cnn_cache = asr.forward_encoder_chunk(
                        fbanks, asr_offset, req_cache, att_cache, cnn_cache
                    )
                    asr_offset += enc_out.size(1)

                    if enc_cache is None:
                        enc = torch.cat([enc_out[:, 0:1, :], enc_out], dim=1)
                    else:
                        enc = torch.cat([enc_cache, enc_out], dim=1)
                    enc_cache = enc[:, -1:, :]

                    enc_up = enc.transpose(1, 2)
                    enc_up = torch.nn.functional.interpolate(
                        enc_up, size=vc_chunk + 1, mode="linear", align_corners=True
                    ).transpose(1, 2)[:, 1:, :]

                    x = torch.randn(1, enc_up.shape[1], 80, dtype=enc_up.dtype)

                    for i in range(self._steps):
                        t = timesteps[i]
                        r = timesteps[i + 1]
                        t_t = torch.full((1,), t)
                        r_t = torch.full((1,), r)
                        u, vc_kv = vc_ts(
                            x, t_t, r_t,
                            cache=vc_cache, cond=enc_up, spks=spk_emb,
                            prompts=prompt_mel, offset=vc_offset,
                            kv_cache=vc_kv,
                        )
                        x = x - (t - r) * u

                    vc_offset += x.shape[1]
                    vc_cache = x

                    if (
                        vc_offset > 40
                        and vc_kv is not None
                        and vc_kv[0][0].shape[2] > self._VC_KV_CACHE_MAX
                    ):
                        for j in range(len(vc_kv)):
                            vc_kv[j] = (
                                vc_kv[j][0][:, :, -self._VC_KV_CACHE_MAX:, :],
                                vc_kv[j][1][:, :, -self._VC_KV_CACHE_MAX:, :],
                            )

                    mel = x.transpose(1, 2)
                    if voc_cache is not None:
                        mel = torch.cat([voc_cache, mel], dim=-1)
                    voc_cache = mel[:, :, -voc_overlap:]
                    mel = (mel + 1) / 2
                    wav_out = vocos.decode(mel).squeeze()
                    wav_np = wav_out.detach().cpu().numpy()

                    if last_wav is not None:
                        front  = wav_np[:voc_wav_overlap]
                        smooth = last_wav * down_lin + front * up_lin
                        out_chunk = np.concatenate([
                            smooth,
                            wav_np[voc_wav_overlap:-voc_wav_overlap],
                        ])
                    else:
                        out_chunk = wav_np[:-voc_wav_overlap]
                    last_wav = wav_np[-voc_wav_overlap:]

                elapsed = time.time() - t0
                duration = len(out_chunk) / 16000
                rtf = elapsed / max(duration, 1e-6)
                self.chunk_rtf.emit(rtf)

                with self._lock:
                    self._out_buf.append(out_chunk.astype(np.float32))

                if self._save_path:
                    saved_chunks.append(out_chunk)

        # Save recording if requested
        if self._save_path and saved_chunks:
            try:
                all_wav = np.concatenate(saved_chunks)
                import soundfile as sf
                sf.write(self._save_path, all_wav, 16000, subtype="PCM_16")
                logger.info(f"[VCRunner] Saved recording to {self._save_path}")
            except Exception as exc:
                logger.error(f"[VCRunner] Failed to save recording: {exc}")

        self.status.emit("Stopped.")
