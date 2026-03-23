#!/usr/bin/env python3
import argparse
import csv
import re
import unicodedata
from pathlib import Path


WORD_CHAR_RE = re.compile(r"[^a-z'\s-]+")
SPACE_RE = re.compile(r"\s+")
VOCALIZING_TAG_RE = re.compile(r"\[vocalizing\]", re.IGNORECASE)

# Sung/informal spellings → standard dictionary forms
SUNG_SPELLING_MAP = {
    "loomin": "looming",
    "goin": "going",
    "fuckin": "fucking",
    "thinkin": "thinking",
}


def normalize_english_text(text: str, drop_apostrophes: bool = False) -> str:
    text = VOCALIZING_TAG_RE.sub("", text)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("-", " ")
    text = text.lower()
    text = WORD_CHAR_RE.sub(" ", text)
    if drop_apostrophes:
        text = text.replace("'", "")
    else:
        # Keep apostrophes only when they appear inside a word.
        text = re.sub(r"(^|[^a-z])'+", r"\1", text)
        text = re.sub(r"'+([^a-z]|$)", r"\1", text)
    words = text.split()
    words = [SUNG_SPELLING_MAP.get(w, w) for w in words]
    text = " ".join(words)
    text = SPACE_RE.sub(" ", text).strip()
    return text


def ensure_symlink(src: Path, dst: Path):
    if dst.is_symlink():
        if dst.resolve() == src.resolve():
            return
        dst.unlink()
    elif dst.exists():
        raise FileExistsError(f"Refusing to replace non-symlink path: {dst}")
    dst.symlink_to(src.resolve())


def main():
    parser = argparse.ArgumentParser(
        description="Build an alignment staging folder with WAV symlinks and .lab files from transcriptions.csv"
    )
    parser.add_argument("csv_path", type=Path, help="Path to transcriptions.csv")
    parser.add_argument("wav_dir", type=Path, help="Directory containing source WAV files")
    parser.add_argument("out_dir", type=Path, help="Output staging directory")
    parser.add_argument(
        "--drop-apostrophes",
        action="store_true",
        help="Remove apostrophes from normalized labels",
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    with args.csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    preview_rows = []
    missing_txt_rows = []
    wordset = set()
    staged = 0

    for row in rows:
        name = (row.get("name") or "").strip()
        txt = (row.get("txt") or "").strip()
        if not name:
            continue

        wav_path = args.wav_dir / f"{name}.wav"
        if not wav_path.exists():
            raise FileNotFoundError(f"Missing WAV for row '{name}': {wav_path}")

        if not txt:
            missing_txt_rows.append({"name": name})
            continue

        normalized = normalize_english_text(txt, drop_apostrophes=args.drop_apostrophes)
        if not normalized:
            missing_txt_rows.append({"name": name})
            continue

        ensure_symlink(wav_path, args.out_dir / wav_path.name)
        (args.out_dir / f"{name}.lab").write_text(normalized + "\n", encoding="utf-8")

        preview_rows.append({
            "name": name,
            "txt": txt,
            "lab": normalized,
        })
        wordset.update(normalized.split())
        staged += 1

    preview_path = args.out_dir / "_lab_preview.csv"
    with preview_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["name", "txt", "lab"])
        writer.writeheader()
        writer.writerows(preview_rows)

    missing_path = args.out_dir / "_missing_txt.csv"
    with missing_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["name"])
        writer.writeheader()
        writer.writerows(missing_txt_rows)

    wordlist_path = args.out_dir / "_wordlist.txt"
    wordlist_path.write_text("\n".join(sorted(wordset)) + ("\n" if wordset else ""), encoding="utf-8")

    print(f"Staged {staged} clips in {args.out_dir}")
    print(f"Preview CSV: {preview_path}")
    print(f"Missing txt report: {missing_path}")
    print(f"Unique word list: {wordlist_path}")


if __name__ == "__main__":
    main()
