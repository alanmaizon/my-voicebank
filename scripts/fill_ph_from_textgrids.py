#!/usr/bin/env python3
"""Read MFA TextGrids and fill ph_seq, ph_dur, ph_num in transcriptions.csv."""
import argparse
import csv
import re
from pathlib import Path


def parse_textgrid(path: Path):
    """Parse a Praat TextGrid file, return list of tiers.

    Each tier is a list of (xmin, xmax, text) tuples.
    """
    text = path.read_text(encoding="utf-8")
    tiers = []
    # Split into item blocks
    item_blocks = re.split(r"item\s*\[\d+\]:", text)
    for block in item_blocks[1:]:  # skip preamble
        intervals = []
        for m in re.finditer(
            r"xmin\s*=\s*([\d.]+)\s*\n\s*xmax\s*=\s*([\d.]+)\s*\n\s*text\s*=\s*\"([^\"]*)\"",
            block,
        ):
            intervals.append((float(m.group(1)), float(m.group(2)), m.group(3)))
        if intervals:
            tiers.append(intervals)
    return tiers


def extract_fields(tg_path: Path):
    """Extract ph_seq, ph_dur, ph_num from a TextGrid.

    - Phone tier empty intervals → SP
    - ph_num counts phones per word (SP between words gets its own count)
    """
    tiers = parse_textgrid(tg_path)
    if len(tiers) < 2:
        raise ValueError(f"Expected 2 tiers in {tg_path}, got {len(tiers)}")

    word_tier = tiers[0]  # (xmin, xmax, word)
    phone_tier = tiers[1]  # (xmin, xmax, phone)

    # Build ph_seq and ph_dur from phone tier
    ph_seq = []
    ph_dur = []
    for xmin, xmax, phone in phone_tier:
        label = phone.strip() if phone.strip() else "SP"
        ph_seq.append(label)
        ph_dur.append(round(xmax - xmin, 6))

    # Build ph_num: count phones per word-tier interval
    # Each word interval maps to the phone intervals that overlap it
    ph_num = []
    phone_idx = 0
    for wxmin, wxmax, wtext in word_tier:
        count = 0
        while phone_idx < len(phone_tier):
            pxmin, pxmax, _ = phone_tier[phone_idx]
            # Phone midpoint falls within this word interval
            pmid = (pxmin + pxmax) / 2
            if pmid < wxmax or (phone_idx == len(phone_tier) - 1 and pmid <= wxmax):
                count += 1
                phone_idx += 1
            else:
                break
        if count > 0:
            ph_num.append(count)

    # Sanity check: total phones in ph_num should equal len(ph_seq)
    if sum(ph_num) != len(ph_seq):
        raise ValueError(
            f"{tg_path.stem}: ph_num sum {sum(ph_num)} != ph_seq len {len(ph_seq)}"
        )

    return (
        " ".join(ph_seq),
        " ".join(str(d) for d in ph_dur),
        " ".join(str(n) for n in ph_num),
    )


def main():
    parser = argparse.ArgumentParser(
        description="Fill ph_seq, ph_dur, ph_num in transcriptions.csv from MFA TextGrids"
    )
    parser.add_argument("csv_path", type=Path, help="Path to transcriptions.csv")
    parser.add_argument("tg_dir", type=Path, help="Directory with .TextGrid files")
    args = parser.parse_args()

    with args.csv_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    fieldnames = list(rows[0].keys()) if rows else []

    filled = 0
    skipped = 0
    errors = []

    for row in rows:
        name = row.get("name", "").strip()
        tg_path = args.tg_dir / f"{name}.TextGrid"
        if not tg_path.exists():
            skipped += 1
            continue
        try:
            ph_seq, ph_dur, ph_num = extract_fields(tg_path)
            row["ph_seq"] = ph_seq
            row["ph_dur"] = ph_dur
            row["ph_num"] = ph_num
            filled += 1
        except Exception as e:
            errors.append(f"{name}: {e}")

    with args.csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Filled {filled} clips, skipped {skipped} (no TextGrid)")
    if errors:
        print(f"Errors ({len(errors)}):")
        for e in errors:
            print(f"  {e}")


if __name__ == "__main__":
    main()
