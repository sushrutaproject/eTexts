#!/usr/bin/env python3
"""
Download the Śārṅgadharasaṃhitā (with Āḍhamalla's Dīpikā and Kāśīrāma's
Gūḍhārthadīpikā) from the CCRAS e-book web service.

The service is a plain form-POST API (found in the CCRAS app's main.js):
    http://164.100.63.6/ccras_ebooks_api/getsamhitadata.php
Text id 4 = Śārṅgadharasaṃhitā. For each khaṇḍa and each adhyāya, one
"fullChapter" request returns every passage with its root text (pada)
and commentary (vya_text).

This script only saves the RAW replies, unchanged, into
sharngadhara_data/raw/. All cleaning and IAST conversion happen in
build_sharngadhara.py, so the conversion can be improved later without
downloading again.

Run (in the venv; needs:  pip install requests):
    python3 scrape_sharngadhara.py
Safe to re-run: chapters already downloaded are skipped.
"""

import json
import time
from pathlib import Path

import requests

API = "http://164.100.63.6/ccras_ebooks_api/getsamhitadata.php"
SAM_ID = 4
RAW = Path("sharngadhara_data/raw")
RAW.mkdir(parents=True, exist_ok=True)
PAUSE = 1.5   # seconds between requests -- be polite to a government server

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (research mirror; Susruta Project, Univ. of Alberta)",
    "Origin": "http://ccras.res.in",
    "Referer": "http://ccras.res.in/ccras_ebooks/",
})


def call(**fields):
    for attempt in range(4):
        try:
            r = session.post(API, files={k: (None, str(v)) for k, v in fields.items()},
                             timeout=90)
            r.raise_for_status()
            data = r.json()
            time.sleep(PAUSE)
            return data
        except Exception as e:
            wait = 5 * (attempt + 1)
            print(f"   retry in {wait}s ({e})")
            time.sleep(wait)
    raise SystemExit(f"Giving up on request {fields}")


def main():
    structure = {
        "samhita": call(request="getselsamhitadet", sam_id=SAM_ID),
        "khandas": [],
    }
    khandas = call(request="getstanadets", sam_id=SAM_ID)
    for kh in sorted(khandas, key=lambda k: int(k["sth_order"])):
        stid = kh["sthana_id"]
        chapters = call(request="getseladhyayadet", sam_id=SAM_ID, sat_id=stid)
        kh = dict(kh, chapters=chapters)
        structure["khandas"].append(kh)
        print(f"Khaṇḍa {stid}: {kh['sth_itrans']} -- {len(chapters)} chapters")

        for ch in chapters:
            adid = ch["adhyaya_id"]
            out = RAW / f"k{int(stid)}_a{int(adid):02d}.json"
            if out.exists():
                print(f"   {out.name} already present, skipped")
                continue
            rows = call(request="fullChapter", sam_id=SAM_ID, stn_id=stid, ady_id=adid)
            out.write_text(json.dumps(rows, ensure_ascii=False, indent=0), encoding="utf-8")
            print(f"   {out.name}: {ch['adh_itrans']} ({len(rows)} rows)")

    (RAW / "structure.json").write_text(
        json.dumps(structure, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nDone. Raw data is in sharngadhara_data/raw/")


if __name__ == "__main__":
    main()
