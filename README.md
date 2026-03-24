# my-voicebank

A reproducible pipeline for training [DiffSinger](https://github.com/openvpi/DiffSinger) singing voice synthesis models from scratch on your own recordings.

Built around the OpenVPI ecosystem: DiffSinger, MakeDiffSinger, SOME, and Montreal Forced Aligner.

## What you get

- Scripts for the full labeling pipeline: slicing, text normalization, forced alignment, note extraction
- Training configs and notebooks for Colab / GCE / local Mac
- A clean project structure that separates code from data

## Quick start

```bash
# 1. Clone and bootstrap tools
git clone https://github.com/<you>/my-voicebank.git
cd my-voicebank
bash scripts/bootstrap_tools.sh

# 2. Create conda environments (DiffSinger, SOME, MFA)
bash scripts/create_envs.sh

# 3. Download vocoder (and optionally SOME + RMVPE models)
bash scripts/download_assets.sh
# DOWNLOAD_SOME_MODEL=1 DOWNLOAD_RMVPE=1 bash scripts/download_assets.sh
```

## Training guide

### 1. Prepare recordings

Place mono 44.1kHz WAV files in `datasets/<singer>/raw/wavs/`, named with 6-digit IDs:

```
datasets/my_singer/raw/wavs/000001.wav
datasets/my_singer/raw/wavs/000002.wav
...
```

### 2. Scaffold transcriptions.csv

```bash
python scripts/scaffold_transcriptions.py \
    datasets/my_singer/raw/transcriptions.csv \
    datasets/my_singer/raw/wavs/
```

Then fill in the `txt` column with the sung lyrics for each clip.

### 3. Forced alignment (MFA)

Generate `.lab` files and run Montreal Forced Aligner:

```bash
# Create .lab files from lyrics
python scripts/prepare_alignment_staging.py \
    datasets/my_singer/raw/transcriptions.csv \
    datasets/my_singer/raw/wavs/ \
    datasets/my_singer/exports/labs/staging/ \
    --spelling-map configs/spelling_map_example.json  # optional

# Run MFA (use the myvb-mfa conda env)
mfa align \
    datasets/my_singer/exports/labs/staging/ \
    english_mfa english_mfa \
    datasets/my_singer/exports/labs/aligned/

# Fill ph_seq, ph_dur, ph_num from TextGrids
python scripts/fill_ph_from_textgrids.py \
    datasets/my_singer/raw/transcriptions.csv \
    datasets/my_singer/exports/labs/aligned/
```

If MFA reports OOV words, create an OOV supplement dictionary and merge it:

```bash
mfa align \
    datasets/my_singer/exports/labs/staging/ \
    /path/to/extended_dictionary.dict english_mfa \
    datasets/my_singer/exports/labs/aligned/
```

### 4. Note extraction (SOME)

```bash
/path/to/myvb-some/bin/python3 scripts/batch_some_infer.py \
    datasets/my_singer/raw/transcriptions.csv \
    datasets/my_singer/raw/wavs/ \
    models/some/0831_opencpop_ds1000.ckpt \
    --midi-dir datasets/my_singer/exports/midi/
```

### 5. Binarize

Copy your labeled data into the DiffSinger data directory and run binarization:

```bash
cd tools/DiffSinger

# Copy config (edit the template for your singer first)
cp ../../configs/acoustic_template.yaml configs/my_singer_acoustic.yaml
# Edit configs/my_singer_acoustic.yaml — set singer name, test_prefixes, etc.

# Copy dictionary
cp ../../datasets/my_singer/exports/labs/english_ipa.txt dictionaries/

# Link or copy raw data
ln -s ../../datasets/my_singer/raw data/my_singer/raw

# Binarize
python scripts/binarize.py --config configs/my_singer_acoustic.yaml
```

### 6. Train

**Local (Mac/CPU):**
```bash
python scripts/train.py --config configs/my_singer_acoustic.yaml --exp_name my_singer_acoustic --reset
```

**Google Colab:**
Upload `<singer>_binary.zip` and your config YAML to Google Drive, then open `notebooks/train_colab.ipynb`.

**GCE VM:**
```bash
# Upload binarized data
gcloud compute scp my_singer_binary.zip <instance>:~/

# Run setup
SINGER_NAME=my_singer \
CONFIG_FILE=configs/my_singer_acoustic.yaml \
DICTIONARY_FILE=dictionaries/english_ipa.txt \
bash scripts/gce_train_setup.sh

# Start training
cd DiffSinger
python scripts/train.py --config configs/my_singer_acoustic.yaml --exp_name my_singer_acoustic --reset
```

### 7. Inference

```bash
# Generate .ds file
python scripts/make_ds_from_csv.py \
    --clip 000001 \
    --csv datasets/my_singer/raw/transcriptions.csv

# Run DiffSinger inference
cd tools/DiffSinger
python scripts/infer.py acoustic ../../renders/000001.ds --exp my_singer_acoustic
```

## Project structure

```
my-voicebank/
  configs/                 Training config templates, spelling maps
  datasets/<singer>/raw/   Source WAVs + transcriptions.csv
  datasets/<singer>/exports/  Generated labs, MIDI, ds files
  models/                  Pretrained checkpoints (vocoder, SOME, RMVPE)
  tools/                   Cloned OpenVPI repos (gitignored)
  scripts/                 Pipeline scripts
  notebooks/               Colab training notebook
  experiments/             Training runs and checkpoints
  renders/                 Inference outputs
```

## transcriptions.csv format

| Column | Description |
|--------|-------------|
| `name` | Clip ID matching WAV filename (e.g. `000001`) |
| `txt` | Sung lyrics |
| `ph_seq` | Space-separated IPA phonemes from MFA |
| `ph_dur` | Space-separated durations (seconds), 1:1 with ph_seq |
| `ph_num` | Phone count per word/silence group |
| `note_seq` | Note names from SOME (`C4`, `rest`, etc.) |
| `note_dur` | Note durations (seconds) |
| `comments` | QC flags; `exclude:` prefix removes clip from training |

## Environment variables

| Variable | Used by | Purpose |
|----------|---------|---------|
| `SUNG_SPELLING_MAP` | `prepare_alignment_staging.py` | Path to JSON spelling map file |
| `SINGER_NAME` | `gce_train_setup.sh` | Singer profile name |
| `BINARY_ZIP` | `gce_train_setup.sh` | Path to binarized dataset zip |
| `CONFIG_FILE` | `gce_train_setup.sh` | Path to training config YAML |
| `DICTIONARY_FILE` | `gce_train_setup.sh` | Path to phoneme dictionary |

## Tips

- **Back up transcriptions.csv** before any bulk operation
- **Avoid commas in lyrics** — simpler than quoting CSV fields
- **Mark bad clips** with `exclude:` in the comments column rather than deleting rows
- **Start small** — 50-100 clips (~10-15 min) is enough for a first training run
- Train on GPU (T4/L4) for reasonable speed; CPU works but is very slow
- Enable pitch augmentation after your base model converges to improve robustness

## Ethics

Only record and model voices you have the right to use. This toolkit is intended for personal and creative use with consent.

## License

MIT
