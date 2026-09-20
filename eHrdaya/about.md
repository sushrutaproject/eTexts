---
layout: default
title: About
permalink: /about/
---
<div class="prose">

# About this site

This site presents the **Aṣṭāṅgahṛdaya** of **Vāgbhaṭa**, a Sanskrit
treatise on medicine, together with two commentaries, in IAST (romanized,
diacritic) transliteration.

## The three texts

The root text is set in larger type at the full measure. Two commentaries
follow it, each set smaller and indented behind a rule, labelled with the
same abbreviations used in print: **Sa.** for **Aruṇadatta's**
*Sarvāṅgasundarā*, and **Ā. rā.** for **Hemādri's** *Āyurvedarasāyana*.
Each commentary can be hidden independently with the controls at the
head of a chapter.

This division is not editorial guesswork on this site's part: the source
marks the start of each comment with its own abbreviation, and that
distinction has been carried through directly.

## Hemādri's commentary is only preserved for part of the text

Unlike Aruṇadatta's, which runs throughout, Hemādri's *Āyurvedarasāyana*
is present in this source only for:

- all of **Sūtrasthāna** and **Kalpasiddhisthāna**,
- the first six chapters of **Nidānasthāna** (of sixteen), and
- the first seven chapters of **Cikitsāsthāna** (of twenty-two),

and is absent from **Śārīrasthāna** and **Uttarasthāna** entirely. Where
it is absent, the "Show Hemādri" control does not appear, since there is
nothing to toggle. This pattern comes directly from the source and looks
consistent with partial survival of the commentary rather than a gap in
this site's extraction — but it has not been independently checked
against the manuscript tradition, and is worth verifying against
catalogue information on the text if you rely on it.

## Source

The text and its transliteration are drawn from
[vedotpatti.in](https://vedotpatti.in/samhita/Vag/ehrudayam/), which uses
the same underlying e-Samhita reading-room software as the NIIMH sites
(e-Suśruta, e-Caraka) this site's sibling projects are built from. This
site is a static, IAST-only mirror of that resource's Aṣṭāṅgahṛdaya text,
restructured for offline reading, searching and hosting.

## How it was made

The original site serves its text through a form-driven interface backed
by client-side JavaScript, rather than through static, linkable pages. Its
content was extracted with a headless browser (chapter by chapter, in
"full chapter" mode) and converted to this static Jekyll site. Root text
and the two commentaries share a single stream of word-spans in the
source markup; the split between them was recovered from the print-style
abbreviation ("Sa." / "Ā. rā.") that the source embeds at the start of
each comment. The extraction was checked chapter by chapter against the
number of word-level text nodes actually rendered, to catch silently
dropped content, and checked again for any leftover abbreviation text
that would indicate a missed split.

## Known limitations

- Only the IAST (diacritical) rendering is included here; the original
  site also offers Devanagari and several other Indic scripts.
- Only "full chapter" view was captured; the original site's per-passage
  (sub-chapter) navigation is not reproduced.
- Verse and chapter divisions follow the source edition.
- This text carries no footnote or variant-reading apparatus in the
  source, so none is reproduced here.
- If you notice missing or garbled passages, please compare against the
  [original site](https://vedotpatti.in/samhita/Vag/ehrudayam/) and open
  an issue.

</div>
