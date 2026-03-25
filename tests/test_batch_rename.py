"""Tests for scripts/batch_rename_clips.py."""
import csv
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from batch_rename_clips import natural_key, next_start_id
from conftest import make_wav_stubs


# ---------------------------------------------------------------------------
# natural_key
# ---------------------------------------------------------------------------

class TestNaturalKey:
    def test_numeric_sorting(self, tmp_path):
        paths = [tmp_path / f"clip_{n}.wav" for n in [10, 2, 1, 20]]
        sorted_paths = sorted(paths, key=natural_key)
        stems = [p.stem for p in sorted_paths]
        assert stems == ["clip_1", "clip_2", "clip_10", "clip_20"]

    def test_alpha_sorting(self, tmp_path):
        paths = [tmp_path / f"{n}.wav" for n in ["beta", "alpha", "gamma"]]
        sorted_paths = sorted(paths, key=natural_key)
        stems = [p.stem for p in sorted_paths]
        assert stems == ["alpha", "beta", "gamma"]

    def test_mixed_sorting(self, tmp_path):
        paths = [tmp_path / f for f in ["a2.wav", "a10.wav", "a1.wav"]]
        sorted_paths = sorted(paths, key=natural_key)
        stems = [p.stem for p in sorted_paths]
        assert stems == ["a1", "a2", "a10"]


# ---------------------------------------------------------------------------
# next_start_id
# ---------------------------------------------------------------------------

class TestNextStartId:
    def test_empty_dir_starts_at_1(self, wav_dir):
        assert next_start_id(wav_dir) == 1

    def test_continues_after_existing(self, wav_dir):
        make_wav_stubs(wav_dir, ["000005", "000010"])
        assert next_start_id(wav_dir) == 11

    def test_ignores_non_numeric(self, wav_dir):
        make_wav_stubs(wav_dir, ["clip_a", "clip_b"])
        assert next_start_id(wav_dir) == 1


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------

class TestBatchRenameCLI:
    def test_renames_to_six_digit_ids(self, tmp_path):
        wav_dir = tmp_path / "raw" / "wavs"
        wav_dir.mkdir(parents=True)
        qc_dir = tmp_path / "raw" / "qc"  # where mapping goes by default
        qc_dir.mkdir(parents=True)

        make_wav_stubs(wav_dir, ["clip_a", "clip_b", "clip_c"])

        result = subprocess.run(
            [sys.executable, "-m", "batch_rename_clips", str(wav_dir)],
            cwd=str(Path(__file__).resolve().parent.parent / "scripts"),
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr

        remaining = sorted(p.stem for p in wav_dir.glob("*.wav"))
        assert remaining == ["000001", "000002", "000003"]

    def test_dry_run_no_changes(self, wav_dir):
        make_wav_stubs(wav_dir, ["clip_x"])

        result = subprocess.run(
            [sys.executable, "-m", "batch_rename_clips", str(wav_dir), "--dry-run"],
            cwd=str(Path(__file__).resolve().parent.parent / "scripts"),
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Dry run" in result.stdout
        # Original file still exists
        assert (wav_dir / "clip_x.wav").exists()

    def test_skips_already_numeric(self, wav_dir):
        make_wav_stubs(wav_dir, ["000001"])

        result = subprocess.run(
            [sys.executable, "-m", "batch_rename_clips", str(wav_dir)],
            cwd=str(Path(__file__).resolve().parent.parent / "scripts"),
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "No non-numeric" in result.stdout

    def test_custom_start_id(self, tmp_path):
        wav_dir = tmp_path / "raw" / "wavs"
        wav_dir.mkdir(parents=True)
        (tmp_path / "raw" / "qc").mkdir(parents=True)

        make_wav_stubs(wav_dir, ["clip_a"])

        result = subprocess.run(
            [sys.executable, "-m", "batch_rename_clips", str(wav_dir), "--start-id", "50"],
            cwd=str(Path(__file__).resolve().parent.parent / "scripts"),
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        assert (wav_dir / "000050.wav").exists()

    def test_collision_detection(self, wav_dir):
        make_wav_stubs(wav_dir, ["000001", "clip_a"])

        result = subprocess.run(
            [sys.executable, "-m", "batch_rename_clips", str(wav_dir), "--start-id", "1"],
            cwd=str(Path(__file__).resolve().parent.parent / "scripts"),
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "already exists" in result.stderr

    def test_mapping_csv_written(self, tmp_path):
        wav_dir = tmp_path / "raw" / "wavs"
        wav_dir.mkdir(parents=True)
        mapping_path = tmp_path / "mapping.csv"

        make_wav_stubs(wav_dir, ["clip_a", "clip_b"])

        subprocess.run(
            [sys.executable, "-m", "batch_rename_clips", str(wav_dir),
             "--mapping-out", str(mapping_path)],
            cwd=str(Path(__file__).resolve().parent.parent / "scripts"),
            capture_output=True, text=True,
        )
        assert mapping_path.exists()
        with mapping_path.open("r") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2
        assert rows[0]["original_name"] == "clip_a"
        assert rows[0]["new_name"] == "000001"
