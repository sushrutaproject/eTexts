#!/usr/bin/env python3
"""
Scraper for the e-Vagbhata site (vedotpatti.in) -- Astangahrudaya with
two commentaries: Arunadatta's Sarvangasundara and Hemadri's
Ayurvedarasayana.

Adapted from the Susruta/Caraka scraper. What's different here, found
during diagnosis:

  - Same NIIMH-family engine (form fields, doIast() renderer), but on
    a different host (vedotpatti.in, not niimh.res.in).
  - Root text: <span id="sloka_trans_N"> -- same convention as before.
  - BOTH commentaries share a single <span id="vya_trans_N"> stream.
    Each switch between them is marked by a literal token embedded in
    that same stream: "sa0" for Arunadatta (print abbreviation "Sa."),
    then "ā0" and "ra0" for Hemadri (print abbreviation "A. ra."). A
    first pass assumed each marker was always the ENTIRE content of
    its own span -- true most of the time, but not always: sometimes
    a marker is fused directly onto the start of the following word in
    the SAME span (e.g. "sa0-annavidhau..."), which an exact-match
    check misses, leaking "sa0-" into the visible text and silently
    failing to register the switch. This version strips a marker (an
    optional run of separator punctuation) from the front of a string
    regardless of what follows in the same span, so the two
    commentaries come out correctly separated and the site builder
    doesn't need to guess at a text-level split.
  - No footnote apparatus on this text (0 <sup> tags found in
    diagnosis). The 'ref' kind is kept in case a later sthana
    surprises us; it's expected to stay at zero, and gets flagged if
    it doesn't.
  - selAdhi must be explicitly set to "pUrNa adhyAya" for the whole
    chapter (same value/convention as the old site) -- the default
    lands on a short intro sub-section only, not the full chapter.

Install (one-time, if not already done):
    pip install playwright
    playwright install chromium

Run:
    python3 scrape_evagbhata.py

Output:
    ./evagbhata_data/sthana_<n>_<name>.json
"""

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "https://vedotpatti.in/samhita/Vag/ehrudayam/?mod=read"
OUT_DIR = Path("evagbhata_data")
OUT_DIR.mkdir(exist_ok=True)

# Order and names as they actually appear on THIS site (not the same
# order as Susruta -- sharirasthana is 2nd here, not 3rd).
STHANA_NAMES = {
    1: "sutrasthana",
    2: "sharirasthana",
    3: "nidanasthana",
    4: "cikitsasthana",
    5: "kalpasiddhisthana",
    6: "uttarasthana",
}

PAUSE_SECONDS = 1.0


def select_and_wait(page, selector, value):
    current = page.eval_on_selector(selector, "el => el.value")
    if current == value:
        return
    with page.expect_navigation():
        page.select_option(selector, value)


