# My Voicebank

Starter pack for a personal OpenVPI-style singing voicebank workflow built around DiffSinger, MakeDiffSinger, and SOME.

## What This Repo Is For

This repo keeps your project metadata, notes, templates, and lightweight bookkeeping in one place. The canonical dataset for the first pass lives under `datasets/singer_v1/raw`, while generated artifacts and large binaries stay out of version control.

The operating rule is simple:

1. Record clean source audio.
2. Build and back up `transcriptions.csv`.
3. Run alignment to fill `ph_seq`, `ph_dur`, and `ph_num`.
4. Fine-tune acoustics first.
5. Add `note_seq` and `note_dur` later with SOME.

## Repo Layout

```text
my-voicebank/
  env/                  environment notes and version tracking
  tools/                external repos cloned locally
  datasets/singer_v1/   source data, backups, QC notes, generated exports
  models/               pretrained and fine-tuned model files
  experiments/          run-specific configs, logs, and checkpoints
  renders/              demo outputs and A/B comparisons
```

## First Setup

Clone the upstream tools into `tools/`:

- `tools/DiffSinger`
- `tools/MakeDiffSinger`
- `tools/SOME`

Keep `env/package-versions.txt` updated as you install Conda envs, MFA, pretrained checkpoints, and vocoders. That makes it much easier to reproduce a working setup later.

## Clip Naming Rules

Use a simple, stable naming scheme from day one:

- Use zero-padded six-digit clip IDs like `000001`, `000002`, `000003`.
- Match the WAV basename exactly to the `name` field in `transcriptions.csv`.
- Treat each final training clip as a unique ID. If you re-record a phrase, give it a new ID instead of replacing the old one.
- Avoid spaces, punctuation, and semantic names in filenames.
- Track recording or QC notes in the retake sheet instead of encoding them in the filename.

Examples:

- `datasets/singer_v1/raw/wavs/000001.wav`
- `datasets/singer_v1/raw/wavs/000257.wav`

## `transcriptions.csv` Schema

Use these columns for the first-pass dataset:

| Column | Status | Notes |
| --- | --- | --- |
| `name` | required | Must match the clip basename without `.wav` |
| `txt` | recommended | Human-readable lyric text for QC |
| `ph_seq` | required later | Filled after phoneme labeling/alignment |
| `ph_dur` | required later | Space-separated phoneme durations |
| `ph_num` | required later | Integer phoneme count |
| `note_seq` | added later | Added or corrected after SOME/manual pass |
| `note_dur` | added later | Added or corrected after SOME/manual pass |
| `comments` | recommended | QC notes, retake flags, alignment issues |

The template file starts with headers only so you can fill it cleanly:

- `datasets/singer_v1/raw/transcriptions.csv`

## Daily Workflow

1. Put raw mono WAVs into `datasets/singer_v1/raw/wavs/`.
2. Add one row per clip to `datasets/singer_v1/raw/transcriptions.csv`.
3. Log bad takes or retakes in `datasets/singer_v1/qc/retake_sheet.csv`.
4. Copy `transcriptions.csv` into `datasets/singer_v1/backups/` before running any automatic relabeling.
5. Save generated MIDI, lab, or dataset exports under `datasets/singer_v1/exports/`.

## Notes On Safety And Scope

Only record voices you have the right to model. Keep the first month narrow: one singer, one language, one singing style, one pretrained vocoder, and one clean dataset pipeline.
