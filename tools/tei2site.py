#!/usr/bin/env python3
"""
tei2site.py -- turn one TEI file into a complete eTexts reading site.

    python3 tools/tei2site.py SRC_DIR OUT_DIR [--meta META.json]

SRC_DIR is a folder of the eTexts repository that holds one TEI file
(and optionally a `text.yml` with overrides, see README). OUT_DIR is
written from scratch as a Jekyll site in the same form as the
hand-built texts (eSushruta etc.), ready for build.rb to build. META
receives the details the collection home page needs (title, blurb...).

The converter is deliberately tolerant: TEI from different projects
(our own eTexts downloads, SARIT, GRETIL-style files, private
transcriptions) encodes the same things in different ways. What it
looks for:

  structure   <div>s in <body>. Sections (sthāna, khaṇḍa...) and
              chapters (adhyāya...) are recognised from @type/@subtype
              where possible, otherwise from the nesting and size of
              the divs. Deeper divs become sub-headings in a chapter.
  registers   mūla vs commentary, from @type/@subtype/@ana of a block
              element (div, ab, p, lg, quote...): e.g. mula, base-text,
              root, sūtra / commentary, commentary1, bhāṣya, ṭīkā...
              Blocks next to an explicit mūla block default to
              commentary; everything else defaults to mūla.
  notes       every non-empty <note>, and the readings of <app>,
              become footnotes (searchable as "Notes").
  script      Devanagari text is transliterated to IAST.

Nothing is silently dropped: unfamiliar elements are rendered as plain
text, and are listed in the report printed at the end.
"""

import argparse
import collections
import html
import json
import re
import shutil
import statistics
import unicodedata
from pathlib import Path

import yaml
from lxml import etree

TEI = "http://www.tei-c.org/ns/1.0"
XML = "http://www.w3.org/XML/1998/namespace"
HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "tei-template"

# --------------------------------------------------------------------------
# Vocabulary
# --------------------------------------------------------------------------

def norm(s):
    """lower-case, strip diacritics and '#', for matching attribute values"""
    s = unicodedata.normalize("NFD", (s or "").strip().lstrip("#").lower())
    return "".join(c for c in s if not unicodedata.combining(c))

MULA_WORDS = {"mula", "root", "root-text", "roottext", "base-text", "basetext",
              "base", "sutra", "karika", "mulapatha", "text-mula"}
COMM_RE = re.compile(r"^(commentary|comm|bhasya|vyakhya|tika|vrtti|vivarana|"
                     r"panjika|dipika|tippani|tippana|gloss|autocommentary|"
                     r"auto-commentary|svavrtti|subcommentary)[\w-]*$")
SECTION_WORDS = {"sthana", "khanda", "part", "book", "kanda", "tantra", "parvan",
                 "level1", "section", "anga", "pada-group"}
CHAPTER_WORDS = {"adhyaya", "adhyayah", "chapter", "patala", "sarga", "ullasa",
                 "prakarana", "taranga", "pariccheda", "vimarsa", "level2",
                 "lambaka", "ahnika", "vilasa", "adhikara"}

BLOCK_TAGS = {"p", "ab", "lg", "l", "list", "table", "head", "trailer", "label",
              "epigraph", "closer", "opener", "byline", "dateline", "salute",
              "signed", "argument", "sp", "speaker", "stage", "figure", "castList",
              "bibl", "listBibl", "docAuthor", "docTitle", "titlePart"}
CONTAINER_TAGS = {"div", "quote", "cit", "floatingText", "group", "text", "body",
                  "front", "back", "div1", "div2", "div3", "div4", "div5", "lg-group"}
SKIP_TAGS = {"teiHeader", "facsimile", "standOff", "fw", "figDesc", "graphic",
             "binaryObject", "surplus", "metamark", "interp", "interpGrp", "link",
             "linkGrp", "join", "timeline", "alt", "altGrp", "spanGrp", "witDetail"}


def local(el):
    return etree.QName(el).localname if isinstance(el.tag, str) else None


def classify(el):
    """('m'|'c'|None, raw attribute value that decided it)"""
    for attr in ("type", "subtype", "ana"):
        v = el.get(attr)
        if not v:
            continue
        for word in v.split():
            w = norm(word)
            if w in MULA_WORDS:
                return "m", word
            if COMM_RE.match(w):
                return "c", word
    return None, None


def div_kind_words(el):
    return {norm(el.get("type")), norm(el.get("subtype"))} - {""}


# --------------------------------------------------------------------------
# Transliteration and text helpers
# --------------------------------------------------------------------------

class Translit:
    def __init__(self, on):
        self.on = on
        if on:
            from indic_transliteration import sanscript
            self._t = lambda s: sanscript.transliterate(s, sanscript.DEVANAGARI, sanscript.IAST)

    def __call__(self, s):
        if not self.on or not s or not re.search("[ऀ-ॿ]", s):
            return s
        out = self._t(s)
        return out.replace("~", "m̐")          # candrabindu


VERSE_RE = re.compile(
    r"(\|\|?\s*[\w.,\-–]*\d[\w.,\-–]*\s*\|\|?|//\s*[\w.,;:\-–]*\d[\w.,;:\-–]*\s*//)")


def text_html(s, tr):
    """transliterate, escape, mark verse numbers, neutralise Liquid"""
    s = html.escape(tr(s), quote=False)
    s = VERSE_RE.sub(lambda m: '<span class="verse-marker">' + m.group(1) + "</span>", s)
    return s.replace("{{", "&#123;&#123;").replace("{%", "&#123;%")


