#!/usr/bin/env python3
"""
Builds the e-Vagbhata Jekyll site from evagbhata_data/*.json.

Differences from the Susruta/Caraka builder:
  - Three registers instead of two: root text ("mula"), Arunadatta's
    Sarvangasundara ("aruna"), Hemadri's Ayurvedarasayana ("hemadri").
    The split already happened in the scraper (at the DOM/span level),
    so this just maps each kind to its CSS class and a small label
    matching the print edition's own convention ("Sa." / "Ā. rā.").
  - No footnote/pāṭhāntara apparatus on this text -- diagnosis found
    zero <sup> tags. 'text'/'ref' segments are dropped rather than
    filed as notes; if a later sthāna does carry footnotes, the
    scraper's "unexpected FOOTNOTE REFS" flag will catch it before
    this build step is even run.
  - Same ISO 15919 -> IAST conversion as before (r̥->ṛ, ē->e, ō->o,
    etc.) -- this site's doIast() renderer produces the same
    combining-diacritic forms.

Usage (from the repo root, with evagbhata_data/ present):
    python3 build_evagbhata.py
"""

import json
import re
import unicodedata
from pathlib import Path

DATA_DIR = Path("evagbhata_data")
OUT_DIR = Path(".")

# (file_stem, slug, display_name, subtitle) -- order/names as they
# actually appear on the site (sharirasthana is 2nd, not 3rd).
STHANAS = [
    ("sutrasthana", "sutrasthana", "Sūtrasthāna", "General Principles"),
    ("sharirasthana", "sharirasthana", "Śārīrasthāna", "Anatomy"),
    ("nidanasthana", "nidanasthana", "Nidānasthāna", "Diagnosis"),
    ("cikitsasthana", "cikitsasthana", "Cikitsāsthāna", "Therapeutics"),
    ("kalpasiddhisthana", "kalpasiddhisthana", "Kalpasiddhisthāna", "Pharmaceutics"),
    ("uttarasthana", "uttarasthana", "Uttarasthāna", "Supplementary Section"),
]

# ISO 15919 -> IAST. Longest sequences first.
IAST_REPLACEMENTS = [
    ("r\u0325\u0304", "\u1E5D"), ("R\u0325\u0304", "\u1E5C"),
    ("r\u0325", "\u1E5B"),       ("R\u0325", "\u1E5A"),
    ("r\u0331", "\u1E5B"),       ("R\u0331", "\u1E5A"),
    ("\u1E41", "\u1E43"),        ("\u1E40", "\u1E42"),
    ("\u0113", "e"),             ("\u0112", "E"),
    ("\u014D", "o"),             ("\u014C", "O"),
]

CSS_CLASS = {"sloka": "mula", "vya_aruna": "aruna", "vya_hemadri": "hemadri"}
LABEL = {"sloka": None, "vya_aruna": "Sa.", "vya_hemadri": "Ā. rā."}


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
    return "Select Sthana" in text or "Select Chapter" in text or "Select  adhikaraṇam" in text


def build_chapter_html(segments):
    body = []
    current_kind = None
    buffer = []

    def flush():
        if not buffer:
            return
        content = mark_verses("".join(buffer).strip())
        if content:
            cls = CSS_CLASS[current_kind]
            label = LABEL.get(current_kind)
            label_html = f'<span class="commentator-label">{label}</span> ' if label else ""
            body.append(f'<div class="{cls}">{label_html}{content}</div>')
        buffer.clear()

    for seg in segments:
        kind, text = seg["k"], seg["t"]

        if kind in ("text", "ref"):
            # No footnote apparatus on this text (see module docstring);
            # anything falling here is boilerplate or an unexpected
            # footnote ref, either way not renderable content yet.
            continue

        if kind in ("sloka", "vya_aruna", "vya_hemadri"):
            if is_nav_boilerplate(text):
                continue
            if kind != current_kind:
                flush()
                current_kind = kind
            buffer.append(escape(text))

    flush()
    return "\n".join(body)


def build():
    summary = {}

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
            body_html = build_chapter_html(segments)

            if ch.get("counts", {}).get("ref", 0):
                print(f"  NOTE: {slug} {local_num} has {ch['counts']['ref']} "
                      f"footnote refs that this builder currently drops -- review.")

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

    print("Done.")


if __name__ == "__main__":
    build()
