# e-Śārṅgadhara

A static Jekyll reading edition of the **Śārṅgadharasaṃhitā** of
Śārṅgadhara, with the commentaries of **Āḍhamalla** (*Dīpikā*) and
**Kāśīrāma** (*Gūḍhārthadīpikā*), in IAST. Content drawn from the CCRAS
e-book reading room (<http://ccras.res.in/ccras_ebooks/readSam>).

## Rebuilding the text

```
pip install requests
python3 scrape_sharngadhara.py   # downloads raw data to sharngadhara_data/raw/
python3 build_sharngadhara.py    # writes the chapter files
```

The source is the CCRAS web service
`http://164.100.63.6/ccras_ebooks_api/getsamhitadata.php` (text id 4),
a plain form-POST API behind the CCRAS Angular reading room.
`rts_iast.py` converts its romanization to IAST.

## Structure

- `_purvakhanda/`, `_madhyamakhanda/`, `_uttarakhanda/` — one collection
  per khaṇḍa, one file per adhyāya (created by the builder). Root text in
  `<div class="mula">`, Āḍhamalla in `<div class="adhamalla">`, Kāśīrāma
  in `<div class="kasirama">`, each commentary with a
  `<span class="commentator-label">`.
- Labels are set once, in `_config.yml` (`label_adhamalla`,
  `label_kasirama`).
- `_data/sthanas.yml` — khaṇḍa names, subtitles, counts (the file keeps
  the family's historical name).
- `search.html` + `search-index/*.json` — client-side search, same
  mechanism as the sibling sites.
- `probe_ccras.py` — the one-off probe used to discover the API.
- `scrape_sharngadhara.py`, `build_sharngadhara.py`, `rts_iast.py` — see above.
- Editor's notes embedded in the source (`#foot@…#`) become numbered
  notes at the foot of each chapter.

## TEI download

The home page offers the complete text as two unified TEI P5 files, in
`assets/tei/`: root text only (`sarngadharasamhita-mula.xml`) and root
text with both commentaries (`sarngadharasamhita-full.xml`). They are
generated from the chapter files by `build_tei.py` (the same script as
the sibling sites). After any change to the text, regenerate and
re-validate:

    python3 build_sharngadhara.py
    python3 build_tei.py --validate path/to/tei_all.rng

(`pip install jingtrang` provides the validator; `tei_all.rng` is in the
TEI release at https://github.com/TEIC/TEI/releases.)

## Deploying

Push to `main`; GitHub Pages builds it. `baseurl` is `/eSarngadhara` —
change it if the repo is named differently.
