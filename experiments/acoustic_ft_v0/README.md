# acoustic_ft_v0

This experiment folder tracks the first throwaway acoustic fine-tune for the micro-pilot.

Success for `acoustic_ft_v0` means:

- the 6-clip starter set aligns cleanly
- `transcriptions.csv` is populated with `name`, `ph_seq`, `ph_dur`, and `ph_num`
- DiffSinger writes at least one checkpoint under `tools/DiffSinger/checkpoints/acoustic_ft_v0/`
- one acoustic inference command completes and writes a render under `renders/demos/acoustic_ft_v0/`

This run is for pipeline proof, not model quality.

