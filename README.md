# eTexts

Digital reading editions of classical Sanskrit medical treatises, with
their commentaries, in IAST, published at
**https://sushrutaproject.github.io/eTexts/** with one combined search
across the whole collection.

| Directory | Text | Published at |
|---|---|---|
| `eCaraka/` | Carakasaṃhitā, with Cakrapāṇidatta | `/eTexts/eCaraka/` |
| `eSushruta/` | Suśrutasaṃhitā, with Ḍalhaṇa | `/eTexts/eSushruta/` |
| `eHrdaya/` | Aṣṭāṅgahṛdaya, with Aruṇadatta and Hemādri | `/eTexts/eHrdaya/` |
| `eMadhava/` | Mādhavanidāna, with the Madhukośa and Ātaṅkadarpaṇa | `/eTexts/eMadhava/` |
| `eSharngadhara/` | Śārṅgadharasaṃhitā, with Āḍhamalla and Kāśīrāma | `/eTexts/eSharngadhara/` |

Each directory was formerly its own repository in the `sushrutaproject`
organization; their full commit histories were carried over
(`git log -- eSushruta/` shows them).

## How it fits together

```
texts.yml                 register of texts: order, titles, TEI files
build.rb                  builds everything into _site/
Gemfile                   one Gemfile for every build (Jekyll 3.10)
.github/workflows/pages.yml   builds and deploys on every push to main
portal/                   the collection home page, combined search, About
eCaraka/ eSushruta/ ...   one complete Jekyll site per text (unchanged in design)
```

`build.rb` builds each text as its own Jekyll site into `_site/<id>/`,
then builds the portal into `_site/`. Each text keeps its own layouts,
CSS and reading controls. Two values are injected into each text at
build time: `corpus_root` (the collection's URL, used by the "eTexts /"
link and the header search box) and `text_id` (its directory name).

### Search

There is a single search page, `portal/search.html` (at `/eTexts/search/`).
Its *Search in* menu offers all texts, any single text, or any single
sthāna of a text. The header box on every text page searches that text
(or the sthāna being read) and lands on this page, where the scope can be
widened. Each text's old `search/` URL now forwards there, so existing
links and bookmarks keep working.

The search reads the per-sthāna index files that every text already
produces (`<id>/search-index/<sthāna>.json`); the list of sthānas comes
from each text's `_data/sthanas.yml`. Searching runs in the browser. The
first all-texts search downloads about 16 MB of index (much less over
the wire, compressed), after which searches are instant.

## Adding a new text

1. Put the new Jekyll site in its own directory, e.g. `eBhela/`, built
   the same way as the others (the e-Suśruta/e-Vāgbhaṭa procedure).
   It needs:
   - `_data/sthanas.yml`: one entry per section collection
     (`slug: {name, subtitle, count}`); a text with no sthāna division
     has a single entry, as in `eMadhava/`;
   - `search-index/<slug>.json` for each section (copy one from another
     text and change the collection name);
   - in `_includes/header.html`, the "eTexts /" link and the header search
     form pointing at `{{ site.corpus_root }}/search/` with
     `scope` = `{{ site.text_id }}`, as in the existing texts;
   - `search.html` replaced by the short forwarding page used in the
     other texts.
2. Add an entry for it to `texts.yml`.
3. Commit and push. The home page, the navigation, the search menu and
   the About page all pick it up automatically.

## Building locally

```sh
bundle install
bundle exec ruby build.rb            # writes _site/ for base path /eTexts
cd _site && python3 -m http.server   # then open http://localhost:8000/
```

For a local preview at the server root use `--base ""`; to preview at
`/eTexts/` serve the folder that contains a link named `eTexts` pointing
to `_site`.

## Deployment

The workflow in `.github/workflows/pages.yml` runs on every push to
`main`. One-time setup on GitHub: **Settings → Pages → Build and
deployment → Source: GitHub Actions**. The workflow takes the base path
from GitHub Pages, so renaming the repository needs no code change.
