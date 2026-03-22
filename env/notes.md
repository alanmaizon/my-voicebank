# Environment Notes

Use this file as the human-readable lab notebook for setup decisions.

## 2026-03-22 smoke test

- OS: macOS, shell: zsh
- Conda envs: `myvb-diffsinger`, `myvb-some`, `myvb-mfa`
- PyTorch import check in DiffSinger env: `conda run -n myvb-diffsinger python -c "import torch; print(torch.__version__)"`
- DiffSinger and SOME currently need `setuptools<81`; SOME also needs `pip<24.1` because `fairseq==0.12.2` depends on older `omegaconf` metadata.
- SOME CLI entry points now set writable cache dirs under `tools/SOME/.cache/` for `NUMBA_CACHE_DIR`, `MPLCONFIGDIR`, and `XDG_CACHE_HOME`.
- DiffSinger CLI entry points now set writable cache dirs under `tools/DiffSinger/.cache/` for `NUMBA_CACHE_DIR`, `MPLCONFIGDIR`, and `XDG_CACHE_HOME`.
- RMVPE upstream release currently ships `rmvpe.zip`, not a raw `rmvpe.pt`; `scripts/download_assets.sh` now accepts and extracts the zip by default.
- MFA launches cleanly when `MFA_ROOT_DIR` points at a writable directory. Known-good command:
  `MFA_ROOT_DIR=/tmp/myvb-mfa conda run -n myvb-mfa mfa --help`

Known-good SOME smoke command from repo root:

```bash
conda run -n myvb-some python tools/SOME/infer.py \
  --model models/some/0917_continuous256_clean_3spk/model_ckpt_steps_72000_simplified.ckpt \
  --wav tools/MakeDiffSinger/acoustic_forced_alignment/assets/2001000001.wav \
  --midi renders/demos/2001000001.some.mid
```

Known-good DiffSinger render command from `tools/DiffSinger/`:

```bash
conda run -n myvb-diffsinger python scripts/vocode.py \
  ../../renders/demos/diffsinger_vocoder_smoke.pt \
  --config configs/acoustic.yaml \
  --ckpt ../../models/vocoder/openvpi/pc_nsf_hifigan_44.1k_hop512_128bin_2025.02/model.ckpt \
  --out ../../renders/demos \
  --title diffsinger_vocoder_smoke
```

Note:

- The DiffSinger smoke render above is vocoder-only, driven by a synthetic mel payload at `renders/demos/diffsinger_vocoder_smoke.pt`.
- A full `scripts/infer.py acoustic ...` smoke test still needs a compatible acoustic checkpoint under `tools/DiffSinger/checkpoints/`.
