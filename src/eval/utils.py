"""UpstreamExpert wrapper — deprecated.

s3prl-based feature extraction has been replaced by HuggingFace transformers.
This file is kept only for backward compatibility with any code that imports it.
Calling UpstreamExpert will now raise a clear error message.
"""


class UpstreamExpert:
    """Previously wrapped fairseq/s3prl upstream models.

    This class has been removed because MeanVC now uses HuggingFace
    ``transformers`` (WavLM, HuBERT, etc.) via the
    ``_TransformerFeatureExtractor`` in ``ecapa_tdnn.py``.

    If you need to load a custom checkpoint, consider converting it to a
    HuggingFace-compatible format and using the ``feat_type`` parameter of
    ``ECAPA_TDNN`` / ``ECAPA_TDNN_SMALL`` instead.
    """

    def __init__(self, ckpt, **kwargs):
        raise NotImplementedError(
            "UpstreamExpert (s3prl/fairseq backend) has been removed. "
            "MeanVC now uses HuggingFace transformers for self-supervised "
            "speech models (WavLM, HuBERT, etc.). See ecapa_tdnn.py for details."
        )
