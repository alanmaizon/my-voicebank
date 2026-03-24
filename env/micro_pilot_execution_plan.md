# Micro-Pilot Execution Plan

Goal: prove the personal voicebank pipeline can go from fresh recordings to a first real DiffSinger acoustic checkpoint and one successful acoustic inference run.

This phase is not about quality. It is a tooling and dataset-contract proof.

## Scope

Use newly recorded dry room clips, not album stems, for this checkpoint.

Keep the scope narrow:

- one singer
- one room/setup
- one language / phoneme system
- one recording style
- one pretrained vocoder
- one tiny acoustic fine-tune run

Defer:

- full pilot corpus
- variance training
- SOME labeling
- custom vocoder work
- UI/editor work

## Clip Target

Target 18-24 final clips.

Recommended split:

- 6 low-range clips
- 6 mid-range clips
- 6 high-range clips
- 2-6 extra retakes or alternates for weak phoneme coverage

Recommended length per clip:

- 2-6 seconds

Hard limits:

- no clip longer than 10 seconds
- no long head/tail silence
- no backing track
- no doubled vocals
- no obvious room echo or processing

## Recording Prompt List

Record these as simple sung phrases on steady pitches or very small stepwise motion. Keep delivery plain and clean, not expressive.

Low range:

1. room
2. blue moon
3. slow fire
4. hold on
5. calm night
6. deep river

Mid range:

1. open window
2. steady light
3. over and over
4. never let go
5. little by little
6. I remember you

High range:

1. bright sky
2. stay with me
3. rising higher
4. carry me home
5. all I wanted
6. hear me now

Optional extra coverage:

1. room tone
2. breathe again
3. take it slow
4. under the water
5. how do I know
6. we were young

Prompt design rules:

- favor simple vowels and clear consonants
- include sustained vowels
- include plosives, fricatives, nasals, and liquids
- avoid tongue-twisters
- avoid extreme melisma
- avoid dramatic vibrato for this pass

## File And Dataset Targets

By the end of the micro-pilot, these should exist:

- `datasets/<singer>/raw/wavs/*.wav`
- `datasets/<singer>/raw/transcriptions.csv`
- `experiments/acoustic_ft_v0/` for run notes and config copies
- `tools/DiffSinger/checkpoints/acoustic_ft_v0/` with at least one checkpoint
- `renders/demos/acoustic_ft_v0_smoke.wav`

## Execution Order

### 1. Record and clean clips

- Record 18-24 dry mono clips.
- Rename final accepted clips to six-digit IDs.
- Put only accepted clips in `datasets/<singer>/raw/wavs/`.
- Add one CSV row per clip in `datasets/<singer>/raw/transcriptions.csv`.

Required CSV fields at this point:

- `name`
- `txt`

### 2. Prepare labels for alignment

- Create matching `.lab` files for each clip in a staging/alignment folder.
- Validate labels against the dictionary.
- Reformat WAVs if MFA needs 16kHz PCM input.

### 3. Run acoustic forced alignment

- Run MFA alignment.
- Check that every clip gets a TextGrid.
- Enhance TextGrids.
- Build the dataset from final TextGrids.
- Add `ph_num` after dataset build so the working CSV has the full future-proof contract.

Required CSV fields after this stage:

- `name`
- `ph_seq`
- `ph_dur`
- `ph_num`

Notes:

- `build_dataset.py` writes `ph_seq` and `ph_dur`.
- `ph_num` is a follow-up step in this repo, not part of the default build output.
- `note_seq` and `note_dur` are still deferred.

### 4. Train a tiny acoustic checkpoint

- Copy a minimal acoustic config into `experiments/acoustic_ft_v0/`.
- Point it at `datasets/<singer>/raw`.
- Keep validation small.
- Train only long enough to confirm binarization, checkpoint writing, and inference compatibility.

### 5. Run first acoustic inference

Use your own checkpoint, not a downloaded one.

For the first proof, a held-out re-synthesis is acceptable:

- choose one short aligned phrase
- build a minimal acoustic `.ds`/JSON input with `ph_seq`, `ph_dur`, `f0_seq`, and `f0_timestep`
- run `tools/DiffSinger/scripts/infer.py acoustic ... --exp acoustic_ft_v0`

This proves the acoustic model path works before variance labels exist.

## Pass / Fail Criteria

### Recording pass

Pass if:

- 18-24 usable clips exist in `raw/wavs/`
- every clip is dry, mono, and short
- clip names and CSV `name` values match exactly

Fail if:

- fewer than 15 usable clips remain after QC
- multiple clips still have long silence, clipping, bleed, or reverb
- filenames and CSV rows do not match

### Alignment pass

Pass if:

- label validation succeeds
- MFA launches and completes
- every accepted clip gets a TextGrid
- final `transcriptions.csv` has non-empty `ph_seq` and `ph_dur` for every row
- `ph_num` is added and its counts are consistent with each row's phoneme count

Fail if:

- any accepted clip is missing a label or TextGrid
- phoneme/duration lengths mismatch
- more than 10% of clips need heavy manual rescue

### Acoustic training pass

Pass if:

- the acoustic config resolves without path errors
- preprocessing/binarization completes on the micro-pilot dataset
- `tools/DiffSinger/checkpoints/acoustic_ft_v0/` contains `config.yaml` and at least one training checkpoint

Fail if:

- training cannot start from your config
- binarization crashes on the dataset
- no checkpoint is written

### First acoustic checkpoint pass

Pass only if all of these are true:

- the checkpoint was trained from your micro-pilot data
- `python scripts/infer.py acoustic ... --exp acoustic_ft_v0` completes without import or checkpoint errors
- the command writes one audio file under `renders/demos/`
- the render is audibly voiced and corresponds to the input phrase timing

Acceptable for this checkpoint:

- robotic timbre
- weak pronunciation
- unstable pitch in places
- obvious data scarcity artifacts

Fail this checkpoint if:

- inference only works with a downloaded checkpoint
- inference crashes on missing fields or incompatible config
- output is empty, all-noise, or clearly not speech/singing
- the repo cannot reproduce the same command on a second run

## Exact Milestone

You can say the acoustic path is proven when this sentence is true:

"I can record a small set of clips, align them into `ph_seq` / `ph_dur` / `ph_num`, train `acoustic_ft_v0`, and render one phrase with my own checkpoint."

## Immediate Next 3 Actions

1. Record 18-24 clean room clips from the prompt list above.
2. Populate `name` and `txt` rows in `datasets/<singer>/raw/transcriptions.csv`, then run alignment through final `ph_seq` / `ph_dur` / `ph_num`.
3. Train `acoustic_ft_v0` just long enough to produce one checkpoint and one successful acoustic inference render.
