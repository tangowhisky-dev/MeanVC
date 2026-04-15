
import sys, time; sys.path.insert(0, '.')
import torch, json
from src.utils.audio import get_device, MelSpectrogramFeatures
from src.infer.dit_kvcache import DiT
from src.model.utils import load_checkpoint
from src.runtime.speaker_verification.verification import init_model

device = get_device()
print('Device:', device)

# DiT — safetensors, weights_only via safetensors lib
with open('src/config/config_200ms.json') as f: cfg = json.load(f)
dit = DiT(**cfg['model'])
dit = load_checkpoint(dit, 'assets/ckpt/model_200ms.safetensors', device, use_ema=False)
dit = dit.float().eval()
print(f'DiT OK  ({sum(p.numel() for p in dit.parameters()):,} params)')

# TorchScript models — torch.jit.load only
vocos = torch.jit.load('assets/ckpt/vocos.pt', map_location=device).eval()
print('Vocos OK')
asr = torch.jit.load('assets/ckpt/fastu2++.pt', map_location=device).eval()
print('ASR OK')

# WavLM — plain state-dict, weights_only=True
sv = init_model('wavlm_large', 'assets/wavLM/wavlm_large_finetune.pth')
sv = sv.to(device).eval()
print('WavLM SV OK')

# Quick tensor-level smoke tests
with torch.no_grad():
    wav = torch.randn(1, 16000).to(device)
    emb = sv(wav)
    print(f'  SV emb: {emb.shape}  NaN={emb.isnan().sum().item()}')
    mel_ext = MelSpectrogramFeatures().to(device)
    mel = mel_ext(wav)
    print(f'  Mel: {mel.shape}  NaN={mel.isnan().sum().item()}')
    wav_out = vocos.decode(torch.rand(1,80,125,device=device)*0.5+0.25)
    print(f'  Vocos out: {wav_out.shape}  NaN={wav_out.isnan().sum().item()}')

print('All models OK')