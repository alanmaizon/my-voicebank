# Environment Notes

Use this file as the human-readable lab notebook for setup decisions.

## Setup tips

- Conda envs: `myvb-diffsinger`, `myvb-some`, `myvb-mfa` (created by `scripts/create_envs.sh`)
- DiffSinger and SOME currently need `setuptools<81`; SOME also needs `pip<24.1` because `fairseq==0.12.2` depends on older `omegaconf` metadata.
- SOME and DiffSinger CLI entry points set writable cache dirs under `tools/<tool>/.cache/` for `NUMBA_CACHE_DIR`, `MPLCONFIGDIR`, and `XDG_CACHE_HOME`.
- RMVPE upstream release ships `rmvpe.zip`, not a raw `rmvpe.pt`; `scripts/download_assets.sh` accepts and extracts the zip by default.
- MFA launches cleanly when `MFA_ROOT_DIR` points at a writable directory. Default is `~/Documents/MFA`.

## Smoke test commands

SOME inference from repo root:

```bash
/path/to/myvb-some/bin/python3 tools/SOME/infer.py \
  --model models/some/<checkpoint>.ckpt \
  --wav /path/to/test.wav \
  --midi renders/demos/test.some.mid
```

DiffSinger vocoder test from `tools/DiffSinger/`:

```bash
/path/to/myvb-diffsinger/bin/python3 scripts/vocode.py \
  ../../renders/demos/vocoder_smoke.pt \
  --config configs/acoustic.yaml \
  --ckpt ../../models/vocoder/openvpi/<vocoder_dir>/model.ckpt \
  --out ../../renders/demos \
  --title vocoder_smoke
```

Note: The vocoder test is vocoder-only, driven by a synthetic mel payload. A full `scripts/infer.py acoustic ...` test needs a trained acoustic checkpoint.