def clean_ws(s):
    return re.sub(r"\s+", " ", s or "").strip()


def plain_text(el, tr, skip=("note",)):
    """readable text of an element, without notes"""
    parts = []

    def walk(e):
        if local(e) in skip or local(e) in SKIP_TAGS:
            if e.tail:
                parts.append(e.tail)
            return
        if e.text:
            parts.append(e.text)
        for c in e:
            walk(c)
        if e is not el and e.tail:
            parts.append(e.tail)
    walk(el)
    return clean_ws(tr("".join(parts)))


def slugify(s, fallback):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:40].strip("-")
    if not s or s[0].isdigit():
        s = fallback
    return s


# --------------------------------------------------------------------------
# Rendering one chapter
# --------------------------------------------------------------------------

class Chapter:
    def __init__(self, title, n):
        self.title = title
        self.n = n
        self.nodes = []        # (node, inherited_reg, inherited_comm) in order


class Renderer:
    def __init__(self, tr, comm_names, persons):
        self.tr = tr
        self.persons = persons                       # xml:id -> name, from the header
        self.unknown = collections.Counter()
        self.comm_keys = collections.OrderedDict()   # key -> display name
        self.comm_names = comm_names                 # overrides from text.yml
        self.stats = collections.Counter()

    # ---- commentary identity -------------------------------------------
    def comm_key(self, el, word):
        """a stable key per commentary: e.g. 'commentary1', 'nibandhasangraha'"""
        if norm(word) in ("commentary", "comm") or word != el.get("type"):
            for attr in ("subtype", "resp"):
                v = el.get(attr)
                if v and v != word:
                    return v.lstrip("#").split()[0]
            ana = (el.get("ana") or "").lstrip("#")
            if ana[:1].isupper():
                return ana
        return word.lstrip("#")

    def register_comm(self, key, el):
        if key not in self.comm_keys:
            name = None
            ana = (el.get("ana") or "").lstrip("#")
            resp = (el.get("resp") or "").split()
            if ana[:1].isupper():
                name = ana
            elif resp:
                names = [self.persons.get(r.lstrip("#")) for r in resp]
                if all(names):
                    # "A (Madhukośa)" + "B (Madhukośa)" -> "A and B (Madhukośa)"
                    tails = {re.search(r"(\s*\([^)]*\))?$", n).group(0) for n in names}
                    if len(names) > 1 and len(tails) == 1 and tails != {""}:
                        tail = tails.pop()
                        name = " and ".join(n[: len(n) - len(tail)] for n in names) + tail
                    else:
                        name = " and ".join(names)
            self.comm_keys[key] = name
        return list(self.comm_keys).index(key) + 1

    # ---- chapter -------------------------------------------------------
    def render_chapter(self, ch, cid):
        self.blocks = []          # [reg, comm, [html...]]
        self.notes = []           # (number, html)
        self.cid = cid
        self.pending = []         # page-break markers waiting for the next block
        regs_by_parent = {}
        for node, reg, comm in ch.nodes:
            if isinstance(node, str):
                self.inline_into_block(text_html(node, self.tr), reg, comm, loose=True)
                continue
            parent = node.getparent()
            if parent is not None and local(node) != "note":
                if parent not in regs_by_parent:
                    regs_by_parent[parent] = self.classify_children(parent, reg, comm)
                self.container_child(node, reg, comm, regs_by_parent[parent])
            else:
                self.container_child(node, reg, comm, None)
        out = []
        for reg, comm, parts in self.blocks:
            body = "".join(parts).strip()
            if not re.sub(r"<[^>]+>", "", body).strip():
                continue
            cls = "mula" if reg == "m" else "bhasya comm-%d" % comm
            out.append('<div class="%s">%s</div>' % (cls, body))
            self.stats["blocks_" + reg] += 1
        if self.notes:
            out.append('<section class="notes">\n<h2>Notes</h2>\n<ol>')
            for i, (num, body) in enumerate(self.notes, 1):
                out.append('<li id="note-%s-%d"><span class="note-num">%s</span> %s '
                           '<a class="note-back" href="#noteref-%s-%d" aria-label="Back to reference %s">&#8617;</a></li>'
                           % (cid, i, html.escape(num), body, cid, i, html.escape(num)))
            out.append("</ol>\n</section>")
            self.stats["notes"] += len(self.notes)
        return "\n".join(out) + "\n"

    # ---- blocks --------------------------------------------------------
    def new_block(self, reg, comm):
        if self.blocks and self.blocks[-1][0] == reg and self.blocks[-1][1] == comm:
            blk = self.blocks[-1]
        else:
            blk = [reg, comm, []]
            self.blocks.append(blk)
        if self.pending:
            blk[2].append("".join(self.pending))
            self.pending = []
        return blk

    def inline_into_block(self, frag, reg, comm, loose=False):
        if not frag.strip():
            if self.blocks:
                self.blocks[-1][2].append(" ")
            return
        blk = self.new_block(reg, comm)
        if loose:
            # loose text directly inside a container: keep it in a paragraph
            if blk[2] and blk[2][-1].startswith('<p class="loose">'):
                blk[2][-1] = blk[2][-1][:-4] + frag + "</p>"
            else:
                blk[2].append('<p class="loose">' + frag + "</p>")
        else:
            blk[2].append(frag)

    def classify_children(self, el, reg, comm):
        """registers for the children of a container; siblings of an
        explicit mūla block default to commentary"""
        kids = [c for c in el if isinstance(c.tag, str)]
        cls = [classify(c) for c in kids]
        has_mula = any(r == "m" for r, _ in cls)
        out = {}
        for c, (r, word) in zip(kids, cls):
            if r == "m":
                out[c] = ("m", comm)
            elif r == "c":
                if reg == "c":                      # nested: keep the outer commentary
                    out[c] = ("c", comm)
                else:
                    key = self.comm_key(c, word)
                    out[c] = ("c", self.register_comm(key, c))
            elif has_mula and reg == "m" and local(c) in BLOCK_TAGS - {"head", "label", "trailer"}:
                # untyped paragraphs/verses beside an explicit mūla block are
                # the commentary on it (untyped divs keep the outer register)
                key = "commentary"
                out[c] = ("c", self.register_comm(key, c))
            else:
                out[c] = (reg, comm)
        return out

    def container_child(self, el, reg, comm, regs):
        """an element met at block level"""
        tag = local(el)
        if tag is None:                               # comment / PI
            return
        if regs is not None:
            reg, comm = regs.get(el, (reg, comm))
        if tag in SKIP_TAGS:
            return
        if tag in CONTAINER_TAGS:
            self.container(el, reg, comm)
            return
        if tag == "head":
            title = self.inline_children(el)
            if title.strip():
                blk = self.new_block(reg, comm)
                blk[2].append('<p class="subhead">' + title + "</p>")
            return
        if tag in ("pb", "milestone"):
            self.pending.append(self.page_marker(el))
            return
        if tag == "note":
            ref = self.note(el)
            if ref:
                if self.blocks:
                    self.blocks[-1][2].append(ref)
                else:
                    self.pending.append(ref)
            return
        if tag in ("lb", "anchor", "caesura"):
            return
        if tag in BLOCK_TAGS or tag in ("app", "choice", "seg", "w", "s", "hi"):
            html_ = self.block_html(el)
            if html_ is not None:
                blk = self.new_block(reg, comm)
                blk[2].append(html_)
            return
        # anything else at block level: render as inline, in its own paragraph
        frag = self.inline(el, tail=False)
        self.inline_into_block(frag, reg, comm, loose=True)

    def container(self, el, reg, comm):
        regs = self.classify_children(el, reg, comm)
        if el.text and el.text.strip():
            self.inline_into_block(text_html(el.text, self.tr), reg, comm, loose=True)
        for c in el:
            self.container_child(c, reg, comm, regs)
            if c.tail and c.tail.strip():             # text after a child belongs to el
                self.inline_into_block(text_html(c.tail, self.tr), reg, comm, loose=True)

    def block_html(self, el):
        tag = local(el)
        inner = self.inline_children(el)
        if tag == "lg":
            return '<p class="lg">' + inner + "</p>"
        if tag == "l":
            return '<p class="lg"><span class="l">' + inner + "</span></p>"
        if tag == "trailer":
            return '<p class="trailer">' + inner + "</p>"
        if tag == "label":
            return '<p class="subhead">' + inner + "</p>"
        if tag == "list":
            return '<ul class="list">' + inner + "</ul>"
        if tag == "table":
            return '<p class="table">' + inner + "</p>"
        if tag == "sp":
            return '<p class="sp">' + inner + "</p>"
        return "<p>" + inner + "</p>"

    # ---- inline --------------------------------------------------------
    def inline_children(self, el):
        out = [text_html(el.text, self.tr) if el.text else ""]
        for c in el:
            out.append(self.inline(c))
        return "".join(out)

    def inline(self, el, tail=True):
        tag = local(el)
        t = (text_html(el.tail, self.tr) if (tail and el.tail) else "")
        if tag is None:
            return t
        if tag in SKIP_TAGS:
            return t
        if tag == "note":
            # an empty <note/> is a bare marker; it still separates words
            return (self.note(el) or " ") + t
        if tag in ("pb", "milestone"):
            return self.page_marker(el) + t
        if tag == "lb":
            return ("" if el.get("break") == "no" else " ") + t
        if tag == "caesura":
            return " " + t
        if tag in ("anchor", "index", "fw"):
            return t
        if tag == "gap":
            return '<span class="gap" title="gap in the source">[…]</span>' + t
        if tag == "app":
            return self.app(el) + t
        if tag == "choice":
            pick = None
            for want in ("corr", "reg", "expan", "seg"):
                pick = el.find("{%s}%s" % (TEI, want))
                if pick is not None:
                    break
            if pick is None and len(el):
                pick = el[0]
            return (self.inline_children(pick) if pick is not None else "") + t
        inner = self.inline_children(el)
        if tag == "l":
            return '<span class="l">' + inner + "</span>" + t
        if tag in ("lg", "p", "ab", "head", "trailer", "quote", "cit", "div", "sp", "epigraph", "floatingText"):
            return '<span class="blk">' + inner + "</span> " + t
        if tag == "label":
            if norm(el.get("type")) == "siglum" or el.getparent() is not None and classify(el.getparent())[0] == "c":
                return '<span class="commentator-label">' + inner + "</span>" + t
            return '<span class="label">' + inner + "</span>" + t
        if tag == "supplied":
            return '<span class="supplied">' + inner + "</span>" + t
        if tag == "unclear":
            return '<span class="unclear">' + inner + "</span>" + t
        if tag == "del":
            return "<del>" + inner + "</del>" + t
        if tag == "add":
            return '<span class="add">' + inner + "</span>" + t
        if tag == "sic":
            return inner + "<sup>[sic]</sup>" + t
        if tag == "hi":
            rend = (el.get("rend") or "").lower()
            if "bold" in rend:
                return "<strong>" + inner + "</strong>" + t
            if "sup" in rend:
                return '<span class="sup">' + inner + "</span>" + t
            return "<em>" + inner + "</em>" + t
        if tag in ("foreign", "title", "term", "mentioned", "emph", "soCalled", "gloss"):
            return "<em>" + inner + "</em>" + t
        if tag == "ref":
            target = el.get("target") or ""
            if target.startswith("http"):
                return '<a href="%s">%s</a>%s' % (html.escape(target), inner, t)
            return inner + t
        if tag == "item":
            return "<li>" + inner + "</li>" + t
        if tag in ("row",):
            return inner + "<br>" + t
        if tag in ("cell",):
            return inner + " " + t
        if tag in ("seg", "w", "s", "c", "pc", "q", "said", "name", "persName", "placeName",
                   "orgName", "num", "date", "measure", "rs", "abbr", "expan", "corr", "reg",
                   "orig", "lem", "rdg", "bibl", "author", "editor", "span", "phr", "m",
                   "unit", "time", "geogName", "objectName", "roleName", "addName",
                   "forename", "surname", "idno", "biblScope", "citedRange", "ptr",
                   "damage", "restore", "subst", "handShift", "space", "listBibl", "locus",
                   "dimensions", "material", "origPlace", "origDate", "secl", "sb", "zone",
                   "speaker", "stage", "figure", "table", "list", "quote", "cit"):
            if tag in ("ptr",):
                return t
            if tag == "space":
                return " " + t
            return inner + t
        self.unknown[tag] += 1
        return inner + t

    def page_marker(self, el):
        n = el.get("n")
        if not n:
            return ""
        unit = el.get("unit") or ("folio" if norm(el.get("type")) == "folio" else "p.")
        if local(el) == "milestone" and unit not in ("page", "folio", "p."):
            return ""
        label = ("f. " if "folio" in unit else "p. ") + n
        if el.get("ed"):
            label = el.get("ed").lstrip("#") + " " + label
        # a <sup>, so the search index leaves it out (see search-entry.json)
        return '<sup class="pb" title="page break">%s</sup>' % html.escape(label)

    def note(self, el):
        body = self.inline_children(el).strip()
        if not re.sub(r"<[^>]+>", "", body).strip():
            return None
        k = len(self.notes) + 1
        num = el.get("n") or str(k)
        self.notes.append((num, body))
        return ('<sup class="noteref" id="noteref-%s-%d"><a href="#note-%s-%d">%s</a></sup>'
                % (self.cid, k, self.cid, k, html.escape(num)))

    def app(self, el):
        lem = el.find("{%s}lem" % TEI)
        rdgs = el.findall(".//{%s}rdg" % TEI)
        shown = lem if lem is not None else (rdgs[0] if rdgs else None)
        main = self.inline_children(shown) if shown is not None else ""
        others = [r for r in rdgs if r is not shown]
        bits = []
        for r in others:
            txt = self.inline_children(r).strip() or "om."
            wit = " ".join(w.lstrip("#") for w in (r.get("wit") or "").split())
            bits.append(txt + (" " + html.escape(wit) if wit else ""))
        for nt in el.findall("{%s}note" % TEI):
            bits.append(self.inline_children(nt))
        ref = ""
        if bits:
            k = len(self.notes) + 1
            self.notes.append((str(k), "; ".join(bits)))
            ref = ('<sup class="noteref" id="noteref-%s-%d"><a href="#note-%s-%d">%d</a></sup>'
                   % (self.cid, k, self.cid, k, k))
        return '<span class="lem">' + main + "</span>" + ref


