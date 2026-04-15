# ECAPA-TDNN Speaker Verification Model
# Feature extraction uses the original Microsoft WavLM implementation (same
# codebase as s3prl) so that wavlm_large_finetune.pth loads without any key
# remapping.  The checkpoint was trained with s3prl's UpstreamExpert wrapper
# which calls WavLMConfig(checkpoint["cfg"]) + WavLM(cfg).
# Part of the code is borrowed from https://github.com/lawlict/ECAPA-TDNN

import os
import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchaudio.transforms as trans

# ── Feature extractor backends ──────────────────────────────────────────────

# WavLM checkpoints trained via s3prl embed a "cfg" dict inside the .pt file
# that was passed to WavLMConfig().  wavlm_large_finetune.pth was fine-tuned
# from such a checkpoint but only saved the model weights ("model" key) and
# "best_valid_eer" — no "cfg".  We must reconstruct the config explicitly.
#
# These are the exact WavLM-Large training config values (from
# https://github.com/microsoft/unilm/tree/master/wavlm and confirmed by
# cross-checking key/shape alignment with the checkpoint):
_WAVLM_LARGE_CFG = {
    "extractor_mode": "layer_norm",
    "encoder_layers": 24,
    "encoder_embed_dim": 1024,
    "encoder_ffn_embed_dim": 4096,
    "encoder_attention_heads": 16,
    "layer_norm_first": True,
    "conv_feature_layers": "[(512,10,5)] + [(512,3,2)] * 4 + [(512,2,2)] * 2",
    "conv_bias": False,
    "feature_grad_mult": 1.0,
    "normalize": True,
    "relative_position_embedding": True,
    "num_buckets": 320,
    "max_distance": 1280,
    "gru_rel_pos": True,
}
_WAVLM_BASE_PLUS_CFG = {
    "extractor_mode": "default",
    "encoder_layers": 12,
    "encoder_embed_dim": 768,
    "encoder_ffn_embed_dim": 3072,
    "encoder_attention_heads": 12,
    "layer_norm_first": False,
    "conv_feature_layers": "[(512,10,5)] + [(512,3,2)] * 4 + [(512,2,2)] * 2",
    "conv_bias": False,
    "feature_grad_mult": 1.0,
    "normalize": False,
    "relative_position_embedding": True,
    "num_buckets": 320,
    "max_distance": 800,
    "gru_rel_pos": False,
}
_MICROSOFT_WAVLM_CONFIGS = {
    "wavlm_large":     _WAVLM_LARGE_CFG,
    "wavlm_base_plus": _WAVLM_BASE_PLUS_CFG,
}

# Other SSL models — resolved via HuggingFace transformers
_TRANSFORMERS_BACKENDS = {
    "hubert_large_ll60k": "facebook/hubert-large-ll60k",
    "hubert_base":        "facebook/hubert-base-ls960",
    "wav2vec2_xlsr":      "facebook/wav2vec2-xls-r-300m",
    "wav2vec2_large":     "facebook/wav2vec2-large",
    "unispeech_sat":      "microsoft/unispeech-large-1500h-cv",
}

# Path to bundled WavLM.py — same file as s3prl uses, copied to assets/wavLM/
_WAVLM_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))),
    "src", "wavLM",
)
_WAVLM_PY = os.path.join(_WAVLM_DIR, "WavLM.py")


