# ECAPA-TDNN Speaker Verification Model
# Replaces s3prl torch.hub with HuggingFace transformers for feature extraction.
# Part of the code is borrowed from https://github.com/lawlict/ECAPA-TDNN

import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchaudio.transforms as trans

# ── Feature extractor backends ──────────────────────────────────────────────

# Map of feat_type → HuggingFace model repo ID (used when config_path is None)
_TRANSFORMERS_BACKENDS = {
    "wavlm_large":        "microsoft/wavlm-large",
    "wavlm_base_plus":    "microsoft/wavlm-base-plus",
    "hubert_large_ll60k": "facebook/hubert-large-ll60k",
    "hubert_base":        "facebook/hubert-base-ls960",
    "wav2vec2_xlsr":      "facebook/wav2vec2-xls-r-300m",
    "wav2vec2_large":     "facebook/wav2vec2-large",
    "unispeech_sat":      "microsoft/unispeech-large-1500h-cv",
}


class _TransformerFeatureExtractor:
    """Wraps a HuggingFace transformer model to match the s3prl calling convention.

    The s3prl interface expects::

        features = model([wav1, wav2, ...])        # list of 1-D tensors
        return features["hidden_states"]            # list/tuple of per-layer tensors

    This wrapper provides the same API using ``transformers``.
    """

    def __init__(self, model_name_or_path: str):
        from transformers import AutoModel, AutoFeatureExtractor
        self.processor = AutoFeatureExtractor.from_pretrained(model_name_or_path)
        self.model = AutoModel.from_pretrained(model_name_or_path, output_hidden_states=True)
        self.model.eval()

        # Expose encoder layers for fp32_attention checks (legacy s3prl compat)
        self.encoder = self.model
        # Most HF models expose layers via model.encoder.layers or model.layers
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
                 feat_type='fbank', sr=16000, feature_selection="hidden_states", update_extract=False, config_path=None):
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
            # Uses HuggingFace transformers instead of s3prl torch.hub
            if config_path is None:
                repo_id = _TRANSFORMERS_BACKENDS.get(feat_type, "microsoft/wavlm-large")
                self.feature_extract = _TransformerFeatureExtractor(repo_id)
            else:
                # Legacy path for custom fairseq checkpoints — not implemented with transformers
                raise NotImplementedError(
                    "Loading a custom fairseq checkpoint via config_path is no longer supported. "
                    "Use a HuggingFace model repo ID as feat_type instead."
                )

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


def ECAPA_TDNN_SMALL(feat_dim, emb_dim=256, feat_type='fbank', sr=16000, feature_selection="hidden_states", update_extract=False, config_path=None):
    return ECAPA_TDNN(feat_dim=feat_dim, channels=512, emb_dim=emb_dim,
                      feat_type=feat_type, sr=sr, feature_selection=feature_selection, update_extract=update_extract, config_path=config_path)


if __name__ == '__main__':
    x = torch.zeros(2, 32000)
    model = ECAPA_TDNN_SMALL(feat_dim=768, emb_dim=256, feat_type='wavlm_base_plus', feature_selection="hidden_states",
                              update_extract=False)
    out = model(x)
    print(out.shape)
