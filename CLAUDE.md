# my-voicebank

OpenVPI-style singing voice synthesis project — DiffSinger acoustic model trained on a single English singer.

## Project structure

```
datasets/<singer>/raw/           # Canonical source: wavs/ + transcriptions.csv
datasets/<singer>/exports/       # Generated: labs, midi, dataset exports
datasets/<singer>/backups/       # Timestamped CSV backups
datasets/<singer>/qc/            # Rejection notes, retake tracking
configs/                         # Training config templates and spelling maps
models/                          # Pretrained checkpoints (vocoder, SOME, acoustic, variance)
tools/                           # Cloned OpenVPI repos (DiffSinger, MakeDiffSinger, SOME, audio-slicer)
scripts/                         # Project helper scripts (see below)
notebooks/                       # Colab training notebook
experiments/                     # Training runs
renders/                         # Demo outputs
```

## Conda environments

| Env | Python | Purpose |
|-----|--------|---------|
| `myvb-diffsinger` | 3.10 | DiffSinger training & inference |
| `myvb-some` | 3.10 | SOME note extraction |
| `myvb-mfa` | 3.8 | Montreal Forced Aligner |

**Important:** `conda run -n <env>` may not activate properly — use direct Python paths (e.g. `/opt/anaconda3/envs/myvb-some/bin/python3`). SOME scripts also need `PYTHONPATH=/path/to/tools/SOME`.

MFA's default root is `~/Documents/MFA`.

## transcriptions.csv format

8 columns: `name, txt, ph_seq, ph_dur, ph_num, note_seq, note_dur, comments`

- `ph_seq`: space-separated IPA phonemes (MFA english_mfa phone set), `SP` for silence
- `ph_dur`: space-separated durations in seconds, 1:1 with ph_seq
- `ph_num`: space-separated integers — phone count per word/silence group
- `note_seq`: space-separated note names (`C4`, `rest`, etc.) from SOME
- `note_dur`: space-separated note durations in seconds
- `comments`: QC flags; `exclude:` prefix means clip is flagged out of training

## Scripts

| Script | Purpose |
|--------|---------|
| `prepare_alignment_staging.py` | Normalize text → .lab files, strip `[vocalizing]`, apply spelling map |
| `fill_ph_from_textgrids.py` | Parse MFA TextGrids → fill ph_seq, ph_dur, ph_num in CSV |
| `batch_some_infer.py` | Batch SOME inference → fill note_seq, note_dur + save MIDIs |
| `batch_rename_clips.py` | Rename WAVs to 6-digit IDs |
| `scaffold_transcriptions.py` | Create/update transcriptions.csv skeleton |
| `make_ds_from_csv.py` | Build .ds inference files from CSV + WAV |
| `bootstrap_tools.sh` | Clone OpenVPI tool repos |
| `create_envs.sh` | Create conda environments |
| `download_assets.sh` | Download vocoder, SOME, RMVPE models |
| `gce_train_setup.sh` | Set up DiffSinger training on a GCE VM |

## Conventions

- Always back up transcriptions.csv before bulk writes (to `datasets/<singer>/backups/`)
- WAV filenames are 6-digit zero-padded numeric IDs (000001.wav)
- Avoid commas in txt fields (prefer removing them over quoting CSV fields)
- Spelling map for informal/sung words is loaded from a JSON file via `--spelling-map` or `SUNG_SPELLING_MAP` env var
