#!/usr/bin/env python3
import argparse
import csv
import json
import os
import re
import unicodedata
from pathlib import Path


WORD_CHAR_RE = re.compile(r"[^a-z'\s-]+")
SPACE_RE = re.compile(r"\s+")
VOCALIZING_TAG_RE = re.compile(r"\[vocalizing\]", re.IGNORECASE)


def load_spelling_map(path: str | None = None) -> dict[str, str]:
    """Load sung/informal spelling -> standard dictionary form mappings.

    Reads from a JSON file (key->value pairs). Path can be passed explicitly
    or set via the SUNG_SPELLING_MAP environment variable.
    Returns an empty dict if no file is configured.
    """
    path = path or os.environ.get("SUNG_SPELLING_MAP")
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Spelling map not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def normalize_english_text(
    text: str, drop_apostrophes: bool = False, spelling_map: dict[str, str] | None = None
) -> str:
    if spelling_map is None:
        spelling_map = {}
    text = VOCALIZING_TAG_RE.sub("", text)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
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
    words = [spelling_map.get(w, w) for w in words]
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
    parser.add_argument(
        "--spelling-map",
        type=str,
        default=None,
        help="Path to JSON file mapping informal spellings to dictionary forms (or set SUNG_SPELLING_MAP env var)",
    )
    args = parser.parse_args()

    spelling_map = load_spelling_map(args.spelling_map)

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

        normalized = normalize_english_text(txt, drop_apostrophes=args.drop_apostrophes, spelling_map=spelling_map)
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
