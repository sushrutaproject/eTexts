# Two textual registers: install

This replaces the chapter files and several site files. **`.gitignore` is
deliberately not included** — yours is correct and untouched.

## What to do
Copy everything here over your repo, preserving paths, then commit and
push. Check locally first with `bundle exec jekyll serve`.

Afterwards you can delete the superseded `esushruta_data/` and
`build_site.py` (v1 data and builder) from the repo if you wish.

## What changed

**All 186 chapter files** are regenerated. Root text is now
`<div class="mula">`, Ḍalhaṇa's commentary `<div class="bhasya">`, and
variant readings a `<section class="notes">` at the foot.

**`_layouts/chapter.html`** — adds the "Show commentary" control and a
one-line legend. The setting is remembered across chapters and visits.

**`assets/css/style.css`** — register styling appended. Root text is set
larger at the full measure; the commentary smaller, indented, behind a
rule. No colour distinction.

**`search-index/*.json`** — now strip inline footnote references before
indexing, so their digits no longer interrupt phrase searches. The notes
themselves remain searchable.

**`about.md`, `index.html`, `_config.yml`** — corrected: earlier copy
claimed the text carries Gayadāsa's Nyāyacandrikā. It does not. Gayadāsa
(and Cakrapāṇidatta, Bhāskara, Hāraṇacandra) appear as citations *within*
Ḍalhaṇa's commentary. The About page now also documents the register
distinction and its provenance.

**`build_site_v2.py`** — the new builder. It applies the ISO→IAST
conversion itself, so `fix_iso_to_iast.py` is no longer needed after a
rebuild.

**`esushruta_data_v2/`** — the structured source data. Excluded from the
built site; included here for reproducibility. Skip it if you'd rather
not carry 5.7 MB in the repo.

## Checks run
- 186/186 chapters have identifiable root text.
- Every footnote reference in the corpus has a matching note. (Two notes
  in Sūtrasthāna 1 are mis-delimited in NIIMH's own data; the parser keys
  on sequential numbering rather than the delimiter, which handles them.)
- HTML tag balance verified across all 186 files.
- Search re-tested against the new markup: plain, regex, diacritic-folded,
  and scope options all behave as before.
- Five Uttaratantra chapters have no notes section; they contain no
  footnote references at all, so that is correct.

Not verified here: Jekyll build and CSS rendering, since this environment
has no Ruby. Worth a local serve before pushing.
