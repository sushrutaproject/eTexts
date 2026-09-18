#!/usr/bin/env python3
"""
Converts the site's text from ISO 15919-flavored romanization to standard
IAST, in place, recursively.

Rules (order matters -- longest sequences first):
  r + COMBINING RING BELOW + COMBINING MACRON  ->  ṝ   (long vocalic r)
  r + COMBINING RING BELOW                     ->  ṛ   (short vocalic r)
  r + COMBINING MACRON BELOW                   ->  ṛ   (same sound; found
                                                          used inconsistently
                                                          in the source data,
                                                          e.g. in "nairṛta")
  ṁ (dot above)                                ->  ṃ   (dot below, anusvara)
  ē                                            ->  e
  ō                                            ->  o
Uppercase equivalents are handled too, in case they show up in titles.

Usage:
    python3 fix_iso_to_iast.py [root_dir]

root_dir defaults to the current directory. Walks all .html and .md files
under it and edits them in place. Prints a summary of how many
replacements of each kind were made, and in how many files.
"""

import sys
from pathlib import Path

REPLACEMENTS = [
    ("r\u0325\u0304", "\u1E5D"),  # r + ring below + macron -> ṝ
    ("R\u0325\u0304", "\u1E5C"),  # -> Ṝ
    ("r\u0325", "\u1E5B"),        # r + ring below -> ṛ
    ("R\u0325", "\u1E5A"),        # -> Ṛ
    ("r\u0331", "\u1E5B"),        # r + macron below -> ṛ (alt. encoding found in source)
    ("R\u0331", "\u1E5A"),        # -> Ṛ
    ("\u1E41", "\u1E43"),         # ṁ -> ṃ
    ("\u1E40", "\u1E42"),         # Ṁ -> Ṃ
    ("\u0113", "e"),              # ē -> e
    ("\u0112", "E"),              # Ē -> E
    ("\u014D", "o"),              # ō -> o
    ("\u014C", "O"),              # Ō -> O
]


def convert(text):
    counts = {}
    for old, new in REPLACEMENTS:
        n = text.count(old)
        if n:
            counts[old] = n
            text = text.replace(old, new)
    return text, counts


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    files = list(root.rglob("*.html")) + list(root.rglob("*.md"))

    total_counts = {}
    files_changed = 0

    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"  skipping (not UTF-8): {f}")
            continue

        new_text, counts = convert(text)
        if counts:
            f.write_text(new_text, encoding="utf-8")
            files_changed += 1
            for k, v in counts.items():
                total_counts[k] = total_counts.get(k, 0) + v

    print(f"Scanned {len(files)} files, changed {files_changed}.")
    if total_counts:
        print("Replacements made:")
        for k, v in sorted(total_counts.items(), key=lambda kv: -kv[1]):
            print(f"  {k!r} -> x{v}")
    else:
        print("No matches found -- nothing changed.")


if __name__ == "__main__":
    main()
