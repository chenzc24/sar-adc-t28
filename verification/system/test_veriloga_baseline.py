"""Focused source and waveform checks for the Verilog-A SAR baseline."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models.behavioral.sar_adc import SarAdcModel
from scripts.analysis.run_veriloga_baseline import (
    FIRST_SAMPLE_CROSSING_S,
    _valid_samples,
    analyze_dynamic,
    analyze_static,
)


class VerilogABaselineTest(unittest.TestCase):
    @staticmethod
    def _write_code_csv(path: Path, codes: np.ndarray) -> None:
        row_count = len(codes) * 3
        names = ["time", "valid", *(f"dout_{bit}" for bit in range(10))]
        matrix = np.zeros((row_count, len(names)), dtype=float)
        for index, code in enumerate(codes):
            row = index * 3
            base_time = index * 1e-9
            matrix[row : row + 3, 0] = [base_time, base_time + 0.1e-9, base_time + 0.2e-9]
            matrix[row : row + 3, 1] = [0.0, 0.9, 0.9]
            for bit in range(10):
                matrix[row : row + 3, 2 + bit] = 0.9 if (int(code) >> bit) & 1 else 0.0
        np.savetxt(path, matrix, delimiter=",", header=",".join(names), comments="")

    def test_source_contract_is_explicit_and_voltage_mode(self) -> None:
        source = (
            PROJECT_ROOT / "models" / "veriloga" / "sar_adc_ideal_10b.va"
        ).read_text(encoding="utf-8")
        for port in (
            "VINP",
            "VINN",
            "VREFP",
            "VREFN",
            "CLK_SAMPLE",
            "CLK_SAR",
            "RST_N",
            "DOUT",
            "BUSY",
            "VALID",
        ):
            self.assertIn(port, source)
        self.assertEqual(source.count("V(DOUT["), 10)
        self.assertNotIn("I(", source)
        self.assertNotIn("ddt(", source)
        self.assertNotIn("idt(", source)
        self.assertIn("@(initial_step)", source)
        self.assertIn("bit_index = bit_index - 1", source)

    def test_valid_edge_decoder_waits_for_output_settling(self) -> None:
        names = ["time", "valid", *(f"dout_{bit}" for bit in range(10))]
        dtype = [(name, float) for name in names]
        data = np.zeros(5, dtype=dtype)
        data["time"] = [0.0, 1e-9, 1.05e-9, 1.1e-9, 2e-9]
        data["valid"] = [0.0, 0.9, 0.9, 0.9, 0.9]
        data["dout_9"] = [0.0, 0.0, 0.9, 0.9, 0.9]
        data["dout_8"] = [0.0, 0.0, 0.9, 0.9, 0.9]
        times, codes = _valid_samples(data)
        np.testing.assert_allclose(times, [1.1e-9])
        np.testing.assert_array_equal(codes, [768])

    def test_static_and_dynamic_analysis_gates(self) -> None:
        model = SarAdcModel(10, (-0.9, 0.9))
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            static_codes = np.repeat(np.arange(1024, dtype=np.int64), 8)
            static_csv = temp / "static.csv"
            self._write_code_csv(static_csv, static_codes)
            static = analyze_static(static_csv)
            self.assertEqual(static["missing_code_count"], 0)
            self.assertEqual(static["dnl_min_lsb"], 0.0)
            self.assertEqual(static["dnl_max_lsb"], 0.0)

            sample_count = 16384
            sample_rate_hz = 10e6
            input_frequency_hz = sample_rate_hz * 7373 / sample_count
            sample_time = (
                FIRST_SAMPLE_CROSSING_S
                + np.arange(sample_count) / sample_rate_hz
            )
            differential_peak_v = 0.9 * 10.0 ** (-1.0 / 20.0)
            vin = differential_peak_v * np.sin(
                2.0 * np.pi * input_frequency_hz * sample_time
            )
            dynamic_codes = model.unsigned_codes(model.convert(vin))
            dynamic_csv = temp / "dynamic.csv"
            self._write_code_csv(dynamic_csv, dynamic_codes)
            dynamic = analyze_dynamic(dynamic_csv)
            self.assertGreaterEqual(dynamic["sndr_db"], 55.94)
            self.assertGreaterEqual(dynamic["enob_bits"], 9.0)


if __name__ == "__main__":
    unittest.main()
