# Dataset Notes

`raw/` is the canonical source for this dataset.

- `raw/wavs/` holds the final training clips (mono 44.1kHz WAV, 6-digit IDs).
- `raw/transcriptions.csv` is the working label sheet.
- `backups/` stores dated copies of `transcriptions.csv`.
- `exports/` holds generated artifacts such as MIDI, lab files, or processed dataset exports.
- `qc/` holds rejection notes, retake tracking, and naming guidance.

Before running any tool that rewrites labels, create a timestamped backup of `raw/transcriptions.csv`.
