#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path


DEFAULT_FIELDS = [
    "name",
    "txt",
    "ph_seq",
    "ph_dur",
    "ph_num",
    "note_seq",
    "note_dur",
    "comments",
]


def load_existing_rows(csv_path: Path):
    if not csv_path.exists():
        return DEFAULT_FIELDS, {}

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or DEFAULT_FIELDS
        rows = {}
        for row in reader:
            name = (row.get("name") or "").strip()
            if name:
                rows[name] = row
    return fieldnames, rows


def load_rename_map(rename_map_path: Path | None):
    if rename_map_path is None or not rename_map_path.exists():
        return {}

    rename_map = {}
    with rename_map_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            new_name = (row.get("new_name") or "").strip()
            original_name = (row.get("original_name") or "").strip()
            if new_name and original_name:
                rename_map[new_name] = original_name
    return rename_map


def build_row(
    name: str,
    fieldnames: list[str],
    existing: dict | None,
    source_comment: str | None,
    fill_comments_from_rename_map: bool,
    clear_source_comments: bool,
):
    row = {field: "" for field in fieldnames}
    row["name"] = name

    if existing is not None:
        for field in fieldnames:
            if field in existing and existing[field] is not None:
                row[field] = existing[field]

    row["name"] = name

    if (
        clear_source_comments
        and "comments" in row
        and (row["comments"] or "").startswith("source: ")
    ):
        row["comments"] = ""

    if (
        fill_comments_from_rename_map
        and "comments" in row
        and not (row["comments"] or "").strip()
        and source_comment
    ):
        row["comments"] = f"source: {source_comment}"

    return row


def main():
    parser = argparse.ArgumentParser(
        description="Create or update transcriptions.csv with one row per WAV."
    )
    parser.add_argument("csv_path", type=Path, help="Path to transcriptions.csv")
    parser.add_argument("wav_dir", type=Path, help="Directory containing WAV files")
    parser.add_argument(
        "--rename-map",
        type=Path,
        default=None,
        help="Optional CSV mapping original_name,new_name",
    )
    parser.add_argument(
        "--fill-comments-from-rename-map",
        action="store_true",
        help="Backfill empty comments from the rename map",
    )
    parser.add_argument(
        "--clear-source-comments",
        action="store_true",
        help="Remove comments previously auto-filled as 'source: ...'",
    )
    args = parser.parse_args()

    wav_names = sorted(path.stem for path in args.wav_dir.glob("*.wav"))
    fieldnames, existing_rows = load_existing_rows(args.csv_path)
    rename_map = load_rename_map(args.rename_map)

    # Keep the repo's established header if present, but ensure any missing default
    # columns exist so we can safely scaffold future fields.
    for field in DEFAULT_FIELDS:
        if field not in fieldnames:
            fieldnames.append(field)

    rows = []
    for name in wav_names:
        rows.append(
            build_row(
                name=name,
                fieldnames=fieldnames,
                existing=existing_rows.get(name),
                source_comment=rename_map.get(name),
                fill_comments_from_rename_map=args.fill_comments_from_rename_map,
                clear_source_comments=args.clear_source_comments,
            )
        )

    args.csv_path.parent.mkdir(parents=True, exist_ok=True)
    with args.csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    preserved = sum(1 for name in wav_names if name in existing_rows)
    filled_comments = sum(
        1 for row in rows if (row.get("comments") or "").startswith("source: ")
    )
    print(
        f"Wrote {len(rows)} rows to {args.csv_path} "
        f"(preserved existing rows for {preserved} names, "
        f"backfilled {filled_comments} comments from rename map)."
    )


if __name__ == "__main__":
    main()
