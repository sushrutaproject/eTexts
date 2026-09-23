# e-Vāgbhaṭa

A static Jekyll reading edition of the **Aṣṭāṅgahṛdaya** of Vāgbhaṭa, a
Sanskrit treatise on medicine, with the commentaries of **Aruṇadatta**
(*Sarvāṅgasundarā*, throughout) and **Hemādri** (*Āyurvedarasāyana*,
preserved for part of the text — see `about.md`). Content drawn from
[vedotpatti.in](https://vedotpatti.in/samhita/Vag/ehrudayam/); see
`about.md` for provenance and limitations.

## Structure

- `_sutrasthana/`, `_sharirasthana/`, `_nidanasthana/`, `_cikitsasthana/`,
  `_kalpasiddhisthana/`, `_uttarasthana/` — one Jekyll collection per
  sthāna, one file per adhyāya, in this text's own sthāna order (note
  Śārīrasthāna is second here, unlike e-Suśruta). Root text is in
  `<div class="mula">`, Aruṇadatta's commentary in
  `<div class="aruna">`, Hemādri's in `<div class="hemadri">` (where
  preserved), each carrying a small `<span class="commentator-label">`
  ("Sa." / "Ā. rā.") matching the print edition's own abbreviations.
- `_data/sthanas.yml` — display names, subtitles, chapter counts.
- `_layouts/`, `_includes/`, `assets/css/style.css` — design and the two
  independent commentary show/hide controls.
- `search.html` + `search-index/*.json` — client-side search, identical
  mechanism to e-Suśruta/e-Caraka. The index files are Liquid templates
  that regenerate at build time, so edits to the text are picked up
  automatically.
- `evagbhata_data/` — the raw scraped source data (kept for
  reproducibility; excluded from the built site).
- `scrape_evagbhata.py` — the Playwright scraper. Needed only to redo the
  extraction from vedotpatti.in; recovers the Aruṇadatta/Hemādri split
  from the source's own "Sa."/"Ā. rā." markers while walking the DOM.
- `build_evagbhata.py` — regenerates the chapter files and
  `_data/sthanas.yml` from `evagbhata_data/`. Needed only if the source
  data changes. It also applies the ISO→IAST conversion, so that is not
  a separate step.

## Local preview

```
bundle install
bundle exec jekyll serve
```

Then open <http://localhost:4000/eVagbhata/>.

## Deploying

Push to `main`; GitHub Pages builds it with the `github-pages` gem pinned
in the `Gemfile`. No plugins beyond Jekyll's built-ins are used.
`baseurl` is set to `/eVagbhata` for the project-page URL — update both
it and this README's local-preview URL if the repo is named differently.

## TEI download

The home page offers the complete text as two unified TEI P5 files, in
`assets/tei/`: root text only (`*-mula.xml`) and root text with commentary
(`*-full.xml`). They are generated from the chapter files by
`build_tei.py`. After any change to the text, regenerate and re-validate:

    python3 build_tei.py --validate path/to/tei_all.rng

(`pip install jingtrang` provides the validator; `tei_all.rng` is in the
TEI release at https://github.com/TEIC/TEI/releases.)