def _import_wavlm_module():
    """Import src/wavLM/WavLM.py without polluting sys.modules permanently.

    WavLM.py uses bare ``from modules import ...`` which requires its directory
    to be on sys.path.  We add it temporarily and remove it after import.
    """
    import importlib.util
    already = _WAVLM_DIR in sys.path
    if not already:
        sys.path.insert(0, _WAVLM_DIR)
    try:
        # Use a unique module name to avoid colliding with any installed 'WavLM'
        spec = importlib.util.spec_from_file_location("_wavlm_microsoft", _WAVLM_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        if not already:
            sys.path.remove(_WAVLM_DIR)
    return mod


def _build_microsoft_wavlm(feat_type: str):
    """Build a Microsoft WavLM model with empty weights.

    Mirrors what s3prl's UpstreamExpert does:
        cfg = WavLMConfig(checkpoint["cfg"])
        model = WavLM(cfg)
        model.load_state_dict(checkpoint["model"])

    Since wavlm_large_finetune.pth has no "cfg" key, we reconstruct the
    config from the known WavLM-Large training values, confirmed to produce
    488/488 key alignment with the checkpoint.
    """
    wm = _import_wavlm_module()
    cfg = wm.WavLMConfig(_MICROSOFT_WAVLM_CONFIGS[feat_type])
    model = wm.WavLM(cfg)
    model.feature_grad_mult = 0.0   # disable feature extractor gradients at inference
    model.encoder.layerdrop = 0.0   # disable layer drop at inference
    # Do NOT remove_weight_norm from pos_conv — the fine-tune checkpoint was
    # saved with weight_norm still active (stores weight_g / weight_v).
    # Keeping weight_norm here means load_state_dict matches those keys exactly.
    model.eval()
    return model


class _MicrosoftWavLMExtractor(nn.Module):
    """Wraps Microsoft's WavLM as a proper nn.Module.

    Being an nn.Module means .to(device), .parameters(), .named_parameters(),
    and .state_dict() all work through PyTorch's standard module tree — so
    ECAPA_TDNN.to(device) automatically moves the WavLM backbone too.

    s3prl's UpstreamExpert registers forward hooks on each encoder layer
    (capturing input[0].transpose(0,1) — layer input in B,T,D order) and one
    hook on the full encoder (capturing output[0] — final x).  We replicate
    that with register_forward_hook so no UpstreamBase machinery is needed.
    """

    def __init__(self, feat_type: str):
        super().__init__()
        self.wavlm = _build_microsoft_wavlm(feat_type)  # registered as submodule
        self.cfg = self.wavlm.cfg
        # encoder is exposed as a plain attribute (not a registered submodule)
        # so fp32_attention checks in ECAPA_TDNN.__init__ can reach it, but
        # PyTorch's module tree doesn't double-register it under 'encoder'
        # alongside 'wavlm' — which would create duplicate state_dict keys.
        object.__setattr__(self, 'encoder', self.wavlm.encoder)
        self._hidden: list = []

        # Hook each encoder layer: capture layer input (T,B,D) → (B,T,D)
        for layer in self.wavlm.encoder.layers:
            layer.register_forward_hook(
                lambda m, inp, out: self._hidden.append(inp[0].transpose(0, 1))
            )
        # Hook full encoder: capture final output x (B,T,D)
        self.wavlm.encoder.register_forward_hook(
            lambda m, inp, out: self._hidden.append(out[0])
        )

    def forward(self, wavs: list):
        """Forward pass — mirrors s3prl UpstreamExpert.forward() exactly."""
        from torch.nn.utils.rnn import pad_sequence

        # Each wav is a 1-D tensor (T,) — same as s3prl convention
        device = wavs[0].device

        if self.cfg.normalize:
            wavs = [F.layer_norm(w, w.shape) for w in wavs]

        wav_lengths = torch.LongTensor([len(w) for w in wavs]).to(device)
        padding_mask = ~torch.lt(
            torch.arange(max(wav_lengths)).unsqueeze(0).to(device),
            wav_lengths.unsqueeze(1),
        )
        padded = pad_sequence(wavs, batch_first=True)

        self._hidden.clear()
        self.wavlm.extract_features(padded, padding_mask=padding_mask, mask=False)

        # _hidden: 24 layer inputs (B,T,D) + 1 final encoder output (B,T,D) = 25
        hidden_states = tuple(self._hidden)
        self._hidden.clear()
        return {"hidden_states": hidden_states}


class _TransformerFeatureExtractor:
    """Wraps a HuggingFace transformer model to match the s3prl calling convention.

    Used for non-WavLM SSL models (HuBERT, wav2vec2, UniSpeech-SAT).
    The backbone is constructed from config only (no weight download) because
    weights come from the fine-tuned ECAPA checkpoint.
    """

    def __init__(self, model_name_or_path: str):
        from transformers import AutoModel, AutoConfig, AutoFeatureExtractor
        self.processor = AutoFeatureExtractor.from_pretrained(model_name_or_path)
        config = AutoConfig.from_pretrained(model_name_or_path)
        config.output_hidden_states = True
        self.model = AutoModel.from_config(config)
        self.model.eval()

        # Expose encoder layers for fp32_attention checks (legacy s3prl compat)
        self.encoder = self.model
        if hasattr(self.model, "encoder") and hasattr(self.model.encoder, "layers"):
            self.encoder = self.model.encoder

    def __call__(self, wavs: list[torch.Tensor]):
        """Forward pass matching the s3prl signature."""
        device = wavs[0].device
        # HF processor expects numpy; convert each wav
        all_hidden_states = []
        for wav in wavs:
            wav_np = wav.cpu().numpy()
            inputs = self.processor(
                wav_np,
                sampling_rate=16000,
                return_tensors="pt",
                padding=True,
            )
            # Move input tensors to the original device
            input_values = inputs["input_values"].to(device)
            with torch.no_grad():
                outputs = self.model(input_values)
            # outputs.hidden_states: tuple of (embedding + N layer states)
            # Skip the embedding layer (index 0), return only transformer layers
            layer_states = outputs.hidden_states[1:]  # tuple of tensors
            all_hidden_states.append(layer_states)

        # If batch size == 1, return as s3prl does (single sample list)
        if len(wavs) == 1:
            return {"hidden_states": all_hidden_states[0]}

        # Stack per-sample layer outputs: [num_layers, batch, time, dim]
        num_layers = len(all_hidden_states[0])
        stacked = []
        for layer_idx in range(num_layers):
            # Stack across samples: [batch, time, dim]
            layer_tensor = torch.stack(
                [all_hidden_states[s][layer_idx].squeeze(0) for s in range(len(wavs))],
                dim=0,
            )
            stacked.append(layer_tensor)
        return {"hidden_states": stacked}

    def named_parameters(self):
        return self.model.named_parameters()

    def parameters(self):
        return self.model.parameters()

    def to(self, device):
        self.model.to(device)
        return self

    def eval(self):
        self.model.eval()
        return self

    def state_dict(self):
        return self.model.state_dict()


# ── ECAPA-TDNN architecture ─────────────────────────────────────────────────


class Res2Conv1dReluBn(nn.Module):
    '''
    in_channels == out_channels == channels
    '''

    def __init__(self, channels, kernel_size=1, stride=1, padding=0, dilation=1, bias=True, scale=4):
        super().__init__()
        assert channels % scale == 0, "{} % {} != 0".format(channels, scale)
        self.scale = scale
        self.width = channels // scale
        self.nums = scale if scale == 1 else scale - 1

        self.convs = []
        self.bns = []
        for i in range(self.nums):
            self.convs.append(nn.Conv1d(self.width, self.width, kernel_size, stride, padding, dilation, bias=bias))
            self.bns.append(nn.BatchNorm1d(self.width))
        self.convs = nn.ModuleList(self.convs)
        self.bns = nn.ModuleList(self.bns)

    def forward(self, x):
        out = []
        spx = torch.split(x, self.width, 1)
        for i in range(self.nums):
            if i == 0:
                sp = spx[i]
            else:
                sp = sp + spx[i]
            # Order: conv -> relu -> bn
            sp = self.convs[i](sp)
            sp = self.bns[i](F.relu(sp))
            out.append(sp)
        if self.scale != 1:
            out.append(spx[self.nums])
        out = torch.cat(out, dim=1)

        return out


class Conv1dReluBn(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=1, stride=1, padding=0, dilation=1, bias=True):
        super().__init__()
        self.conv = nn.Conv1d(in_channels, out_channels, kernel_size, stride, padding, dilation, bias=bias)
        self.bn = nn.BatchNorm1d(out_channels)

    def forward(self, x):
        return self.bn(F.relu(self.conv(x)))


class SE_Connect(nn.Module):
    def __init__(self, channels, se_bottleneck_dim=128):
        super().__init__()
        self.linear1 = nn.Linear(channels, se_bottleneck_dim)
        self.linear2 = nn.Linear(se_bottleneck_dim, channels)

    def forward(self, x):
        out = x.mean(dim=2)
        out = F.relu(self.linear1(out))
        out = torch.sigmoid(self.linear2(out))
        out = x * out.unsqueeze(2)

        return out


class SE_Res2Block(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride, padding, dilation, scale, se_bottleneck_dim):
        super().__init__()
        self.Conv1dReluBn1 = Conv1dReluBn(in_channels, out_channels, kernel_size=1, stride=1, padding=0)
        self.Res2Conv1dReluBn = Res2Conv1dReluBn(out_channels, kernel_size, stride, padding, dilation, scale=scale)
        self.Conv1dReluBn2 = Conv1dReluBn(out_channels, out_channels, kernel_size=1, stride=1, padding=0)
        self.SE_Connect = SE_Connect(out_channels, se_bottleneck_dim)

        self.shortcut = None
        if in_channels != out_channels:
            self.shortcut = nn.Conv1d(
                in_channels=in_channels,
                out_channels=out_channels,
                kernel_size=1,
            )

    def forward(self, x):
        residual = x
        if self.shortcut:
            residual = self.shortcut(x)

        x = self.Conv1dReluBn1(x)
        x = self.Res2Conv1dReluBn(x)
        x = self.Conv1dReluBn2(x)
        x = self.SE_Connect(x)

        return x + residual


class AAMSoftmax(nn.Module):
    """Additive Angular Margin Softmax loss head for speaker verification training.

    Stores weights as ``self.projection`` (shape ``[num_class, emb_dim]``) to
    match the key name used in wavlm_large_finetune.pth:
    ``loss_calculator.projection.weight``.

    Usage during training::

        loss = model.loss_calculator(embeddings, speaker_labels)

    Not called during inference — ``ECAPA_TDNN.forward`` returns raw embeddings.
    """

    def __init__(self, emb_dim: int, num_class: int, scale: float = 15.0, margin: float = 0.3,
                 easy_margin: bool = False):
        import math
        super().__init__()
        self.scale = scale
        self.margin = margin
        self.num_class = num_class
        self.projection = nn.Linear(emb_dim, num_class, bias=False)
        nn.init.xavier_normal_(self.projection.weight, gain=1)
        self.ce = nn.CrossEntropyLoss()
        self.easy_margin = easy_margin
        self.cos_m = math.cos(margin)
        self.sin_m = math.sin(margin)
        self.th = math.cos(math.pi - margin)
        self.mm = math.sin(math.pi - margin) * margin

    def forward(self, x: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x:      Speaker embeddings (B, emb_dim) — raw output of ECAPA linear layer.
            labels: Speaker class indices (B,) in [0, num_class).
        Returns:
            AAM-softmax loss scalar.
        """
        assert x.shape[0] == labels.shape[0]
        cosine = F.linear(F.normalize(x), F.normalize(self.projection.weight))
        sine = torch.sqrt((1.0 - cosine.pow(2)).clamp(0, 1))
        phi = cosine * self.cos_m - sine * self.sin_m
        if self.easy_margin:
            phi = torch.where(cosine > 0, phi, cosine)
        else:
            phi = torch.where((cosine - self.th) > 0, phi, cosine - self.mm)
        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, labels.view(-1, 1), 1)
        output = (one_hot * phi) + ((1.0 - one_hot) * cosine)
        output = output * self.scale
        return self.ce(output, labels)


class AttentiveStatsPool(nn.Module):
    def __init__(self, in_dim, attention_channels=128, global_context_att=False):
        super().__init__()
        self.global_context_att = global_context_att

        if global_context_att:
            self.linear1 = nn.Conv1d(in_dim * 3, attention_channels, kernel_size=1)
        else:
            self.linear1 = nn.Conv1d(in_dim, attention_channels, kernel_size=1)
        self.linear2 = nn.Conv1d(attention_channels, in_dim, kernel_size=1)

    def forward(self, x):
        if self.global_context_att:
            context_mean = torch.mean(x, dim=-1, keepdim=True).expand_as(x)
            context_std = torch.sqrt(torch.var(x, dim=-1, keepdim=True) + 1e-10).expand_as(x)
            x_in = torch.cat((x, context_mean, context_std), dim=1)
        else:
            x_in = x

        alpha = torch.tanh(self.linear1(x_in))
        alpha = torch.softmax(self.linear2(alpha), dim=2)
        mean = torch.sum(alpha * x, dim=2)
        residuals = torch.sum(alpha * (x ** 2), dim=2) - mean ** 2
        std = torch.sqrt(residuals.clamp(min=1e-9))
        return torch.cat([mean, std], dim=1)


class ECAPA_TDNN(nn.Module):
    def __init__(self, feat_dim=80, channels=512, emb_dim=192, global_context_att=False,
                 feat_type='fbank', sr=16000, feature_selection="hidden_states", update_extract=False,
                 config_path=None, num_class: int = 0):
        super().__init__()

        self.feat_type = feat_type
        self.feature_selection = feature_selection
        self.update_extract = update_extract
        self.sr = sr

        if feat_type == "fbank" or feat_type == "mfcc":
            self.update_extract = False

        win_len = int(sr * 0.025)
        hop_len = int(sr * 0.01)

        if feat_type == 'fbank':
            self.feature_extract = trans.MelSpectrogram(sample_rate=sr, n_fft=512, win_length=win_len,
                                                        hop_length=hop_len, f_min=0.0, f_max=sr // 2,
                                                        pad=0, n_mels=feat_dim)
        elif feat_type == 'mfcc':
            melkwargs = {
                'n_fft': 512,
                'win_length': win_len,
                'hop_length': hop_len,
                'f_min': 0.0,
                'f_max': sr // 2,
                'pad': 0
            }
            self.feature_extract = trans.MFCC(sample_rate=sr, n_mfcc=feat_dim, log_mels=False,
                                              melkwargs=melkwargs)
        else:
            # Self-supervised speech model (WavLM, HuBERT, etc.)
            if config_path is not None:
                raise NotImplementedError(
                    "Loading a custom fairseq checkpoint via config_path is no longer supported."
                )
            if feat_type in _MICROSOFT_WAVLM_CONFIGS:
                # Use the original Microsoft WavLM implementation — required for
                # checkpoints trained against that codebase (e.g. wavlm_large_finetune.pth).
                # The key schema (self_attn, fc1, grep_a, …) differs from HuggingFace's
                # WavLMModel and is not interchangeable.
                self.feature_extract = _MicrosoftWavLMExtractor(feat_type)
            else:
                repo_id = _TRANSFORMERS_BACKENDS.get(feat_type)
                if repo_id is None:
                    raise ValueError(
                        f"Unknown feat_type '{feat_type}'. "
                        f"Supported: {sorted(list(_MICROSOFT_WAVLM_CONFIGS) + list(_TRANSFORMERS_BACKENDS))}"
                    )
                self.feature_extract = _TransformerFeatureExtractor(repo_id)

            # Disable fp32_attention for large models (legacy s3prl compat — no-op for transformers)
            encoder_layers = getattr(self.feature_extract.encoder, "layers", None)
            if encoder_layers is not None and len(encoder_layers) == 24:
                for layer in encoder_layers:
                    if hasattr(layer, "self_attn") and hasattr(layer.self_attn, "fp32_attention"):
                        layer.self_attn.fp32_attention = False

            self.feat_num = self.get_feat_num()
            self.feature_weight = nn.Parameter(torch.zeros(self.feat_num))

        if feat_type != 'fbank' and feat_type != 'mfcc':
            freeze_list = ['final_proj', 'label_embs_concat', 'mask_emb', 'project_q', 'quantizer']
            for name, param in self.feature_extract.named_parameters():
                for freeze_val in freeze_list:
                    if freeze_val in name:
                        param.requires_grad = False
                        break

        if not self.update_extract:
            for param in self.feature_extract.parameters():
                param.requires_grad = False

        self.instance_norm = nn.InstanceNorm1d(feat_dim)
        self.channels = [channels] * 4 + [1536]

        self.layer1 = Conv1dReluBn(feat_dim, self.channels[0], kernel_size=5, padding=2)
        self.layer2 = SE_Res2Block(self.channels[0], self.channels[1], kernel_size=3, stride=1, padding=2, dilation=2, scale=8, se_bottleneck_dim=128)
        self.layer3 = SE_Res2Block(self.channels[1], self.channels[2], kernel_size=3, stride=1, padding=3, dilation=3, scale=8, se_bottleneck_dim=128)
        self.layer4 = SE_Res2Block(self.channels[2], self.channels[3], kernel_size=3, stride=1, padding=4, dilation=4, scale=8, se_bottleneck_dim=128)

        cat_channels = channels * 3
        self.conv = nn.Conv1d(cat_channels, self.channels[-1], kernel_size=1)
        self.pooling = AttentiveStatsPool(self.channels[-1], attention_channels=128, global_context_att=global_context_att)
        self.bn = nn.BatchNorm1d(self.channels[-1] * 2)
        self.linear = nn.Linear(self.channels[-1] * 2, emb_dim)

        # Training loss head — AAM-softmax over num_class speaker classes.
        # Named `loss_calculator` to match the key in wavlm_large_finetune.pth
        # (loss_calculator.projection.weight, shape [num_class, emb_dim]).
        # Not used during inference; only called when training with speaker labels.
        # Set num_class=0 (default) to omit it — e.g. for inference-only models.
        if num_class > 0:
            self.loss_calculator = AAMSoftmax(emb_dim=emb_dim, num_class=num_class)
        else:
            self.loss_calculator = None

    def get_feat_num(self):
        self.feature_extract.eval()
        wav = [torch.randn(self.sr).to(next(self.feature_extract.parameters()).device)]
        with torch.no_grad():
            features = self.feature_extract(wav)
        select_feature = features[self.feature_selection]
        if isinstance(select_feature, (list, tuple)):
            return len(select_feature)
        else:
            return 1

    def get_feat(self, x):
        if self.update_extract:
            x = self.feature_extract([sample for sample in x])
        else:
            with torch.no_grad():
                if self.feat_type == 'fbank' or self.feat_type == 'mfcc':
                    x = self.feature_extract(x) + 1e-6
                else:
                    x = self.feature_extract([sample for sample in x])

        if self.feat_type == 'fbank':
            x = x.log()

        if self.feat_type != "fbank" and self.feat_type != "mfcc":
            x = x[self.feature_selection]
            if isinstance(x, (list, tuple)):
                x = torch.stack(x, dim=0)
            else:
                x = x.unsqueeze(0)
            norm_weights = F.softmax(self.feature_weight, dim=-1).unsqueeze(-1).unsqueeze(-1).unsqueeze(-1)
            x = (norm_weights * x).sum(dim=0)
            x = torch.transpose(x, 1, 2) + 1e-6

        x = self.instance_norm(x)
        return x

    def forward(self, x):
        x = self.get_feat(x)

        out1 = self.layer1(x)
        out2 = self.layer2(out1)
        out3 = self.layer3(out2)
        out4 = self.layer4(out3)

        out = torch.cat([out2, out3, out4], dim=1)
        out = F.relu(self.conv(out))
        out = self.bn(self.pooling(out))
        out = self.linear(out)

        return out


def ECAPA_TDNN_SMALL(feat_dim, emb_dim=256, feat_type='fbank', sr=16000,
                     feature_selection="hidden_states", update_extract=False,
                     config_path=None, num_class: int = 0):
    return ECAPA_TDNN(feat_dim=feat_dim, channels=512, emb_dim=emb_dim,
                      feat_type=feat_type, sr=sr, feature_selection=feature_selection,
                      update_extract=update_extract, config_path=config_path,
                      num_class=num_class)


if __name__ == '__main__':
    x = torch.zeros(2, 32000)
    model = ECAPA_TDNN_SMALL(feat_dim=768, emb_dim=256, feat_type='wavlm_base_plus', feature_selection="hidden_states",
                              update_extract=False)
    out = model(x)
    print(out.shape)
