# legacy/ — the former hand-built sites (not built, not published)

Until November 2026 the first five texts (eCaraka, eSushruta, eHrdaya,
eMadhava, eSharngadhara) were hand-built Jekyll sites: their chapter pages
had been scraped from the source editions (NIIMH e-Samhita, vedotpatti.in,
CCRAS), and their TEI files were generated *from* those pages by each
folder's `build_tei.py`.

Since then the TEI file in each text's folder is the master copy, and the
reading pages are generated from it by `tools/tei2site.py` (see the main
README, "Editing a text"). When that change was made, the generated pages
were checked against these: body text, mūla/commentary division, all
notes, search indexes and every page address are the same.

What is kept here, unchanged, for reference:

- the Jekyll sites (`_config.yml`, `_layouts/`, `_includes/`, the chapter
  pages in `_<section>/`, CSS, search-index stubs);
- the scrapers and site builders (`scrape_*.py`, `build_*.py`,
  `probe_ccras.py`, `rts_iast.py`), with their downloaded data where it
  was in the repository;
- `build_tei.py`, which turned the chapter pages into TEI. **Do not run
  it**: it would overwrite the TEI files with output that lacks all
  later edits;
- the old `…-mula.xml` files under `assets/tei/` (the build now derives
  them from the full TEI file).

Nothing in `build.rb` reads this folder. It can be deleted once it is no
longer wanted; git keeps the history either way.
