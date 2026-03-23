# my-voicebank

OpenVPI-style singing voice synthesis project — DiffSinger acoustic model fine-tuned on a single English singer.

## Project structure

```
datasets/singer_v1/raw/          # Canonical source: wavs/ + transcriptions.csv
datasets/singer_v1/exports/      # Generated: labs, midi, dataset exports
datasets/singer_v1/backups/      # Timestamped CSV backups
datasets/singer_v1/qc/           # Rejection notes, retake tracking
models/                          # Pretrained checkpoints (vocoder, SOME, acoustic, variance)
tools/                           # Cloned OpenVPI repos (DiffSinger, MakeDiffSinger, SOME, audio-slicer)
scripts/                         # Project helper scripts (see below)
experiments/                     # Training runs
renders/                         # Demo outputs
```

## Conda environments

| Env | Python | Purpose |
|-----|--------|---------|
| `myvb-diffsinger` | 3.10 | DiffSinger training & inference |
| `myvb-some` | 3.10 | SOME note extraction |
| `myvb-mfa` | 3.8 | Montreal Forced Aligner |

**Important:** `conda run -n myvb-some` does NOT activate properly — use `/opt/anaconda3/envs/myvb-some/bin/python3` directly. Same issue may apply to other envs. SOME scripts also need `PYTHONPATH=/path/to/tools/SOME`.

MFA's default root is `~/Documents/MFA` (not `/tmp/myvb-mfa`).

## transcriptions.csv format

8 columns: `name, txt, ph_seq, ph_dur, ph_num, note_seq, note_dur, comments`

- `ph_seq`: space-separated IPA phonemes (MFA english_mfa phone set), `SP` for silence
- `ph_dur`: space-separated durations in seconds, 1:1 with ph_seq
- `ph_num`: space-separated integers — phone count per word/silence group
- `note_seq`: space-separated note names (`C4`, `rest`, etc.) from SOME
- `note_dur`: space-separated note durations in seconds
- `comments`: QC flags; `exclude:` prefix means clip is flagged out of training

## Dataset status

- 122 total clips, 106 with full labels, 16 pure-vocalizing (unlabeled)
- 12 clips tagged `exclude:` (low SNR or alignment issues)
- **94 training-ready clips** (~12 minutes)
- OOV supplement dictionary at `exports/labs/english_word_staging/oov_supplement.dict`
- Extended MFA dictionary (english_mfa + supplement) cached at `/tmp/english_mfa_extended.dict` — rebuild if lost

## Scripts

| Script | Purpose |
|--------|---------|
| `prepare_alignment_staging.py` | Normalize text → .lab files, strip `[vocalizing]`, apply sung spelling map |
| `fill_ph_from_textgrids.py` | Parse MFA TextGrids → fill ph_seq, ph_dur, ph_num in CSV |
| `batch_some_infer.py` | Batch SOME inference → fill note_seq, note_dur + save MIDIs |
| `batch_rename_clips.py` | Rename WAVs to 6-digit IDs |
| `scaffold_transcriptions.py` | Create/update transcriptions.csv skeleton |
| `bootstrap_tools.sh` | Clone OpenVPI tool repos |
| `create_envs.sh` | Create conda environments |
| `download_assets.sh` | Download vocoder, SOME, RMVPE models |

## Conventions

- Always back up transcriptions.csv before bulk writes (to `datasets/singer_v1/backups/`)
- WAV filenames are 6-digit zero-padded numeric IDs (000001.wav)
- Text fields containing commas must be quoted in the CSV
- The sung spelling map in `prepare_alignment_staging.py` handles: loomin→looming, goin→going, fuckin→fucking, thinkin→thinking
