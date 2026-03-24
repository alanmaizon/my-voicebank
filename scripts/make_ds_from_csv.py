#!/usr/bin/env python3
"""Build a .ds file from transcriptions.csv + original WAV for inference testing.

Usage:
    python make_ds_from_csv.py --clip 000004 --csv datasets/my_singer/raw/transcriptions.csv
"""
import argparse
import csv
import json
import pathlib
import numpy as np


def extract_f0_parselmouth(wav_path, sr=44100, hop_ms=5.0):
    """Extract F0 using Parselmouth (Praat) at 5ms intervals."""
    import parselmouth
    snd = parselmouth.Sound(str(wav_path))
    pitch = snd.to_pitch_ac(
        time_step=hop_ms / 1000.0,
        pitch_floor=65.0,
        pitch_ceiling=1100.0,
    )
    f0_values = []
    duration = snd.get_total_duration()
    n_frames = int(duration / (hop_ms / 1000.0))
    for i in range(n_frames):
        t = i * (hop_ms / 1000.0)
        f0 = pitch.get_value_at_time(t)
        if f0 is None or np.isnan(f0) or f0 == 0:
            f0 = 0.0
        f0_values.append(round(f0, 1))

    # Interpolate only *interior* gaps (between voiced frames).
    # Leading/trailing zeros stay at 0 so silence regions don't get pitch.
    f0_arr = np.array(f0_values, dtype=np.float64)
    voiced = np.where(f0_arr > 0)[0]
    if len(voiced) >= 2:
        first_v, last_v = voiced[0], voiced[-1]
        interior = slice(first_v, last_v + 1)
        sub = f0_arr[interior]
        v_mask = sub > 0
        if not v_mask.all():
            idx = np.arange(len(sub))
            sub[~v_mask] = np.interp(idx[~v_mask], idx[v_mask], sub[v_mask])
            f0_arr[interior] = sub
    return [round(v, 1) for v in f0_arr]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--clip', required=True, help='Clip name (e.g., 000004)')
    parser.add_argument('--csv', required=True, help='Path to transcriptions.csv')
    parser.add_argument('--wav', help='Path to WAV (auto-detected if omitted)')
    parser.add_argument('--out', help='Output .ds path (default: renders/<clip>.ds)')
    args = parser.parse_args()

    csv_path = pathlib.Path(args.csv)
    clip_name = args.clip

    # Find clip in CSV
    row = None
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r['name'] == clip_name:
                row = r
                break
    if row is None:
        raise ValueError(f'Clip {clip_name} not found in {csv_path}')

    # WAV path
    wav_path = pathlib.Path(args.wav) if args.wav else csv_path.parent / 'wavs' / f'{clip_name}.wav'
    if not wav_path.exists():
        raise FileNotFoundError(f'WAV not found: {wav_path}')

    print(f'Clip: {clip_name}')
    print(f'Text: {row.get("txt", "")}')
    print(f'WAV: {wav_path}')

    # Extract F0
    print('Extracting F0...')
    f0_seq = extract_f0_parselmouth(wav_path)
    print(f'F0 frames: {len(f0_seq)}')

    # Build .ds segment
    ph_seq = row['ph_seq']
    ph_dur = row['ph_dur']

    # Replace SP/AP with DiffSinger silence tokens
    # DiffSinger uses AP (aspiration) and SP (silence)
    # Our CSV already uses SP, but the first silence should be AP
    phones = ph_seq.split()
    if phones[0] == 'SP':
        phones[0] = 'AP'
    ph_seq_out = ' '.join(phones)

    # Zero F0 only in leading SP/AP and trailing silence regions.
    # Mid-phrase unvoiced consonants keep their interpolated F0 (matches training).
    # Find where the trailing silence starts: walk backwards from the end
    # past SP, AP, and any unvoiced consonants that precede them.
    UNVOICED = {'SP', 'AP', 'p', 'pʲ', 't', 'tʰ', 'tʲ', 'tʃ', 'k', 'kʰ',
                'c', 'cʰ', 'cʷ', 'f', 'fʲ', 's', 'ʃ', 'h', 'θ', 'ç',
                'ʈ', 'ʈʲ', 't̪'}
    durs = [float(d) for d in ph_dur.split()]
    hop_sec = 0.005
    f0_arr = list(f0_seq)

    # Find trailing unvoiced+silence boundary
    tail_start = len(phones)
    for j in range(len(phones) - 1, -1, -1):
        if phones[j] in UNVOICED:
            tail_start = j
        else:
            break

    # Find leading silence boundary
    head_end = 0
    for j in range(len(phones)):
        if phones[j] in ('SP', 'AP'):
            head_end = j + 1
        else:
            break

    # Zero F0 in leading and trailing regions
    cursor = 0.0
    for idx, (ph, dur) in enumerate(zip(phones, durs)):
        start_frame = int(round(cursor / hop_sec))
        end_frame = int(round((cursor + dur) / hop_sec))
        if idx < head_end or idx >= tail_start:
            for i in range(start_frame, min(end_frame, len(f0_arr))):
                f0_arr[i] = 0.0
        cursor += dur

    segment = {
        'offset': 0.0,
        'text': row.get('txt', ''),
        'ph_seq': ph_seq_out,
        'ph_dur': ph_dur,
        'ph_num': row.get('ph_num', ''),
        'note_seq': row.get('note_seq', ''),
        'note_dur': row.get('note_dur', ''),
        'f0_seq': ' '.join(str(v) for v in f0_arr),
        'f0_timestep': '0.005',
    }

    # Remove empty optional fields
    segment = {k: v for k, v in segment.items() if v}

    ds_data = [segment]

    # Output
    out_path = pathlib.Path(args.out) if args.out else pathlib.Path('renders') / f'{clip_name}.ds'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(ds_data, f, indent=2, ensure_ascii=False)

    print(f'Saved: {out_path}')
    print(f'Run inference with:')
    print(f'  python scripts/infer.py acoustic {out_path} --exp <your_exp_name>')


if __name__ == '__main__':
    main()
