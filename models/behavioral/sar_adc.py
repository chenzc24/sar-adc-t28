"""Bit-accurate ideal model for the project SAR ADC.

The ideal transfer of a 5+5 split CDAC is identical to a binary 10-bit DAC.
Physical bridge-capacitor error, parasitics, switching trajectories, and
settling belong to the later CDAC model and are deliberately absent here.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from adctoolbox import sar_convert, sar_ideal_weights, sar_reconstruct


@dataclass(frozen=True)
class SarAdcModel:
    """Ideal fully differential SAR quantizer with explicit bit decisions."""

    resolution_bits: int
    differential_range_v: tuple[float, float]

    def __post_init__(self) -> None:
        v_min, v_max = self.differential_range_v
        if self.resolution_bits <= 0:
            raise ValueError("resolution_bits must be positive")
        if not np.isfinite(v_min) or not np.isfinite(v_max) or v_max <= v_min:
            raise ValueError("differential_range_v must be finite and increasing")

    @property
    def code_count(self) -> int:
        return 1 << self.resolution_bits

    @property
    def full_scale_span_v(self) -> float:
        return self.differential_range_v[1] - self.differential_range_v[0]

    @property
    def lsb_v(self) -> float:
        return self.full_scale_span_v / self.code_count

    @property
    def ideal_weights(self) -> np.ndarray:
        return sar_ideal_weights(self.resolution_bits)

    def convert(
        self,
        vin_diff_v,
        *,
        analog_weights: np.ndarray | None = None,
        sampling_noise_rms_v: float = 0.0,
        comparator_noise_rms_v: float = 0.0,
        rng: np.random.Generator | None = None,
    ) -> np.ndarray:
        """Return raw MSB-first decisions with shape ``vin.shape + (N,)``."""

        weights = self.ideal_weights if analog_weights is None else np.asarray(analog_weights)
        if weights.shape != (self.resolution_bits,):
            raise ValueError(
                f"analog_weights must have shape ({self.resolution_bits},), got {weights.shape}"
            )
        return sar_convert(
            vin_diff_v,
            weights,
            quant_range=self.differential_range_v,
            sampling_noise_rms=sampling_noise_rms_v,
            comparator_noise_rms=comparator_noise_rms_v,
            rng=rng,
        )

    def reconstruct(
        self,
        bits,
        *,
        digital_weights: np.ndarray | None = None,
    ) -> np.ndarray:
        """Reconstruct the differential voltage represented by raw decisions."""

        weights = self.ideal_weights if digital_weights is None else np.asarray(digital_weights)
        if weights.shape != (self.resolution_bits,):
            raise ValueError(
                f"digital_weights must have shape ({self.resolution_bits},), got {weights.shape}"
            )
        return sar_reconstruct(bits, weights, quant_range=self.differential_range_v)

    def unsigned_codes(self, bits) -> np.ndarray:
        """Pack an MSB-first decision matrix into unsigned integer codes."""

        bits_array = np.asarray(bits)
        if bits_array.ndim < 1 or bits_array.shape[-1] != self.resolution_bits:
            raise ValueError(
                f"bits must end with an axis of length {self.resolution_bits}, "
                f"got {bits_array.shape}"
            )
        if not np.all((bits_array == 0) | (bits_array == 1)):
            raise ValueError("bits must contain only 0 or 1")
        powers = 1 << np.arange(self.resolution_bits - 1, -1, -1, dtype=np.int64)
        return bits_array.astype(np.int64) @ powers
