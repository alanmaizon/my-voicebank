# singer_v1 Dataset Notes

`raw/` is the canonical source for this dataset version.

- `raw/wavs/` holds the final training clips.
- `raw/transcriptions.csv` is the working label sheet.
- `backups/` stores dated copies of `transcriptions.csv`.
- `exports/` holds generated artifacts such as MIDI, lab files, or processed dataset exports.
- `qc/` holds rejection notes, retake tracking, and naming guidance.

Before running any tool that rewrites labels, create a timestamped backup of `raw/transcriptions.csv`.
