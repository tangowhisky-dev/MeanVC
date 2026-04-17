"""Core device detection for MeanVC."""

import os
import torch


def get_current_device():
    """Detect the best available compute device.

    Returns:
        str: Device name ('cuda', 'mps', 'cpu')
    """
    # Check environment variable first
    if env_device := os.environ.get("MEANVC_DEVICE"):
        return env_device

    # Check CUDA
    if torch.cuda.is_available():
        return "cuda"

    # Check MPS (Apple Silicon)
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"

    return "cpu"


def get_device_info():
    """Get detailed device information.

    Returns:
        dict: Device info including name, capability, memory
    """
    device = get_current_device()
    info = {"device": device, "name": device.upper()}

    if device == "cuda":
        info["name"] = f"CUDA ({torch.cuda.get_device_name(0)})"
        info["memory"] = torch.cuda.get_device_properties(0).total_memory / 1e9
    elif device == "mps":
        info["name"] = "Apple MPS"
        info["memory"] = "Unknown"
    else:
        info["name"] = "CPU"
        info["memory"] = "Unknown"

    return info


def enumerate_audio_devices():
    """Enumerate available audio input/output devices.

    Returns:
        dict: Lists of input and output devices
    """
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        inputs = []
        outputs = []

        for i, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                inputs.append((i, dev["name"]))
            if dev["max_output_channels"] > 0:
                outputs.append((i, dev["name"]))

        return {"inputs": inputs, "outputs": outputs}
    except Exception:
        return {"inputs": [], "outputs": []}
