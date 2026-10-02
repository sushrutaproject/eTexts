#!/usr/bin/env python3
"""
Builds the e-Suśruta Jekyll site from esushruta_data_v2/*.json.

What's new in v2:
  - Root text (Suśrutasaṃhitā) and commentary (Ḍalhaṇa's
    Nibandhasaṅgraha) are emitted as separate, class-tagged blocks,
    using the sloka_trans / vya_trans distinction that NIIMH's own
    markup carries.
  - Footnote references become real links to the notes at the foot of
    the chapter, with back-links.
  - The ISO->IAST conversion is applied here, so it no longer has to be
    run as a separate step after every rebuild.

Usage (from the repo root, with esushruta_data_v2/ present):
    python3 build_site_v2.py

Rewrites _<sthana>/*.html and _data/sthanas.yml.
"""

import json
import re
import unicodedata
from pathlib import Path

DATA_DIR = Path("esushruta_data_v2")
OUT_DIR = Path(".")

STHANAS = [
    ("sutrasthana", "sutrasthana", "Sūtrasthāna", "General Principles"),
    ("nidanasthana", "nidanasthana", "Nidānasthāna", "Diagnosis"),
    ("sharirasthana", "sharirasthana", "Śārīrasthāna", "Anatomy"),
    ("cikitsasthana", "cikitsasthana", "Cikitsāsthāna", "Therapeutics"),
    ("kalpasthana", "kalpasthana", "Kalpasthāna", "Toxicology & Pharmaceutics"),
    ("uttaratantra", "uttaratantra", "Uttaratantram", "Supplementary Section"),
]

# ISO 15919 -> IAST. Longest sequences first; see fix_iso_to_iast.py.
IAST_REPLACEMENTS = [
    ("r\u0325\u0304", "\u1E5D"), ("R\u0325\u0304", "\u1E5C"),
    ("r\u0325", "\u1E5B"),       ("R\u0325", "\u1E5A"),
    ("r\u0331", "\u1E5B"),       ("R\u0331", "\u1E5A"),
    ("\u1E41", "\u1E43"),        ("\u1E40", "\u1E42"),
    ("\u0113", "e"),             ("\u0112", "E"),
    ("\u014D", "o"),             ("\u014C", "O"),
]


def to_iast(text):
    for old, new in IAST_REPLACEMENTS:
        text = text.replace(old, new)
    return text


def slugify(text):
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    ascii_text = re.sub(r"^\d+\.\s*", "", ascii_text)
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return slug or "chapter"


def escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


VERSE_MARKER_RE = re.compile(r"(\|\|[\d,\-]+\|\|)")


def mark_verses(html):
    return VERSE_MARKER_RE.sub(r'<span class="verse-marker">\1</span>', html)


def is_nav_boilerplate(text):
    """The scraped #readContent begins with the page's own dropdown menus."""
    return "Select Sthana" in text or "Select Chapter" in text


def parse_notes(block):
    """Split the footnote block into numbered notes.

    NIIMH's data separates notes with '|', but not reliably: in
    Sūtrasthāna 1 alone, note 12 ends with a stray '0' instead, and note
    21 has no separator at all. So instead of splitting on the
    delimiter, walk the text and accept a 'N.' only when N is the number
    we're actually expecting next. That tolerates both glitches and
    ignores numerals that merely occur inside a note.
    """
    notes = []
    expected = 1
    pos = 0
    start = None
    for m in re.finditer(r"(\d+)\.", block):
        if int(m.group(1)) != expected:
            continue
        if start is not None:
            notes.append((expected - 1, block[start:m.start()]))
        start = m.end()
        expected += 1
        pos = m.end()
    if start is not None:
        notes.append((expected - 1, block[start:]))
    return [(n, clean_note(t)) for n, t in notes]


def clean_note(text):
    text = text.strip()
    text = re.sub(r"[|\s]+$", "", text)     # trailing separator/whitespace
    return text.strip()


