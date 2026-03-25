"""Shared fixtures for voicebank test suite."""
import csv
import textwrap
from pathlib import Path

import pytest


@pytest.fixture
def csv_factory(tmp_path):
    """Return a helper that writes a transcriptions CSV and returns its path."""

    def _make(rows: list[dict], path: Path | None = None) -> Path:
        if path is None:
            path = tmp_path / "transcriptions.csv"
        fieldnames = list(rows[0].keys()) if rows else [
            "name", "txt", "ph_seq", "ph_dur", "ph_num",
            "note_seq", "note_dur", "comments",
        ]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return path

    return _make


@pytest.fixture
def wav_dir(tmp_path):
    """Create a wav directory with empty stub files and return the path."""
    d = tmp_path / "wavs"
    d.mkdir()
    return d


def make_wav_stubs(wav_dir: Path, names: list[str]):
    """Create empty .wav stub files."""
    for name in names:
        stem = name if name.endswith(".wav") else f"{name}.wav"
        (wav_dir / stem).write_bytes(b"RIFF" + b"\x00" * 40)


SAMPLE_TEXTGRID = textwrap.dedent("""\
    File type = "ooTextFile"
    Object class = "TextGrid"

    xmin = 0
    xmax = 1.5
    tiers? <exists>
    size = 2
    item [1]:
        class = "IntervalTier"
        name = "words"
        xmin = 0
        xmax = 1.5
        intervals: size = 3
        intervals [1]:
            xmin = 0
            xmax = 0.3
            text = ""
        intervals [2]:
            xmin = 0.3
            xmax = 1.1
            text = "hello"
        intervals [3]:
            xmin = 1.1
            xmax = 1.5
            text = ""
    item [2]:
        class = "IntervalTier"
        name = "phones"
        xmin = 0
        xmax = 1.5
        intervals: size = 6
        intervals [1]:
            xmin = 0
            xmax = 0.3
            text = ""
        intervals [2]:
            xmin = 0.3
            xmax = 0.45
            text = "h"
        intervals [3]:
            xmin = 0.45
            xmax = 0.65
            text = "ɛ"
        intervals [4]:
            xmin = 0.65
            xmax = 0.85
            text = "l"
        intervals [5]:
            xmin = 0.85
            xmax = 1.1
            text = "oʊ"
        intervals [6]:
            xmin = 1.1
            xmax = 1.5
            text = ""
""")
