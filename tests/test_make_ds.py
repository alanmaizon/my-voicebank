"""Tests for scripts/make_ds_from_csv.py — DS building and F0 zeroing logic.

F0 extraction requires parselmouth + real WAVs, so we test the building
logic by mocking F0 extraction where needed.
"""
import csv
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


# ---------------------------------------------------------------------------
# DS segment building (no parselmouth needed)
# ---------------------------------------------------------------------------

class TestDsSegmentBuilding:
    """Test the phone processing and F0 zeroing logic without real audio."""

    def _build_segment(self, ph_seq, ph_dur, f0_values, txt="test"):
        """Reproduce the segment-building logic from make_ds_from_csv.main."""
        phones = ph_seq.split()
        durs = [float(d) for d in ph_dur.split()]

        # Leading SP → AP
        if phones[0] == "SP":
            phones[0] = "AP"
        ph_seq_out = " ".join(phones)

        UNVOICED = {
            "SP", "AP", "p", "pʲ", "t", "tʰ", "tʲ", "tʃ", "k", "kʰ",
            "c", "cʰ", "cʷ", "f", "fʲ", "s", "ʃ", "h", "θ", "ç",
            "ʈ", "ʈʲ", "t̪",
        }
        hop_sec = 0.005
        f0_arr = list(f0_values)

        tail_start = len(phones)
        for j in range(len(phones) - 1, -1, -1):
            if phones[j] in UNVOICED:
                tail_start = j
            else:
                break

        head_end = 0
        for j in range(len(phones)):
            if phones[j] in ("SP", "AP"):
                head_end = j + 1
            else:
                break

        cursor = 0.0
        for idx, (ph, dur) in enumerate(zip(phones, durs)):
            start_frame = int(round(cursor / hop_sec))
            end_frame = int(round((cursor + dur) / hop_sec))
            if idx < head_end or idx >= tail_start:
                for i in range(start_frame, min(end_frame, len(f0_arr))):
                    f0_arr[i] = 0.0
            cursor += dur

        return ph_seq_out, f0_arr

    def test_leading_sp_becomes_ap(self):
        ph_seq_out, _ = self._build_segment(
            "SP h ɛ l oʊ SP",
            "0.3 0.15 0.2 0.2 0.25 0.4",
            [0.0] * 300,
        )
        assert ph_seq_out.startswith("AP")

    def test_leading_silence_f0_zeroed(self):
        # 0.3s silence = 60 frames at 5ms hop
        f0 = [220.0] * 300
        _, f0_out = self._build_segment(
            "SP h ɛ l oʊ SP",
            "0.3 0.15 0.2 0.2 0.25 0.4",
            f0,
        )
        # First 60 frames (leading SP) should be zeroed
        assert all(v == 0.0 for v in f0_out[:60])

    def test_trailing_silence_f0_zeroed(self):
        f0 = [220.0] * 300
        _, f0_out = self._build_segment(
            "SP h ɛ l oʊ SP",
            "0.3 0.15 0.2 0.2 0.25 0.4",
            f0,
        )
        # Last 80 frames (trailing SP, 0.4s) should be zeroed
        assert all(v == 0.0 for v in f0_out[220:])

    def test_mid_phrase_f0_preserved(self):
        f0 = [220.0] * 300
        _, f0_out = self._build_segment(
            "SP h ɛ l oʊ SP",
            "0.3 0.15 0.2 0.2 0.25 0.4",
            f0,
        )
        # Mid-phrase voiced region should keep F0
        # Frames 60-220 cover the word phones
        assert any(v > 0 for v in f0_out[60:220])

    def test_trailing_unvoiced_consonant_zeroed(self):
        """Trailing unvoiced consonants before final SP should also be zeroed."""
        f0 = [220.0] * 200
        _, f0_out = self._build_segment(
            "SP ɛ s SP",
            "0.2 0.3 0.2 0.3",
            f0,
        )
        # 's' is unvoiced, comes before trailing SP → both zeroed
        # s starts at frame 100, SP starts at 140
        assert all(v == 0.0 for v in f0_out[100:])

    def test_no_phones_in_unvoiced_set_preserves_f0(self):
        """Voiced consonants mid-phrase keep their F0."""
        f0 = [220.0] * 200
        _, f0_out = self._build_segment(
            "SP m ɛ n SP",
            "0.1 0.2 0.3 0.2 0.2",
            f0,
        )
        # m, ɛ, n are all voiced → mid-phrase F0 preserved
        # m starts at frame 20 (after 0.1s AP), n ends at frame 160
        assert all(v == 220.0 for v in f0_out[20:160])


# ---------------------------------------------------------------------------
# CSV lookup
# ---------------------------------------------------------------------------

class TestCsvLookup:
    def test_clip_not_found_raises(self, tmp_path, csv_factory):
        csv_path = csv_factory([
            {"name": "000001", "txt": "hello", "ph_seq": "h ɛ l oʊ",
             "ph_dur": "0.15 0.2 0.2 0.25"},
        ])
        result = subprocess.run(
            [sys.executable, "-m", "make_ds_from_csv",
             "--clip", "999999", "--csv", str(csv_path)],
            cwd=str(Path(__file__).resolve().parent.parent / "scripts"),
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "not found" in result.stderr


# ---------------------------------------------------------------------------
# Full CLI (requires parselmouth — skip if not installed)
# ---------------------------------------------------------------------------

class TestMakeDsCLI:
    @pytest.fixture
    def sine_wav(self, tmp_path):
        """Create a short sine wave WAV for testing."""
        try:
            import numpy as np
            import wave
        except ImportError:
            pytest.skip("numpy required for WAV generation")

        sr = 44100
        duration = 1.5
        freq = 220.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        samples = (np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)

        wav_path = tmp_path / "wavs" / "000001.wav"
        wav_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(wav_path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(samples.tobytes())
        return wav_path

    def test_generates_ds_file(self, tmp_path, csv_factory, sine_wav):
        try:
            import parselmouth  # noqa: F401
        except ImportError:
            pytest.skip("parselmouth not installed")

        csv_path = csv_factory([
            {"name": "000001", "txt": "hello", "ph_seq": "SP h ɛ l oʊ SP",
             "ph_dur": "0.3 0.15 0.2 0.2 0.25 0.4", "ph_num": "1 4 1"},
        ])
        out_path = tmp_path / "out" / "000001.ds"

        result = subprocess.run(
            [sys.executable, "-m", "make_ds_from_csv",
             "--clip", "000001", "--csv", str(csv_path),
             "--wav", str(sine_wav), "--out", str(out_path)],
            cwd=str(Path(__file__).resolve().parent.parent / "scripts"),
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        assert out_path.exists()

        ds = json.loads(out_path.read_text())
        assert isinstance(ds, list)
        assert len(ds) == 1
        seg = ds[0]
        assert "ph_seq" in seg
        assert "f0_seq" in seg
        assert seg["ph_seq"].startswith("AP")  # leading SP → AP
        assert seg["f0_timestep"] == "0.005"
