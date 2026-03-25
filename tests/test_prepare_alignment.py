"""Tests for scripts/prepare_alignment_staging.py."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Import functions under test
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from prepare_alignment_staging import (
    load_spelling_map,
    normalize_english_text,
    ensure_symlink,
)
from conftest import make_wav_stubs


# ---------------------------------------------------------------------------
# normalize_english_text
# ---------------------------------------------------------------------------

class TestNormalizeEnglishText:
    def test_basic_lowering(self):
        assert normalize_english_text("Hello World") == "hello world"

    def test_strips_vocalizing_tag(self):
        assert normalize_english_text("[vocalizing] ooh") == "ooh"
        assert normalize_english_text("[Vocalizing]") == ""

    def test_unicode_smart_quotes(self):
        assert normalize_english_text("\u2018don\u2019t\u201d") == "don't"

    def test_hyphens_become_spaces(self):
        assert normalize_english_text("well-known") == "well known"

    def test_drop_apostrophes(self):
        assert normalize_english_text("don't", drop_apostrophes=True) == "dont"

    def test_keep_internal_apostrophes(self):
        assert normalize_english_text("don't") == "don't"

    def test_strip_leading_trailing_apostrophes(self):
        assert normalize_english_text("'hello'") == "hello"

    def test_spelling_map_applied(self):
        m = {"goin": "going", "singin": "singing"}
        assert normalize_english_text("goin singin", spelling_map=m) == "going singing"

    def test_spelling_map_not_applied_to_non_matches(self):
        m = {"goin": "going"}
        assert normalize_english_text("hello goin world", spelling_map=m) == "hello going world"

    def test_collapses_whitespace(self):
        assert normalize_english_text("  too   many   spaces  ") == "too many spaces"

    def test_removes_numbers_and_punctuation(self):
        assert normalize_english_text("hello! world? 123") == "hello world"

    def test_empty_string(self):
        assert normalize_english_text("") == ""

    def test_only_vocalizing(self):
        assert normalize_english_text("[vocalizing]") == ""


# ---------------------------------------------------------------------------
# load_spelling_map
# ---------------------------------------------------------------------------

class TestLoadSpellingMap:
    def test_returns_empty_when_no_path(self):
        # Ensure env var is not set
        env = os.environ.pop("SUNG_SPELLING_MAP", None)
        try:
            assert load_spelling_map(None) == {}
        finally:
            if env is not None:
                os.environ["SUNG_SPELLING_MAP"] = env

    def test_loads_from_file(self, tmp_path):
        p = tmp_path / "map.json"
        p.write_text('{"goin": "going"}', encoding="utf-8")
        assert load_spelling_map(str(p)) == {"goin": "going"}

    def test_loads_from_env_var(self, tmp_path, monkeypatch):
        p = tmp_path / "map.json"
        p.write_text('{"singin": "singing"}', encoding="utf-8")
        monkeypatch.setenv("SUNG_SPELLING_MAP", str(p))
        assert load_spelling_map(None) == {"singin": "singing"}

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            load_spelling_map("/nonexistent/map.json")


# ---------------------------------------------------------------------------
# ensure_symlink
# ---------------------------------------------------------------------------

class TestEnsureSymlink:
    def test_creates_symlink(self, tmp_path):
        src = tmp_path / "source.wav"
        src.write_bytes(b"data")
        dst = tmp_path / "link.wav"
        ensure_symlink(src, dst)
        assert dst.is_symlink()
        assert dst.resolve() == src.resolve()

    def test_idempotent_same_target(self, tmp_path):
        src = tmp_path / "source.wav"
        src.write_bytes(b"data")
        dst = tmp_path / "link.wav"
        ensure_symlink(src, dst)
        ensure_symlink(src, dst)  # no error
        assert dst.is_symlink()

    def test_replaces_symlink_different_target(self, tmp_path):
        src1 = tmp_path / "a.wav"
        src1.write_bytes(b"a")
        src2 = tmp_path / "b.wav"
        src2.write_bytes(b"b")
        dst = tmp_path / "link.wav"
        ensure_symlink(src1, dst)
        ensure_symlink(src2, dst)
        assert dst.resolve() == src2.resolve()

    def test_refuses_to_replace_real_file(self, tmp_path):
        src = tmp_path / "source.wav"
        src.write_bytes(b"data")
        dst = tmp_path / "real_file.wav"
        dst.write_bytes(b"real")
        with pytest.raises(FileExistsError):
            ensure_symlink(src, dst)


# ---------------------------------------------------------------------------
# CLI integration (end-to-end)
# ---------------------------------------------------------------------------

class TestMainCLI:
    def test_stages_clips(self, tmp_path, csv_factory, wav_dir):
        make_wav_stubs(wav_dir, ["000001", "000002"])
        csv_path = csv_factory([
            {"name": "000001", "txt": "hello world"},
            {"name": "000002", "txt": "bright sky"},
        ])
        out_dir = tmp_path / "staging"

        result = subprocess.run(
            [sys.executable, "-m", "prepare_alignment_staging",
             str(csv_path), str(wav_dir), str(out_dir)],
            cwd=str(Path(__file__).resolve().parent.parent / "scripts"),
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr

        assert (out_dir / "000001.lab").read_text().strip() == "hello world"
        assert (out_dir / "000002.lab").read_text().strip() == "bright sky"
        assert (out_dir / "000001.wav").is_symlink()
        assert (out_dir / "_lab_preview.csv").exists()
        assert (out_dir / "_wordlist.txt").exists()

    def test_missing_wav_raises(self, tmp_path, csv_factory):
        csv_path = csv_factory([{"name": "000099", "txt": "no wav here"}])
        wav_dir = tmp_path / "empty_wavs"
        wav_dir.mkdir()
        out_dir = tmp_path / "staging"

        result = subprocess.run(
            [sys.executable, "-m", "prepare_alignment_staging",
             str(csv_path), str(wav_dir), str(out_dir)],
            cwd=str(Path(__file__).resolve().parent.parent / "scripts"),
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        assert "Missing WAV" in result.stderr

    def test_missing_txt_tracked(self, tmp_path, csv_factory, wav_dir):
        make_wav_stubs(wav_dir, ["000001"])
        csv_path = csv_factory([{"name": "000001", "txt": ""}])
        out_dir = tmp_path / "staging"

        subprocess.run(
            [sys.executable, "-m", "prepare_alignment_staging",
             str(csv_path), str(wav_dir), str(out_dir)],
            cwd=str(Path(__file__).resolve().parent.parent / "scripts"),
            capture_output=True, text=True,
        )
        missing = (out_dir / "_missing_txt.csv").read_text()
        assert "000001" in missing

    def test_spelling_map_cli(self, tmp_path, csv_factory, wav_dir):
        make_wav_stubs(wav_dir, ["000001"])
        csv_path = csv_factory([{"name": "000001", "txt": "goin home"}])
        out_dir = tmp_path / "staging"
        map_path = tmp_path / "map.json"
        map_path.write_text('{"goin": "going"}', encoding="utf-8")

        result = subprocess.run(
            [sys.executable, "-m", "prepare_alignment_staging",
             str(csv_path), str(wav_dir), str(out_dir),
             "--spelling-map", str(map_path)],
            cwd=str(Path(__file__).resolve().parent.parent / "scripts"),
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        assert (out_dir / "000001.lab").read_text().strip() == "going home"