def build_chapter_html(segments, chapter_slug):
    """Turn the ordered segments into register-tagged block HTML."""
    body = []
    current_kind = None
    buffer = []

    def flush():
        if not buffer:
            return
        cls = "mula" if current_kind == "sloka" else "bhasya"
        content = mark_verses("".join(buffer).strip())
        if content:
            body.append(f'<div class="{cls}">{content}</div>')
        buffer.clear()

    note_blocks = []
    after_ref = False

    for seg in segments:
        kind, text = seg["k"], seg["t"]

        if kind == "text":
            if is_nav_boilerplate(text):
                continue
            note_blocks.append(text)
            continue

        if kind == "ref":
            # References arrive as three segments: '[', 'N', ']'.
            n = text.strip()
            if not n.isdigit():
                continue
            if current_kind is None:
                continue
            buffer.append(
                f'<sup class="noteref" id="noteref-{chapter_slug}-{n}">'
                f'<a href="#note-{chapter_slug}-{n}">{n}</a></sup>'
            )
            after_ref = True
            continue

        if kind in ("sloka", "vya"):
            if kind != current_kind:
                flush()
                current_kind = kind
            # The scrape drops the whitespace node that follows a footnote
            # marker, so restore the space unless punctuation follows.
            if after_ref and text[:1] not in ("", " ", "|", ",", ".", ";", "!"):
                text = " " + text
            after_ref = False
            buffer.append(escape(text))

    flush()

    notes = parse_notes(" ".join(note_blocks)) if note_blocks else []
    if notes:
        items = []
        for n, t in notes:
            items.append(
                f'<li id="note-{chapter_slug}-{n}"><span class="note-num">{n}</span> '
                f'{mark_verses(escape(t))} '
                f'<a class="note-back" href="#noteref-{chapter_slug}-{n}" '
                f'aria-label="Back to reference {n}">&#8617;</a></li>'
            )
        body.append(
            '<section class="notes">\n<h2>pāṭhāntarāḥ</h2>\n<ol>\n'
            + "\n".join(items)
            + "\n</ol>\n</section>"
        )

    return "\n".join(body), len(notes)


def build():
    summary = {}
    problems = []

    for file_stem, slug, display_name, subtitle in STHANAS:
        matches = list(DATA_DIR.glob(f"sthana_*_{file_stem}.json"))
        if not matches:
            print(f"WARNING: no data file for {file_stem}")
            continue
        chapters = json.loads(matches[0].read_text(encoding="utf-8"))

        coll_dir = OUT_DIR / f"_{slug}"
        coll_dir.mkdir(parents=True, exist_ok=True)
        for old in coll_dir.glob("*.html"):
            old.unlink()

        for ch in chapters:
            local_title = to_iast(ch["title"].strip())
            m = re.match(r"^(\d+)\.\s*(.*)$", local_title)
            local_num = int(m.group(1)) if m else ch["adhyaya"]
            name_only = m.group(2) if m else local_title

            segments = [{"k": s["k"], "t": to_iast(s["t"])} for s in ch["segments"]]
            chapter_slug = f"{slug}-{local_num}"
            body_html, note_count = build_chapter_html(segments, chapter_slug)

            # Cross-check: every reference should have a matching note.
            ref_numbers = {
                int(s["t"]) for s in segments
                if s["k"] == "ref" and s["t"].strip().isdigit()
            }
            if ref_numbers and note_count != len(ref_numbers):
                problems.append(
                    f"{slug} {local_num}: {len(ref_numbers)} refs but {note_count} notes"
                )

            fname = f"{local_num:02d}-{slugify(name_only)}.html"
            front = (
                "---\n"
                f'title: "{local_title}"\n'
                f"adhyaya: {local_num}\n"
                f"order: {local_num}\n"
                "---\n"
            )
            (coll_dir / fname).write_text(front + body_html + "\n", encoding="utf-8")

        summary[slug] = len(chapters)
        print(f"{slug}: {len(chapters)} chapters")

    data_dir = OUT_DIR / "_data"
    data_dir.mkdir(exist_ok=True)
    lines = []
    for file_stem, slug, display_name, subtitle in STHANAS:
        if slug not in summary:
            continue
        lines.append(f"{slug}:")
        lines.append(f'  name: "{display_name}"')
        lines.append(f'  subtitle: "{subtitle}"')
        lines.append(f"  count: {summary[slug]}")
    (data_dir / "sthanas.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")

    if problems:
        print(f"\nReference/note mismatches ({len(problems)}):")
        for p in problems[:40]:
            print("  " + p)
    else:
        print("\nEvery footnote reference has a matching note.")
    print("Done.")


if __name__ == "__main__":
    build()
