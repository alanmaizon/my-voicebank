"""Tests for scripts/scaffold_transcriptions.py."""
import csv
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from scaffold_transcriptions import (
    DEFAULT_FIELDS,
    load_existing_rows,
    load_rename_map,
    build_row,
)
from conftest import make_wav_stubs


# ---------------------------------------------------------------------------
# load_existing_rows
# ---------------------------------------------------------------------------

class TestLoadExistingRows:
    def test_returns_defaults_when_no_file(self, tmp_path):
        fieldnames, rows = load_existing_rows(tmp_path / "nope.csv")
        assert fieldnames == DEFAULT_FIELDS
        assert rows == {}

    def test_loads_existing_csv(self, tmp_path, csv_factory):
        csv_path = csv_factory([
            {"name": "000001", "txt": "hello"},
        ])
        fieldnames, rows = load_existing_rows(csv_path)
        assert "000001" in rows
        assert rows["000001"]["txt"] == "hello"


# ---------------------------------------------------------------------------
# load_rename_map
# ---------------------------------------------------------------------------

class TestLoadRenameMap:
    def test_returns_empty_for_none(self):
        assert load_rename_map(None) == {}

    def test_loads_mapping(self, tmp_path):
        p = tmp_path / "map.csv"
        with p.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["original_name", "new_name"])
            w.writerow(["clip_a", "000001"])
        result = load_rename_map(p)
        assert result == {"000001": "clip_a"}


# ---------------------------------------------------------------------------
# build_row
# ---------------------------------------------------------------------------

class TestBuildRow:
    def test_new_row_empty_fields(self):
        row = build_row("000001", DEFAULT_FIELDS, None, None, False, False)
        assert row["name"] == "000001"
        assert row["txt"] == ""
        assert row["ph_seq"] == ""

    def test_preserves_existing_data(self):
        existing = {"name": "000001", "txt": "hello", "ph_seq": "h ɛ l oʊ"}
        row = build_row("000001", DEFAULT_FIELDS, existing, None, False, False)
        assert row["txt"] == "hello"
        assert row["ph_seq"] == "h ɛ l oʊ"

    def test_fills_comment_from_rename_map(self):
        row = build_row("000001", DEFAULT_FIELDS, None, "clip_a", True, False)
        assert row["comments"] == "source: clip_a"

    def test_does_not_overwrite_existing_comment(self):
        existing = {"name": "000001", "comments": "manual note"}
        row = build_row("000001", DEFAULT_FIELDS, existing, "clip_a", True, False)
        assert row["comments"] == "manual note"

    def test_clears_source_comment(self):
        existing = {"name": "000001", "comments": "source: old_clip"}
        row = build_row("000001", DEFAULT_FIELDS, existing, None, False, True)
        assert row["comments"] == ""

    def test_clear_then_fill(self):
        existing = {"name": "000001", "comments": "source: old_clip"}
        row = build_row("000001", DEFAULT_FIELDS, existing, "new_clip", True, True)
        assert row["comments"] == "source: new_clip"


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------

class TestScaffoldCLI:
    def test_creates_new_csv(self, tmp_path, wav_dir):
        make_wav_stubs(wav_dir, ["000001", "000002", "000003"])
        csv_path = tmp_path / "transcriptions.csv"

        result = subprocess.run(
            [sys.executable, "-m", "scaffold_transcriptions", str(csv_path), str(wav_dir)],
            cwd=str(Path(__file__).resolve().parent.parent / "scripts"),
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr

        with csv_path.open("r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 3
        names = [r["name"] for r in rows]
        assert "000001" in names

    def test_preserves_existing_rows(self, tmp_path, csv_factory, wav_dir):
        make_wav_stubs(wav_dir, ["000001", "000002"])
        csv_path = csv_factory([
            {"name": "000001", "txt": "hello world", "ph_seq": "", "ph_dur": "",
             "ph_num": "", "note_seq": "", "note_dur": "", "comments": ""},
        ])

        subprocess.run(
            [sys.executable, "-m", "scaffold_transcriptions", str(csv_path), str(wav_dir)],
            cwd=str(Path(__file__).resolve().parent.parent / "scripts"),
            capture_output=True, text=True,
        )

        with csv_path.open("r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        row1 = next(r for r in rows if r["name"] == "000001")
        assert row1["txt"] == "hello world"

    def test_has_all_default_fields(self, tmp_path, wav_dir):
        make_wav_stubs(wav_dir, ["000001"])
        csv_path = tmp_path / "transcriptions.csv"

        subprocess.run(
            [sys.executable, "-m", "scaffold_transcriptions", str(csv_path), str(wav_dir)],
            cwd=str(Path(__file__).resolve().parent.parent / "scripts"),
            capture_output=True, text=True,
        )

        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
        for field in DEFAULT_FIELDS:
            assert field in fieldnames
