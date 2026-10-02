---
layout: default
title: About
permalink: /about/
---

<div class="prose" markdown="1">

# About eTexts

eTexts gathers digital reading editions of classical Sanskrit medical
treatises, each with its commentaries, in IAST transliteration. It is a
resource of the [Suśruta Project](https://sushrutaproject.github.io/).

{% for t in site.data.corpus %}
- **[{{ t.work }}]({{ t.id | prepend: '/' | append: '/' | relative_url }})**, {{ t.commentary }}. Source: {{ t.source }}.
{% endfor %}

Each text has its own About page describing its source edition, scope and
known limitations.

## Searching

The [search page]({{ '/search/' | relative_url }}) works across the whole
collection, a single text, or a single sthāna of a text. The search box at
the top of every text page searches that text (or the sthāna you are
reading) by default; the scope can be widened on the results page.

Plain-text and regular-expression matching are both available, and
diacritics can optionally be ignored (so _dosa_ finds _doṣa_). Root text,
commentaries and editorial notes are all searched. Clicking a result opens
the chapter with the matches highlighted.

Searching runs entirely in your browser: the first search across all
texts downloads the full collection, after which further searches are
immediate.

## Downloads

Every text can be downloaded as a validating TEI P5 XML file, either the
root text alone or with its commentaries, from the links on the
[home page]({{ '/' | relative_url }}).

</div>