# --------------------------------------------------------------------------
# Structure: sections and chapters
# --------------------------------------------------------------------------

def is_structural(el):
    return local(el) in ("div", "div1", "div2", "div3", "div4") and classify(el)[0] is None


def struct_children(el):
    return [c for c in el if isinstance(c.tag, str) and is_structural(c)]


def head_title(el, tr):
    heads = [h for h in el if local(h) == "head"]
    best = None
    for h in heads:
        t = plain_text(h, tr).strip(" /|[]")
        if not re.search(r"[^\W\d_]", t):
            continue
        if h.get("{%s}lang" % XML, "").startswith("en") and best is None:
            best = ("en", t)
            continue
        return t, heads
    return (best[1] if best else ""), heads


def label_for(el, fallback_word, i):
    """'Sthāna 1', 'Adhyāya 3'... for a div without a usable <head>"""
    n = el.get("n") or str(i)
    w = ""
    for attr in ("subtype", "type"):
        v = (el.get(attr) or "").strip()
        if v and norm(v) not in ("level1", "level2", "level3", "unknown") and not v[-1].isdigit():
            w = v[:1].upper() + v[1:]
            break
    return "%s %s" % (w or fallback_word, n)


def text_len(el):
    return len(clean_ws("".join(el.itertext())))


def build_structure(body, tr, cfg, log):
    """-> list of sections: {name, chapters:[Chapter]}"""
    root = body
    # unwrap single wrapper divs
    while True:
        kids = struct_children(root)
        loose = [c for c in root if isinstance(c.tag, str) and not is_structural(c)
                 and local(c) not in ("head", "pb", "milestone", "lb", "anchor")
                 and text_len(c) > 0]
        if len(kids) == 1 and not loose and struct_children(kids[0]):
            root = kids[0]
        else:
            break

    L0 = struct_children(root)
    L1 = [c for d in L0 for c in struct_children(d)]

    level = cfg.get("chapter_level")
    if level is None:
        if L1 and any(div_kind_words(d) & CHAPTER_WORDS for d in L1):
            level = 1
        elif L0 and any(div_kind_words(d) & CHAPTER_WORDS for d in L0):
            level = 0
        elif L1 and statistics.median(text_len(d) for d in L1) >= 1500:
            level = 1
        elif L0:
            level = 0
        else:
            level = -1
    level = int(level)
    if level == 1 and not L1:
        level = 0
    if level == 0 and not L0:
        level = -1
    log("structure: %d top-level divs, %d second-level; chapters taken at level %s"
        % (len(L0), len(L1), {1: "2 (sections > chapters)", 0: "1 (chapters only)", -1: "none (one chapter)"}[level]))

    sections = []

    def gather(container, chapter_divs, sec, title_for_opening):
        """walk container; chapter_divs become chapters, everything else
        is attached to the preceding chapter (or an opening chapter)"""
        current = None
        lead_heads = True
        if container.text and container.text.strip():
            current = Chapter(title_for_opening, 0)
            sec["chapters"].append(current)
            current.nodes.append((container.text, "m", 0))
        for c in container:
            if c in chapter_divs:
                lead_heads = False
                i = len([x for x in sec["chapters"] if x.n]) + 1
                title, heads = head_title(c, tr)
                n = c.get("n")
                ch = Chapter(title or label_for(c, "Chapter", i), n if n and len(n) <= 6 else i)
                # chapter content: everything except the head used as its title
                # (notes inside that head are kept, at the top of the chapter)
                used = [h for h in heads if plain_text(h, tr).strip(" /|[]") == title][:1]
                skip = set(used)
                for h in used:
                    for nt in h.iter("{%s}note" % TEI):
                        ch.nodes.append((nt, "m", 0))
                if c.text and c.text.strip():
                    ch.nodes.append((c.text, "m", 0))
                for x in c:
                    if local(x) == "head" and not re.search(r"[^\W\d_]", plain_text(x, tr)):
                        skip.add(x)          # a bare number: the chapter badge shows it
                    if x in skip:
                        if x.tail and x.tail.strip():
                            ch.nodes.append((x.tail, "m", 0))
                        continue
                    ch.nodes.append((x, "m", 0))
                    if x.tail and x.tail.strip():
                        ch.nodes.append((x.tail, "m", 0))
                ch.container = c
                sec["chapters"].append(ch)
                current = ch
            else:
                if not isinstance(c.tag, str):
                    continue
                if lead_heads and local(c) == "head":   # the section's own title
                    continue
                if text_len(c) == 0 and local(c) not in ("pb", "milestone"):
                    continue
                if current is None:
                    current = Chapter(title_for_opening, 0)
                    sec["chapters"].insert(0, current)
                current.nodes.append((c, "m", 0))
                if c.tail and c.tail.strip():
                    current.nodes.append((c.tail, "m", 0))

    if level == 1:
        for i, d in enumerate(L0, 1):
            title, _ = head_title(d, tr)
            name = title or label_for(d, "Section", i)
            sec = {"name": name, "el": d, "chapters": []}
            kids = set(struct_children(d))
            gather(d, kids, sec, name + (" (opening)" if kids else ""))
            sections.append(sec)
        # loose material at the root level
        extra = [c for c in root if isinstance(c.tag, str) and c not in L0
                 and local(c) != "head" and text_len(c) > 0]
        if extra:
            sec = {"name": "Opening", "chapters": []}
            ch = Chapter("Opening matter", 0)
            for c in extra:
                ch.nodes.append((c, "m", 0))
            sec["chapters"].append(ch)
            sections.insert(0, sec)
            log("note: material outside the sections was put in an 'Opening' section")
    elif level == 0:
        sec = {"name": None, "chapters": []}
        gather(root, set(L0), sec, "Opening matter")
        sections.append(sec)
    else:
        sec = {"name": None, "chapters": []}
        ch = Chapter(cfg.get("work") or "Text", 1)
        ch.n = 1
        for c in root:
            if isinstance(c.tag, str) and local(c) != "head":
                ch.nodes.append((c, "m", 0))
        sec["chapters"].append(ch)
        sections.append(sec)

    # an 'opening' chapter with no text of its own (e.g. only a marginal
    # note or a page break) is folded into the chapter that follows it
    def has_text(ch):
        for node, _, _ in ch.nodes:
            if isinstance(node, str):
                if node.strip():
                    return True
            elif local(node) not in ("note", "pb", "milestone", "lb", "anchor") and \
                    plain_text(node, tr):
                return True
        return False
    for sec in sections:
        chs = sec["chapters"]
        for i in range(len(chs) - 2, -1, -1):
            if chs[i].n == 0 and not has_text(chs[i]):
                chs[i + 1].nodes[:0] = chs[i].nodes
                del chs[i]

    # number chapters within each section; 'opening' chapters get 0
    for sec in sections:
        sec["chapters"] = [c for c in sec["chapters"] if c.nodes]
        for k, ch in enumerate(sec["chapters"], 1):
            ch.order = k
            if not getattr(ch, "n", 0):
                ch.n = 0
    return [s for s in sections if s["chapters"]]


