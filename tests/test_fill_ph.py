"""Tests for scripts/fill_ph_from_textgrids.py."""
import csv
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from fill_ph_from_textgrids import parse_textgrid, extract_fields
from conftest import SAMPLE_TEXTGRID, make_wav_stubs


# ---------------------------------------------------------------------------
# parse_textgrid
# ---------------------------------------------------------------------------

class TestParseTextgrid:
    def test_parses_two_tiers(self, tmp_path):
        tg = tmp_path / "test.TextGrid"
        tg.write_text(SAMPLE_TEXTGRID, encoding="utf-8")
        tiers = parse_textgrid(tg)
        assert len(tiers) == 2

    def test_word_tier_intervals(self, tmp_path):
        tg = tmp_path / "test.TextGrid"
        tg.write_text(SAMPLE_TEXTGRID, encoding="utf-8")
        tiers = parse_textgrid(tg)
        word_tier = tiers[0]
        assert len(word_tier) == 3
        # Middle interval is "hello"
        assert word_tier[1][2] == "hello"

    def test_phone_tier_intervals(self, tmp_path):
        tg = tmp_path / "test.TextGrid"
        tg.write_text(SAMPLE_TEXTGRID, encoding="utf-8")
        tiers = parse_textgrid(tg)
        phone_tier = tiers[1]
        assert len(phone_tier) == 6
        labels = [t[2] for t in phone_tier]
        assert labels == ["", "h", "ɛ", "l", "oʊ", ""]

    def test_single_tier_raises_in_extract(self, tmp_path):
        single_tier = textwrap.dedent("""\
            File type = "ooTextFile"
            Object class = "TextGrid"
            xmin = 0
            xmax = 1
            tiers? <exists>
            size = 1
            item [1]:
                class = "IntervalTier"
                name = "words"
                xmin = 0
                xmax = 1
                intervals: size = 1
                intervals [1]:
                    xmin = 0
                    xmax = 1
                    text = "hello"
        """)
        tg = tmp_path / "bad.TextGrid"
        tg.write_text(single_tier, encoding="utf-8")
        with pytest.raises(ValueError, match="Expected 2 tiers"):
            extract_fields(tg)


# ---------------------------------------------------------------------------
# extract_fields
# ---------------------------------------------------------------------------

class TestExtractFields:
    def test_ph_seq_maps_empty_to_SP(self, tmp_path):
        tg = tmp_path / "test.TextGrid"
        tg.write_text(SAMPLE_TEXTGRID, encoding="utf-8")
        ph_seq, ph_dur, ph_num = extract_fields(tg)
        phones = ph_seq.split()
        assert phones[0] == "SP"   # leading silence
        assert phones[-1] == "SP"  # trailing silence
        assert "h" in phones
        assert "ɛ" in phones

    def test_ph_dur_positive(self, tmp_path):
        tg = tmp_path / "test.TextGrid"
        tg.write_text(SAMPLE_TEXTGRID, encoding="utf-8")
        _, ph_dur, _ = extract_fields(tg)
        durations = [float(d) for d in ph_dur.split()]
        assert all(d > 0 for d in durations)

    def test_ph_num_sums_to_phone_count(self, tmp_path):
        tg = tmp_path / "test.TextGrid"
        tg.write_text(SAMPLE_TEXTGRID, encoding="utf-8")
        ph_seq, _, ph_num = extract_fields(tg)
        phones = ph_seq.split()
        nums = [int(n) for n in ph_num.split()]
        assert sum(nums) == len(phones)

    def test_ph_num_structure(self, tmp_path):
        """3 word intervals → 3 groups: SP(1), hello(4 phones), SP(1)."""
        tg = tmp_path / "test.TextGrid"
        tg.write_text(SAMPLE_TEXTGRID, encoding="utf-8")
        _, _, ph_num = extract_fields(tg)
        nums = [int(n) for n in ph_num.split()]
        assert nums == [1, 4, 1]  # SP | h ɛ l oʊ | SP

    def test_duration_precision(self, tmp_path):
        tg = tmp_path / "test.TextGrid"
        tg.write_text(SAMPLE_TEXTGRID, encoding="utf-8")
        _, ph_dur, _ = extract_fields(tg)
        for d in ph_dur.split():
            # Should have at most 6 decimal places
            if "." in d:
                assert len(d.split(".")[1]) <= 6


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------

class TestFillPhCLI:
    def test_fills_csv_from_textgrids(self, tmp_path, csv_factory):
        tg_dir = tmp_path / "textgrids"
        tg_dir.mkdir()
        (tg_dir / "000001.TextGrid").write_text(SAMPLE_TEXTGRID, encoding="utf-8")

        csv_path = csv_factory([
            {"name": "000001", "txt": "hello", "ph_seq": "", "ph_dur": "", "ph_num": ""},
        ])

        result = subprocess.run(
            [sys.executable, "-m", "fill_ph_from_textgrids", str(csv_path), str(tg_dir)],
            cwd=str(Path(__file__).resolve().parent.parent / "scripts"),
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "Filled 1" in result.stdout

        with csv_path.open("r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["ph_seq"] != ""
        assert rows[0]["ph_dur"] != ""
        assert rows[0]["ph_num"] != ""

    def test_skips_missing_textgrid(self, tmp_path, csv_factory):
        tg_dir = tmp_path / "textgrids"
        tg_dir.mkdir()

        csv_path = csv_factory([
            {"name": "000099", "txt": "no textgrid", "ph_seq": "", "ph_dur": "", "ph_num": ""},
        ])

        result = subprocess.run(
            [sys.executable, "-m", "fill_ph_from_textgrids", str(csv_path), str(tg_dir)],
            cwd=str(Path(__file__).resolve().parent.parent / "scripts"),
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "skipped 1" in result.stdout
