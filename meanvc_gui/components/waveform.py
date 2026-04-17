"""Waveform visualization using PIL."""

import numpy as np
from PIL import Image, ImageDraw


class WaveformGenerator:
    """Generate waveform visualizations."""

    def __init__(self, width: int = 800, height: int = 100):
        """Initialize generator.

        Args:
            width: Image width
            height: Image height
        """
        self.width = width
        self.height = height

    def generate(self, audio_data: np.ndarray, color: str = "#22d3ee") -> Image.Image:
        """Generate waveform image.

        Args:
            audio_data: Audio samples (normalized -1 to 1)
            color: Waveform color hex

        Returns:
            PIL Image
        """
        # Create image
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        if len(audio_data) == 0:
            return img

        # Downsample to width
        samples = len(audio_data)
        if samples > self.width:
            step = samples // self.width
            audio_data = audio_data[::step]

        # Draw waveform
        mid = self.height // 2
        points = []

        for i, sample in enumerate(audio_data):
            y = int(mid - sample * mid * 0.9)
            points.append((i, y))

        if points:
            draw.line(points, fill=color, width=2)

        return img

    def generate_bar(
        self, audio_data: np.ndarray, color: str = "#22d3ee"
    ) -> Image.Image:
        """Generate bar-style waveform.

        Args:
            audio_data: Audio samples
            color: Bar color hex

        Returns:
            PIL Image
        """
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        if len(audio_data) == 0:
            return img

        # Calculate RMS for each segment
        num_bars = self.width // 4
        segment_size = max(1, len(audio_data) // num_bars)

        for i in range(num_bars):
            start = i * segment_size
            end = min(start + segment_size, len(audio_data))
            if start >= len(audio_data):
                break

            segment = audio_data[start:end]
            rms = np.sqrt(np.mean(segment**2))
            bar_height = int(rms * self.height * 0.9)

            x = i * 4
            y_top = (self.height - bar_height) // 2
            y_bottom = y_top + bar_height

            draw.rectangle([x, y_top, x + 3, y_bottom], fill=color)

        return img
