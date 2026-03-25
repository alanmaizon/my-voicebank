# My Voicebank

Train a singing voice model from your own recordings — no pre-existing datasets, no third-party voice cloning. Just your mic, your voice, and an open-source stack.

This repo wraps the [OpenVPI](https://github.com/openvpi) ecosystem (DiffSinger, SOME, MFA) into a single reproducible workflow: record clips, label them, train, render.

> **[View the visual guide →](https://alanmaizon.github.io/my-voicebank/)**

---

## The pipeline at a glance

```
 Record WAVs ──→ Transcribe ──→ Align (MFA) ──→ Extract notes (SOME) ──→ Binarize ──→ Train ──→ Sing
```

Each step has a dedicated script. The CSV is your single source of truth — every script reads from it or writes back to it. Nothing is hidden in config files or scattered across directories.

## Setup

```bash
git clone https://github.com/<you>/my-voicebank.git && cd my-voicebank
bash scripts/bootstrap_tools.sh          # clone OpenVPI repos
bash scripts/create_envs.sh              # conda envs: diffsinger, some, mfa
bash scripts/download_assets.sh          # vocoder checkpoint
```

Three conda environments are created: `myvb-diffsinger` (training + inference), `myvb-some` (note extraction), `myvb-mfa` (forced alignment). Each is isolated so dependency conflicts stay out of your way.

## From recording to render

### Record

Sing short phrases (2–6 seconds each) into a decent mic. Dry, mono, 44.1 kHz. No reverb, no backing track. Rename clips to 6-digit IDs or let the rename script do it:

```bash
python scripts/batch_rename_clips.py datasets/my_singer/raw/wavs/
```

### Label

Scaffold an empty CSV, then type in the lyrics:

```bash
python scripts/scaffold_transcriptions.py \
    datasets/my_singer/raw/transcriptions.csv \
    datasets/my_singer/raw/wavs/
```

### Align

Turn lyrics into timed phoneme sequences using Montreal Forced Aligner:

```bash
python scripts/prepare_alignment_staging.py \
    datasets/my_singer/raw/transcriptions.csv \
    datasets/my_singer/raw/wavs/ \
    datasets/my_singer/exports/labs/staging/

mfa align datasets/my_singer/exports/labs/staging/ english_mfa english_mfa \
    datasets/my_singer/exports/labs/aligned/

python scripts/fill_ph_from_textgrids.py \
    datasets/my_singer/raw/transcriptions.csv \
    datasets/my_singer/exports/labs/aligned/
```

If MFA flags out-of-vocabulary words, you can supply a custom dictionary or use the `--spelling-map` option to remap informal spellings before alignment.

### Extract notes

SOME estimates pitch contours from audio and converts them into discrete note events:

```bash
python scripts/batch_some_infer.py \
    datasets/my_singer/raw/transcriptions.csv \
    datasets/my_singer/raw/wavs/ \
    models/some/0831_opencpop_ds1000.ckpt \
    --midi-dir datasets/my_singer/exports/midi/
```

### Train

Binarize the dataset inside `tools/DiffSinger/`, point your config at the data, and go:

```bash
cd tools/DiffSinger
python scripts/binarize.py --config configs/my_singer_acoustic.yaml
python scripts/train.py --config configs/my_singer_acoustic.yaml --exp_name my_singer_acoustic
```

A Colab notebook and a GCE setup script are included for GPU training — see `notebooks/` and `scripts/gce_train_setup.sh`.

### Render

Build a `.ds` inference file from one of your aligned clips, then run the acoustic model:

```bash
python scripts/make_ds_from_csv.py --clip 000001 \
    --csv datasets/my_singer/raw/transcriptions.csv

cd tools/DiffSinger
python scripts/infer.py acoustic ../../renders/000001.ds --exp my_singer_acoustic
```

---

## The CSV contract

Everything flows through `transcriptions.csv`. Eight columns, one row per clip:

| Column | Filled by | What it holds |
|--------|-----------|---------------|
| `name` | you | Clip ID — matches the WAV filename |
| `txt` | you | Sung lyrics for the clip |
| `ph_seq` | MFA | IPA phoneme sequence |
| `ph_dur` | MFA | Duration of each phoneme (seconds) |
| `ph_num` | MFA | Phone count per word group |
| `note_seq` | SOME | Note names (`C4`, `rest`, …) |
| `note_dur` | SOME | Duration of each note (seconds) |
| `comments` | you | QC flags — prefix with `exclude:` to skip a clip |

## Project layout

```
configs/              Training templates, spelling maps
datasets/<singer>/    raw/ (wavs + csv), exports/ (labs, midi, ds), qc/, backups/
models/               Pretrained checkpoints (vocoder, SOME, RMVPE)
tools/                Cloned OpenVPI repos (gitignored, bootstrapped locally)
scripts/              Everything that touches the pipeline
notebooks/            Colab training notebook
experiments/          Checkpoint output
renders/              Inference audio
```

## Things I learned the hard way

- **Back up the CSV before bulk writes.** The scripts overwrite in place.
- **Avoid commas in lyrics.** Easier than quoting CSV fields correctly.
- **50–100 clips is enough to start.** You can always record more after the first pass proves the pipeline works.
- **Mark bad clips with `exclude:` in comments** instead of deleting rows — keeps the audit trail intact.
- **GPU matters.** A T4 or L4 will train in hours; CPU will take days.

## Ethics

Only model voices you have consent to use. This toolkit is built for personal and creative work — not for cloning someone without their knowledge.

## License

MIT
