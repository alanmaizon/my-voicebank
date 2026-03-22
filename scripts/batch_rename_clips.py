#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from datetime import datetime, UTC
from pathlib import Path


def natural_key(path: Path) -> list[object]:
    parts = re.split(r"(\d+)", path.stem)
    key: list[object] = []
    for part in parts:
        if not part:
            continue
        key.append(int(part) if part.isdigit() else part.lower())
    key.append(path.suffix.lower())
    return key


def next_start_id(wavs_dir: Path) -> int:
    numeric_ids = []
    for wav in wavs_dir.glob("*.wav"):
        if wav.stem.isdigit():
            numeric_ids.append(int(wav.stem))
    return (max(numeric_ids) + 1) if numeric_ids else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rename dataset clips to six-digit numeric IDs."
    )
    parser.add_argument(
        "wavs_dir",
        type=Path,
        help="Directory containing final dataset wav clips to rename.",
    )
    parser.add_argument(
        "--start-id",
        type=int,
        default=None,
        help="First numeric clip ID to assign. Defaults to the next free ID.",
    )
    parser.add_argument(
        "--mapping-out",
        type=Path,
        default=None,
        help="Optional CSV path for the rename mapping.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the planned renames without changing files.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    wavs_dir = args.wavs_dir.resolve()
    if not wavs_dir.is_dir():
        raise SystemExit(f"Not a directory: {wavs_dir}")

    source_files = [
        path for path in wavs_dir.glob("*.wav")
        if not (path.stem.isdigit() and len(path.stem) == 6)
    ]
    source_files.sort(key=natural_key)

    if not source_files:
        print("No non-numeric wav files found to rename.")
        return 0

    start_id = args.start_id if args.start_id is not None else next_start_id(wavs_dir)
    mapping_path = args.mapping_out
    if mapping_path is None:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        mapping_path = (
            wavs_dir.parent.parent / "qc" / f"rename_map_{timestamp}.csv"
        )

    planned_rows: list[tuple[Path, Path]] = []
    for offset, src in enumerate(source_files):
        clip_id = start_id + offset
        dst = src.with_name(f"{clip_id:06d}{src.suffix.lower()}")
        if dst.exists() and dst != src:
            raise SystemExit(f"Target already exists: {dst}")
        planned_rows.append((src, dst))

    print(f"Planning {len(planned_rows)} renames in {wavs_dir}:")
    for src, dst in planned_rows[:10]:
        print(f"  {src.name} -> {dst.name}")
    if len(planned_rows) > 10:
        print(f"  ... {len(planned_rows) - 10} more")

    if args.dry_run:
        print("Dry run only; no files changed.")
        return 0

    temp_rows: list[tuple[Path, Path, Path]] = []
    for index, (src, dst) in enumerate(planned_rows, start=1):
        temp = src.with_name(f".rename_tmp_{index:06d}{src.suffix.lower()}")
        src.rename(temp)
        temp_rows.append((temp, dst, src))

    try:
        for temp, dst, _src in temp_rows:
            temp.rename(dst)
    except Exception:
        for temp, _dst, src in reversed(temp_rows):
            if temp.exists():
                temp.rename(src)
        raise

    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    with mapping_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["original_name", "new_name"])
        for src, dst in planned_rows:
            writer.writerow([src.stem, dst.stem])

    print(f"Renamed {len(planned_rows)} files.")
    print(f"Mapping written to {mapping_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
