# Smoke Test

Use this checklist before recording the real pilot corpus. The goal is to prove the repo can bootstrap cleanly and that one reproducible toolchain survives basic setup, asset download, and a first inference pass.

## Default Run Order

From the repo root:

```bash
bash scripts/bootstrap_tools.sh
bash scripts/create_envs.sh
DOWNLOAD_SOME_MODEL=1 DOWNLOAD_RMVPE=1 bash scripts/download_assets.sh
```

Default env names:

- `myvb-diffsinger`
- `myvb-some`
- `myvb-mfa`

If you used `micromamba` or `mamba` instead of `conda`, swap that command name into the examples below.

## Checklist

- [ ] DiffSinger env created
- [ ] SOME env created
- [ ] MFA env created
- [ ] vocoder downloaded
- [ ] test inference rendered
- [ ] SOME test run completed
- [ ] pilot dataset folder populated

## Quick Validation Commands

Environment checks:

```bash
conda run -n myvb-diffsinger python -c "import torch; print(torch.__version__)"
conda run -n myvb-some python tools/SOME/infer.py --help
conda run -n myvb-mfa mfa --help
```

Asset checks:

```bash
find models/vocoder -maxdepth 3 -type f | sort
find models/some -maxdepth 3 -type f | sort
find tools/SOME/pretrained -maxdepth 2 -type f | sort
```

## DiffSinger Smoke Test

Use the current upstream inference flow from `tools/DiffSinger` and save the first render under `renders/demos/`. The minimum success bar for this checkpoint is:

- the DiffSinger env imports PyTorch cleanly
- the selected vocoder asset is present under `models/vocoder/openvpi/`
- one inference command completes and writes an audio file

Record the exact command that worked in `env/notes.md`.

## SOME Smoke Test

Use a short dry mono WAV and a downloaded SOME checkpoint:

```bash
conda run -n myvb-some python tools/SOME/infer.py \
  --model models/some/<some-checkpoint> \
  --wav <path-to-test.wav>
```

Success means the command runs without import errors and writes a MIDI output for the test WAV.

If RMVPE was downloaded, it should live under `tools/SOME/pretrained/`.

## Dataset Safety Check

Before using `batch_infer.py --overwrite`, make a backup:

```bash
cp datasets/<singer>/raw/transcriptions.csv \
  datasets/<singer>/backups/transcriptions.smoke-test.csv
```

Then confirm the input dataset already has:

- `name`
- `ph_seq`
- `ph_dur`
- `ph_num`

That is the minimum contract before SOME adds `note_seq` and `note_dur`.

## Pilot Gate

Do not move to a full corpus until these are true:

- the scripts run cleanly on your machine
- one DiffSinger inference completes
- one SOME inference completes
- MFA launches
- the repo structure still matches the expected `raw/wavs/` plus `transcriptions.csv` workflow