EXTRACT_JS = r"""
() => {
  const map = {};
  document.querySelectorAll('div[id]').forEach(div => {
    if (div.classList.contains('hidden')) map[div.id] = div.textContent;
  });
  let emptySpans = 0;
  document.querySelectorAll('span[id]').forEach(span => {
    if (Object.prototype.hasOwnProperty.call(map, span.id)) {
      if (span.innerHTML.trim() === '') {
        span.innerHTML = doIast(map[span.id], 'iast');
        if (span.innerHTML.trim() === '') emptySpans++;
      }
    }
  });

  const root = document.querySelector('#readContent');
  if (!root) return {error: 'no #readContent'};

  function classify(node) {
    for (let el = node.parentElement; el && el !== root; el = el.parentElement) {
      if (el.classList && el.classList.contains('hidden')) return null;
      if (el.tagName === 'SUP') return 'ref';
      const id = el.id || '';
      if (id.indexOf('sloka_trans') === 0) return 'sloka';
      if (id.indexOf('vya_trans') === 0) return 'vya';
      if (id === 'sthAdhTitle') return null;
    }
    return 'text';
  }

  // Marker tokens found in diagnosis, embedded inside the shared
  // vya_trans_ stream: "sa0" flips to Arunadatta; "ā0" then "ra0"
  // flips to Hemadri ("ā0" alone is decorative, no state change).
  // These are NOT reliably isolated in their own span. Three fusion
  // patterns turned up across the corpus: marker alone in its own
  // span (the common case); marker fused onto the FRONT of the next
  // word in the same span ("sa0-annavidhau..."); and marker fused
  // onto the END of the previous sentence with zero separator at all
  // ("...sambhavanti|sa0-anyāḥ..."). A leading-anchor check only
  // catches the first two, silently leaking "sa0-" into the text and
  // missing the commentary switch for the third. This scans for the
  // marker ANYWHERE in a span's text (safe: real Sanskrit words never
  // contain the digit "0"), splitting the span into before/after
  // pieces at each occurrence and updating the running commentary
  // state at each one -- so a single span can yield more than one
  // tagged piece when a marker sits in its middle.
  const MARKER_RE = /(sa0|ra0|\u01010|a0)[\s\-.]*/giu;
  let vyaSub = 'aruna';        // Arunadatta's commentary always opens the chapter
  let justSawMarker = false;   // true right after a marker-only span, until real content arrives

  function splitOnMarkers(s) {
    const pieces = [];
    let lastIndex = 0;
    let currentSub = vyaSub;
    let m;
    MARKER_RE.lastIndex = 0;
    while ((m = MARKER_RE.exec(s))) {
      const before = s.slice(lastIndex, m.index);
      if (before) pieces.push({ sub: currentSub, text: before });
      const tok = m[1].toLowerCase();
      if (tok === 'sa0') currentSub = 'aruna';
      else if (tok === 'ra0') currentSub = 'hemadri';
      lastIndex = m.index + m[0].length;
    }
    const rest = s.slice(lastIndex);
    if (rest) pieces.push({ sub: currentSub, text: rest });
    vyaSub = currentSub;
    return pieces;
  }

  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
  const segments = [];
  let n;
  while ((n = walker.nextNode())) {
    const kind = classify(n);
    if (!kind) continue;
    const raw = n.nodeValue;

    if (kind === 'vya') {
      let s = raw || '';
      if (justSawMarker) s = s.replace(/^[\s\-.]+/, '');
      const pieces = splitOnMarkers(s);
      justSawMarker = (pieces.length === 0);
      for (const piece of pieces) {
        const effectiveKind = 'vya_' + piece.sub;
        const last = segments[segments.length - 1];
        if (last && last.k === effectiveKind) {
          last.t += piece.text;
        } else {
          segments.push({ k: effectiveKind, t: piece.text });
        }
      }
      if (pieces.length === 0 && segments.length && segments[segments.length - 1].k !== 'ref') {
        segments[segments.length - 1].t += ' ';
      }
      continue;
    }

    if (!raw || !raw.trim()) {
      if (segments.length && segments[segments.length - 1].k !== 'ref') {
        segments[segments.length - 1].t += ' ';
      }
      continue;
    }

    const t = raw;
    const last = segments[segments.length - 1];
    if (last && last.k === kind && kind !== 'ref') {
      last.t += t;
    } else {
      segments.push({k: kind, t: t});
    }
  }

  const counts = {sloka: 0, vya_aruna: 0, vya_hemadri: 0, ref: 0, text: 0};
  segments.forEach(s => { counts[s.k] = (counts[s.k] || 0) + 1; });

  return {segments: segments, emptySpans: emptySpans, counts: counts};
}
"""


def get_adhyaya_list(page):
    options = page.query_selector_all('select[name="selAdhyaya"] option')
    result = []
    for opt in options:
        value = opt.get_attribute("value")
        title = (opt.inner_text() or "").strip()
        if value:
            result.append((value, title))
    return result


def set_script_iast(page):
    page.select_option('select[name="scriptName"]', "IAST")
    page.wait_for_timeout(300)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL, wait_until="load")

        for sthana_num, sthana_name in STHANA_NAMES.items():
            out_path = OUT_DIR / f"sthana_{sthana_num}_{sthana_name}.json"
            if out_path.exists():
                print(f"Skipping sthāna {sthana_num} ({sthana_name}) -- already scraped")
                continue

            print(f"=== Sthāna {sthana_num}: {sthana_name} ===")
            select_and_wait(page, 'select[name="selSthana"]', str(sthana_num))
            set_script_iast(page)

            adhyayas = get_adhyaya_list(page)
            print(f"  Found {len(adhyayas)} adhyāyas")

            chapters = []
            for value, title in adhyayas:
                select_and_wait(page, 'select[name="selAdhyaya"]', value)
                select_and_wait(page, 'select[name="selAdhi"]', "pUrNa adhyAya")
                set_script_iast(page)

                result = page.evaluate(EXTRACT_JS)
                if result.get("error"):
                    print(f"    Adhyāya {value}: ERROR {result['error']}")
                    continue

                counts = result["counts"]
                empty = result["emptySpans"]
                chars = sum(len(s["t"]) for s in result["segments"])
                flags = []
                if empty:
                    flags.append(f"{empty} EMPTY SPANS")
                if counts.get("sloka", 0) == 0:
                    flags.append("NO ROOT TEXT FOUND")
                if counts.get("ref", 0):
                    flags.append(f"{counts['ref']} FOOTNOTE REFS (unexpected -- review)")
                flag = ("  *** " + "; ".join(flags) + " -- REVIEW ***") if flags else ""

                print(f"    Adhyāya {value}: {title[:48]!r} -- {chars} chars, "
                      f"root {counts.get('sloka', 0)} / Aruṇadatta {counts.get('vya_aruna', 0)} "
                      f"/ Hemādri {counts.get('vya_hemadri', 0)}{flag}")

                chapters.append({
                    "adhyaya": int(value),
                    "title": title,
                    "segments": result["segments"],
                    "empty_spans": empty,
                    "counts": counts,
                })
                time.sleep(PAUSE_SECONDS)

            out_path.write_text(json.dumps(chapters, ensure_ascii=False), encoding="utf-8")
            print(f"  Saved {out_path}")

        browser.close()
    print("\nDone. Zip up evagbhata_data/ and send it back.")


if __name__ == "__main__":
    main()