# --------------------------------------------------------------------------
# Header metadata
# --------------------------------------------------------------------------

def header_meta(tree, tr):
    h = tree.find(".//{%s}teiHeader" % TEI)
    q = lambda path: h.findall(path.replace("t:", "{%s}" % TEI)) if h is not None else []
    meta = {}
    titles = q(".//t:fileDesc/t:titleStmt/t:title")
    main = next((t for t in titles if t.get("type") == "main"), titles[0] if titles else None)
    sub = next((t for t in titles if t.get("type") == "sub"), None)
    meta["title_full"] = plain_text(main, tr, skip=()) if main is not None else ""
    meta["subtitle"] = plain_text(sub, tr, skip=()) if sub is not None else ""
    persons = {}
    authors, commentators = [], []
    for a in q(".//t:fileDesc/t:titleStmt/t:author"):
        xid = a.get("{%s}id" % XML)
        if xid:
            persons[xid] = plain_text(a, tr, skip=())
        (commentators if norm(a.get("role")) == "commentator" else authors).append(plain_text(a, tr, skip=()))
    meta["authors"], meta["commentators"], meta["persons"] = authors, commentators, persons
    meta["editors"] = [plain_text(e, tr, skip=()) for e in q(".//t:fileDesc/t:titleStmt/t:editor")]
    meta["resp"] = [(plain_text(r.find("{%s}resp" % TEI), tr, skip=()) if r.find("{%s}resp" % TEI) is not None else "",
                     clean_ws(" ".join(plain_text(x, tr, skip=()) for x in r if local(x) != "resp")))
                    for r in q(".//t:fileDesc/t:titleStmt/t:respStmt")]
    pub = q(".//t:fileDesc/t:publicationStmt")
    meta["publisher"] = ""
    meta["licence"] = ""
    meta["licence_url"] = ""
    meta["availability"] = []
    if pub:
        p = pub[0]
        for tag in ("publisher", "distributor", "authority"):
            e = p.find("{%s}%s" % (TEI, tag))
            if e is not None and plain_text(e, tr, skip=()):
                meta["publisher"] = plain_text(e, tr, skip=())
                break
        for lic in p.iter("{%s}licence" % TEI):
            meta["licence"] = plain_text(lic, tr, skip=())
            meta["licence_url"] = lic.get("target", "")
        for r in p.iter("{%s}ref" % TEI):
            if norm(r.get("type")) == "licence" or "creativecommons" in (r.get("target") or ""):
                meta["licence_url"] = meta["licence_url"] or r.get("target", "")
                meta["licence"] = meta["licence"] or plain_text(r, tr, skip=())
        av = p.find("{%s}availability" % TEI)
        if av is not None:
            meta["availability"] = [plain_text(x, tr, skip=()) for x in av if local(x) == "p" and plain_text(x, tr, skip=())]
    def bibl_text(b):
        """a <bibl>'s parts joined with commas: 'Title, Editor, Place, 1977'"""
        if not len(b):
            return plain_text(b, tr, skip=())
        parts = [clean_ws(tr(b.text or ""))] + [plain_text(c, tr, skip=()) + clean_ws(tr(c.tail or ""))
                                                 for c in b if isinstance(c.tag, str) and local(c) != "ptr"]
        return ", ".join(x.strip(" ,") for x in parts if x.strip(" ,"))
    meta["sources"] = []
    for b in q(".//t:fileDesc/t:sourceDesc//t:bibl") + q(".//t:fileDesc/t:sourceDesc//t:biblStruct"):
        txt = bibl_text(b)
        if txt and txt not in meta["sources"]:
            meta["sources"].append(txt)
    for p in q(".//t:fileDesc/t:sourceDesc/t:p"):
        txt = plain_text(p, tr, skip=())
        if txt:
            meta["sources"].append(txt)
    meta["changes"] = [(c.get("when") or "", c.get("who") or "", plain_text(c, tr, skip=()))
                       for c in q(".//t:revisionDesc//t:change")]
    meta["project"] = [plain_text(p, tr, skip=()) for p in q(".//t:encodingDesc/t:projectDesc/t:p")]
    meta["editorial"] = [plain_text(p, tr, skip=()) for p in q(".//t:encodingDesc/t:editorialDecl/t:p")]
    return meta


