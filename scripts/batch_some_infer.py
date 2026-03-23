#!/usr/bin/env python3
"""Batch SOME inference: extract note_seq and note_dur for all clips."""
import argparse
import csv
import importlib
import pathlib
import sys

# Must run from tools/SOME directory with the myvb-some conda env python
from runtime import configure_runtime

configure_runtime()

import librosa
import numpy as np
import yaml

import inference
from utils.infer_utils import build_midi_file
from utils.slicer2 import Slicer

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def midi_to_note_name(midi_num):
    """Convert MIDI note number to name, e.g. 60 -> C4."""
    note = int(round(midi_num))
    return f"{NOTE_NAMES[note % 12]}{note // 12 - 1}"


def run_inference(infer_ins, config, wav_path):
    """Run SOME on one WAV file, return (note_seq, note_dur) strings."""
    waveform, _ = librosa.load(wav_path, sr=config["audio_sample_rate"], mono=True)
    slicer = Slicer(sr=config["audio_sample_rate"], max_sil_kept=1000)
    chunks = slicer.slice(waveform)
    segments = infer_ins.infer([c["waveform"] for c in chunks])

    # Flatten all segments into a single note sequence
    all_notes = []
    all_durs = []
    for offset_info, segment in zip(chunks, segments):
        note_midi = segment["note_midi"]
        note_dur = segment["note_dur"]
        note_rest = segment["note_rest"]

        for midi_val, dur, is_rest in zip(note_midi, note_dur, note_rest):
            if is_rest:
                all_notes.append("rest")
            else:
                all_notes.append(midi_to_note_name(midi_val))
            all_durs.append(round(float(dur), 6))

    note_seq = " ".join(all_notes)
    note_dur = " ".join(str(d) for d in all_durs)
    return note_seq, note_dur


def main():
    parser = argparse.ArgumentParser(description="Batch SOME inference")
    parser.add_argument("csv_path", type=pathlib.Path, help="Path to transcriptions.csv")
    parser.add_argument("wav_dir", type=pathlib.Path, help="Directory with WAV files")
    parser.add_argument("model_path", type=pathlib.Path, help="Path to SOME checkpoint")
    parser.add_argument(
        "--midi-dir",
        type=pathlib.Path,
        default=None,
        help="Optional: also save MIDI files here",
    )
    args = parser.parse_args()

    # Load model once
    with open(args.model_path.with_name("config.yaml"), "r", encoding="utf8") as f:
        config = yaml.safe_load(f)

    infer_cls = inference.task_inference_mapping[config["task_cls"]]
    pkg = ".".join(infer_cls.split(".")[:-1])
    cls_name = infer_cls.split(".")[-1]
    infer_cls = getattr(importlib.import_module(pkg), cls_name)
    infer_ins = infer_cls(config=config, model_path=args.model_path)

    # Read CSV
    with args.csv_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    fieldnames = list(rows[0].keys()) if rows else []

    if args.midi_dir:
        args.midi_dir.mkdir(parents=True, exist_ok=True)

    filled = 0
    skipped = 0
    errors = []

    for row in rows:
        name = row.get("name", "").strip()
        # Skip clips without ph_seq (vocalizing clips)
        if not row.get("ph_seq", "").strip():
            skipped += 1
            continue

        wav_path = args.wav_dir / f"{name}.wav"
        if not wav_path.exists():
            skipped += 1
            continue

        try:
            note_seq, note_dur = run_inference(infer_ins, config, wav_path)
            row["note_seq"] = note_seq
            row["note_dur"] = note_dur
            filled += 1

            if args.midi_dir:
                # Also save MIDI for inspection
                waveform, _ = librosa.load(
                    wav_path, sr=config["audio_sample_rate"], mono=True
                )
                slicer = Slicer(sr=config["audio_sample_rate"], max_sil_kept=1000)
                chunks = slicer.slice(waveform)
                segments = infer_ins.infer([c["waveform"] for c in chunks])
                midi_file = build_midi_file(
                    [c["offset"] for c in chunks], segments, tempo=120
                )
                midi_file.save(args.midi_dir / f"{name}.mid")

            if filled % 10 == 0:
                print(f"  Processed {filled} clips...", flush=True)
        except Exception as e:
            errors.append(f"{name}: {e}")

    # Write updated CSV
    with args.csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Filled {filled} clips, skipped {skipped}")
    if errors:
        print(f"Errors ({len(errors)}):")
        for e in errors:
            print(f"  {e}")


if __name__ == "__main__":
    main()
