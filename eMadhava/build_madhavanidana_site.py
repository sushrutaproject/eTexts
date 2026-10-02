#!/usr/bin/env python3
"""
Builds the e-Mādhavanidāna Jekyll site from
madhavanidana_data/madhavanidana.json.

Differences from build_site_v2.py (the e-Suśruta builder this was
adapted from):

  - No sthāna collections: a single flat `_nidanas/` collection, one file
    per adhyāya. No _data/sthanas.yml is written or needed.
  - THREE registers instead of two: root text ("mula"), and two
    commentaries ("madhukosha", "atankadarpana") that arrive already
    distinguished in the source JSON (the scraper told them apart by
    colour). They become <div class="bhasya bhasya-madhukosha"> /
    <div class="bhasya bhasya-atankadarpana"> -- both still match the
    generic .bhasya CSS rule (size/indent, and the show/hide toggle),
    with a modifier class adding only a quiet, differently-coloured left
    rule per commentary.
  - Notes are read DIRECTLY from the scraped `notes` dict, keyed by
    number -- no heuristic "expected sequential numbering" parser is
    needed here, because the scraper already isolated each note's text
    by its own id (foot_match_N) rather than splitting a flattened
    footnote-block string.
  - Any leftover "text"-kind segment (which shouldn't exist -- everything
    should be classified as mula/madhukosha/atankadarpana/ref) is dropped
    and printed as a warning rather than silently included, since it
    indicates something in the source wasn't excluded that should have
    been.
  - A chapter with no extracted text at all (currently: 44 and 58) gets a
    short placeholder notice instead of an empty page.

Usage (from the repo root, with madhavanidana_data/ present):
    python3 build_madhavanidana_site.py

Rewrites _nidanas/*.html.
"""

import json
import re
import unicodedata
from pathlib import Path

DATA_PATH = Path("madhavanidana_data/madhavanidana.json")
OUT_DIR = Path(".")
COLLECTION_DIR = OUT_DIR / "_nidanas"

# ISO 15919 -> IAST. Longest sequences first; same table as the other
# three texts in this series.
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


REGISTER_CLASS = {
    "mula": "mula",
    "madhukosha": "bhasya bhasya-madhukosha",
    "atankadarpana": "bhasya bhasya-atankadarpana",
}


def build_chapter_html(segments, notes, chapter_slug, adhyaya_num):
    if not segments:
        return (
            '<p class="no-text-notice">No text could be extracted for this '
            "chapter from the source. This appears to be a gap in NIIMH's "
            "own digitized edition rather than a problem with this site's "
            "extraction -- see the About page.</p>"
        ), 0

    body = []
    current_kind = None
    buffer = []
    warnings = []

    def flush():
        if not buffer:
            return
        cls = REGISTER_CLASS.get(current_kind)
        content = mark_verses("".join(buffer).strip())
        if cls and content:
            body.append(f'<div class="{cls}">{content}</div>')
        buffer.clear()

    after_ref = False

    for seg in segments:
        kind, text = seg["k"], seg["t"]

        if kind == "text":
            t = text.strip()
            if t:
                warnings.append(t[:80])
                # Genuine content the source left untagged and
                # untransliterated (confirmed case: adhyāya 21, a clause
                # sitting as bare text between two footnote markers with
                # no span/hidden-div pair at all) is kept rather than
                # dropped -- inherited into whatever register is
                # currently open, shown in the site's own internal ASCII
                # scheme since we can't safely guess its IAST, and
                # flagged visually so it's never mistaken for ordinary
                # transliterated text.
                if current_kind is not None:
                    buffer.append(
                        f'<span class="untransliterated" '
                        f'title="Untransliterated in source (shown in original ASCII romanization)">'
                        f'{escape(text)}</span>'
                    )
            continue

        if kind == "ref":
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

        if kind in REGISTER_CLASS:
            if kind != current_kind:
                flush()
                current_kind = kind
            if after_ref and text[:1] not in ("", " ", "|", ",", ".", ";", "!"):
                text = " " + text
            after_ref = False
            buffer.append(escape(text))

    flush()

    if warnings:
        print(f"  *** {chapter_slug}: {len(warnings)} untagged source fragment(s) kept "
              f"inline (flagged, not transliterated), e.g. {warnings[0]!r} -- "
              f"worth a manual look ***")

    if notes:
        items = []
        for n in sorted(notes, key=lambda x: int(x)):
            t = to_iast(notes[n]).strip()
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
    chapters = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    chapters.sort(key=lambda c: c["adhyaya"])

    COLLECTION_DIR.mkdir(parents=True, exist_ok=True)
    for old in COLLECTION_DIR.glob("*.html"):
        old.unlink()

    problems = []

    for ch in chapters:
        local_num = ch["adhyaya"]
        local_title = to_iast(ch["title"].strip())
        m = re.match(r"^(\d+)\.\s*(.*)$", local_title)
        name_only = m.group(2) if m else local_title

        segments = [{"k": s["k"], "t": to_iast(s["t"])} for s in ch["segments"]]
        chapter_slug = f"nidana-{local_num}"
        body_html, note_count = build_chapter_html(segments, ch.get("notes", {}), chapter_slug, local_num)

        ref_numbers = {
            int(s["t"]) for s in segments
            if s["k"] == "ref" and s["t"].strip().isdigit()
        }
        if ref_numbers and note_count != len(ref_numbers):
            problems.append(
                f"adhyāya {local_num}: {len(ref_numbers)} refs but {note_count} notes"
            )

        fname = f"{local_num:02d}-{slugify(name_only)}.html"
        front = (
            "---\n"
            f'title: "{local_title}"\n'
            f"adhyaya: {local_num}\n"
            f"order: {local_num}\n"
            "---\n"
        )
        (COLLECTION_DIR / fname).write_text(front + body_html + "\n", encoding="utf-8")

    print(f"nidanas: {len(chapters)} chapters written to {COLLECTION_DIR}/")

    if problems:
        print(f"\nReference/note mismatches ({len(problems)}):")
        for p in problems[:40]:
            print("  " + p)
    else:
        print("\nEvery footnote reference has a matching note.")
    print("Done.")


if __name__ == "__main__":
    build()