def split_title(full):
    """'Carakasaṃhitā with Cakrapāṇidatta's commentary [a machine-readable
    transcription]' -> ('Carakasaṃhitā', "with Cakrapāṇidatta's commentary")"""
    t = re.split(r"\s+\[|\s+from\s+|:\s+|\s+etext\b|\s+\(", full)[0].strip(" ,;")
    m = re.match(r"(.+?)\s+(with\s+.+)$", t)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return t, ""


# --------------------------------------------------------------------------
# Writing the site
# --------------------------------------------------------------------------

def yq(s):
    return json.dumps(s, ensure_ascii=False)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def find_tei(src, cfg):
    if cfg.get("tei"):
        p = src / cfg["tei"]
        if not p.exists():
            raise SystemExit("text.yml names tei: %s, which is not in the folder %s" % (cfg["tei"], src.name))
        return p
    xmls = sorted(p for p in src.glob("*.xml") if p.is_file())
    teis = []
    for p in xmls:
        with open(p, "rb") as fh:
            head = fh.read(4000)
        if b"<TEI" in head or b"tei-c.org" in head:
            teis.append(p)
    if not teis:
        raise SystemExit("no TEI file (*.xml) found in the folder %s" % src.name)
    if len(teis) > 1:
        raise SystemExit("the folder %s holds %d TEI files (%s); name the one to use as 'tei:' in a text.yml file there"
                         % (src.name, len(teis), ", ".join(p.name for p in teis)))
    return teis[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--meta", help="write collection metadata (JSON) here")
    args = ap.parse_args()

    src = Path(args.src).resolve()
    out = Path(args.out).resolve()
    text_id = src.name
    report = []
    log = lambda s: (report.append(s), print("  [%s] %s" % (text_id, s)))

    cfg = {}
    if (src / "text.yml").exists():
        cfg = yaml.safe_load((src / "text.yml").read_text(encoding="utf-8")) or {}
    tei_path = find_tei(src, cfg)
    log("reading %s (%.1f MB)" % (tei_path.name, tei_path.stat().st_size / 1e6))

    parser = etree.XMLParser(huge_tree=True, remove_comments=True, resolve_entities=False)
    try:
        tree = etree.parse(str(tei_path), parser)
    except etree.XMLSyntaxError as e:
        log("WARNING: the file is not well-formed XML (%s); reading it in recovery mode, "
            "so some text may be missing" % e)
        tree = etree.parse(str(tei_path), etree.XMLParser(huge_tree=True, recover=True,
                                                          remove_comments=True))
    try:
        tree.xinclude()
    except Exception:
        pass
    root = tree.getroot()
    if local(root) not in ("TEI", "teiCorpus"):
        raise SystemExit("%s: root element is <%s>, not <TEI>" % (tei_path.name, local(root)))
    body = root.find(".//{%s}text/{%s}body" % (TEI, TEI))
    if body is None:
        body = root.find(".//{%s}body" % TEI)
    if body is None:
        raise SystemExit("%s: no <text><body> found" % tei_path.name)

    alltext = "".join(body.itertext())
    deva = sum(1 for c in alltext if "ऀ" <= c <= "ॿ")
    latin = sum(1 for c in alltext if c.isalpha() and c < "ɐ")
    translit = cfg.get("transliterate", deva > latin)
    tr = Translit(bool(translit))
    if translit:
        log("Devanagari text: transliterating to IAST")

    meta = header_meta(root, tr)
    work, with_comm = split_title(meta["title_full"] or text_id)
    sub = meta["subtitle"]
    if not with_comm and sub.lower().startswith("with "):
        with_comm = re.split(r":\s", sub)[0].strip()
        sub = ""
    work = cfg.get("work") or work
    commentary_line = cfg.get("commentary") or with_comm or (
        "with " + " and ".join(meta["commentators"]) if meta["commentators"] else "")
    site_title = cfg.get("site_title") or ("e-" + work)
    source = cfg.get("source") or meta["publisher"] or "TEI file"
    cfg.setdefault("work", work)

    sections = build_structure(body, tr, cfg, log)
    nchap = sum(len(s["chapters"]) for s in sections)
    if nchap == 0:
        raise SystemExit("%s: no text found in <body>" % tei_path.name)

    # ---- section names (text.yml may supply them) and slugs ---------------
    names = cfg.get("sections") or []
    for sec, nm in zip(sections, names):
        if nm:
            sec["name"] = str(nm)
    if names and len(names) != len(sections):
        log("WARNING: text.yml gives %d section names, but the TEI has %d sections"
            % (len(names), len(sections)))
    single = len(sections) == 1
    used = set()
    for i, sec in enumerate(sections, 1):
        if single:
            slug = "chapters"
            sec["name"] = sec["name"] or work
        else:
            slug = slugify(sec["name"], "section%d" % i)
        while slug in used or slug in ("assets", "search", "about", "search-index", "chapters") and not single:
            slug = "%s%d" % (slug, i)
        used.add(slug)
        sec["slug"] = slug

    # ---- render ---------------------------------------------------------
    rend = Renderer(tr, cfg.get("commentaries") or {}, meta["persons"])
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(TEMPLATE, out)
    for sec in sections:
        for ch in sec["chapters"]:
            fname = "%03d-%s" % (ch.order, slugify(ch.title, "chapter"))
            cid = "%s-%d" % (sec["slug"], ch.order)
            body_html = rend.render_chapter(ch, cid)
            fm = "---\ntitle: %s\nadhyaya: %s\norder: %d\n---\n" % (
                yq(ch.title), yq(ch.n if ch.n else "·"), ch.order)
            write(out / ("_" + sec["slug"]) / (fname + ".html"), fm + body_html)

    # commentary names
    comms = []
    overrides = cfg.get("commentaries") or {}
    for k, (key, name) in enumerate(rend.comm_keys.items(), 1):
        nm = overrides.get(key) or name
        if not nm and len(rend.comm_keys) == 1:
            if meta["commentators"]:
                nm = " and ".join(meta["commentators"])
            elif with_comm:
                nm = re.sub(r"^with\s+", "", with_comm)
            else:
                nm = "commentary"
        if not nm and meta["persons"].get(key):
            nm = meta["persons"][key]
        comms.append({"n": k, "key": key, "name": nm or "commentary %d" % k})
    if comms:
        log("commentaries: " + "; ".join("%s (%s)" % (c["name"], c["key"]) for c in comms))
    else:
        log("no commentary found: the whole text is treated as mūla")
    log("%d sections, %d chapters; %d mūla blocks, %d commentary blocks, %d notes"
        % (len(sections), nchap, rend.stats["blocks_m"], rend.stats["blocks_c"], rend.stats["notes"]))
    if rend.unknown:
        log("elements rendered as plain text: " +
            ", ".join("<%s> ×%d" % kv for kv in rend.unknown.most_common()))

    # ---- config and data -------------------------------------------------
    tei_name = tei_path.name
    (out / "assets" / "tei").mkdir(parents=True, exist_ok=True)
    shutil.copy(tei_path, out / "assets" / "tei" / tei_name)

    blurb = cfg.get("blurb") or ""
    description = blurb or (work + (" " + commentary_line if commentary_line else "") + ".")
    conf = {
        "title": site_title,
        "tagline": cfg.get("tagline") or ("The %s, in IAST" % work),
        "description": description,
        "work": work,
        "commentary_line": commentary_line,
        "source_note": source,
        "tei_file": "assets/tei/" + tei_name,
        "single_section": single,
        "baseurl": "/" + text_id,
        "url": "",
        "markdown": "kramdown",
        "kramdown": {"input": "GFM"},
        "collections": {s["slug"]: {"output": True, "permalink": "/:collection/:name/"} for s in sections},
        "defaults": [{"scope": {"path": "", "type": s["slug"]},
                      "values": {"layout": "chapter", "sthana_slug": s["slug"]}} for s in sections]
                    + [{"scope": {"path": ""}, "values": {"layout": "default"}}],
        "exclude": ["text.yml"],
    }
    write(out / "_config.yml", "# Generated by tools/tei2site.py from %s -- do not edit\n" % tei_name
          + yaml.safe_dump(conf, allow_unicode=True, sort_keys=False))
    sth = {}
    for s in sections:
        sth[s["slug"]] = {"name": s["name"], "subtitle": "", "count": len(s["chapters"])}
    write(out / "_data" / "sthanas.yml", yaml.safe_dump(sth, allow_unicode=True, sort_keys=False))
    write(out / "_data" / "commentaries.yml", yaml.safe_dump(comms, allow_unicode=True, sort_keys=False))

    for s in sections:
        write(out / "search-index" / (s["slug"] + ".json"),
              "---\npermalink: /search-index/%s.json\nlayout: null\nsitemap: false\n---\n"
              "[{%% for c in site.%s %%}{%% include search-entry.json chapter=c %%}"
              "{%% unless forloop.last %%},{%% endunless %%}{%% endfor %%}]\n" % (s["slug"], s["slug"]))
        if not single:
            write(out / (s["slug"] + ".html"),
                  "---\nlayout: sthana-index\nsthana_slug: %s\npermalink: /%s/\ntitle: %s\n---\n"
                  % (s["slug"], s["slug"], yq(s["name"])))

    # ---- About page from the TEI header ---------------------------------
    esc = lambda s: html.escape(s or "", quote=False)
    a = ['---\nlayout: default\ntitle: About\npermalink: /about/\n---\n<div class="prose">',
         "<h1>About this edition</h1>",
         "<p><em>%s</em>%s. This reading edition is generated automatically from "
         'a <a href="{{ \'/%s\' | relative_url }}" download>TEI file</a>; the text, '
         "its divisions and its notes are exactly as encoded there.</p>"
         % (esc(meta["title_full"] or work), (" — " + esc(meta["subtitle"])) if meta["subtitle"] else "",
            conf["tei_file"])]
    def section(title, items):
        items = [i for i in items if i]
        if items:
            a.append("<h2>%s</h2>" % title)
            a.extend("<p>%s</p>" % esc(i) for i in items)
    section("Authors", meta["authors"] + meta["commentators"])
    section("Editors", meta["editors"])
    section("Responsibility", ["%s: %s" % r if r[0] else r[1] for r in meta["resp"]])
    section("Source", meta["sources"])
    section("Publication", [meta["publisher"]])
    if meta["licence"] or meta["licence_url"]:
        a.append("<h2>Licence</h2>")
        if meta["licence_url"]:
            a.append('<p><a href="%s">%s</a></p>' % (esc(meta["licence_url"]), esc(meta["licence"] or meta["licence_url"])))
        else:
            a.append("<p>%s</p>" % esc(meta["licence"]))
    section("Availability", meta["availability"])
    section("Project", meta["project"])
    section("Editorial principles", meta["editorial"])
    if meta["changes"]:
        a.append("<h2>Revision history</h2><ul>")
        a.extend("<li>%s %s%s</li>" % (esc(w), esc(who) + ": " if who else "", esc(t)) for w, who, t in meta["changes"])
        a.append("</ul>")
    a.append("<h2>How this edition was made</h2><p>The TEI file was converted by the eTexts "
             "tools (<code>tools/tei2site.py</code>). Root text (mūla), commentaries and notes "
             "are distinguished as encoded in the TEI; where the TEI does not mark them, the "
             "text is shown as mūla. Conversion report:</p><ul>")
    a.extend("<li>%s</li>" % esc(r) for r in report if not r.startswith("reading "))
    a.append("</ul></div>")
    write(out / "about.md", "\n".join(a) + "\n")

    meta_out = {
        "id": text_id,
        "site_title": site_title,
        "work": work,
        "commentary": commentary_line,
        "blurb": blurb or sub,
        "source": source,
        "tei": [{"label": "source file", "file": conf["tei_file"]}],
        "generated_from_tei": tei_name,
    }
    if args.meta:
        Path(args.meta).write_text(json.dumps(meta_out, ensure_ascii=False, indent=2), encoding="utf-8")
    log("site written: %s" % out)


if __name__ == "__main__":
    main()
