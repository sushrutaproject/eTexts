#!/usr/bin/env python3
"""
Probe the CCRAS e-book API directly -- no browser needed.

The CCRAS reading room is an Angular app that fetches its text from a
plain web service at http://164.100.63.6/ccras_ebooks_api/getsamhitadata.php
(found in the app's main.js). Each request is a simple form POST with a
"request" field, e.g. GetAllSamhitas, getstanadets, getseladhyayadet,
fullChapter. Some calls also send a login id ("uid") and token ("cetv");
this probe first tries WITHOUT logging in, to see what is open.

Install (one-time, inside the venv):
    pip install requests

Run:
    python3 probe_ccras.py

Output: folder  ccras_probe/  with the raw replies. Zip it and send it back,
together with whatever the script prints.
"""

import json
import re
import time
from pathlib import Path

import requests

API = "http://164.100.63.6/ccras_ebooks_api/getsamhitadata.php"
OUT = Path("ccras_probe")
OUT.mkdir(exist_ok=True)
PAUSE = 1.0

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (research mirror probe; Susruta Project)",
    "Origin": "http://ccras.res.in",
    "Referer": "http://ccras.res.in/ccras_ebooks/",
})

step = [0]


def call(label, **fields):
    step[0] += 1
    fname = OUT / f"{step[0]:02d}_{label}.txt"
    try:
        r = session.post(API, files={k: (None, str(v)) for k, v in fields.items()},
                         timeout=60)
        body = r.text
        status = r.status_code
    except Exception as e:
        body, status = f"<<request failed: {e}>>", None
    fname.write_text(f"FIELDS: {fields}\nSTATUS: {status}\n\n{body}", encoding="utf-8")
    time.sleep(PAUSE)
    try:
        data = json.loads(body)
    except Exception:
        data = None
    kind = (f"list of {len(data)}" if isinstance(data, list)
            else type(data).__name__ if data is not None else "not JSON")
    print(f"[{step[0]:02d}] {label}: HTTP {status}, {kind}, {len(body)} chars")
    if data is None:
        print("      starts:", body[:200].replace("\n", " "))
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        print("      fields:", ", ".join(data[0].keys()))
    return data


def first(d, *keys):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return None


def main():
    samhitas = call("GetAllSamhitas", request="GetAllSamhitas")
    if not isinstance(samhitas, list):
        print("\nCould not list the texts -- please send ccras_probe/ back.")
        return

    print("\nTexts on the server:")
    targets = []
    for s in samhitas:
        sid = first(s, "samhita_id", "sam_id", "id")
        title = " / ".join(str(s.get(k, "")) for k in ("title_unic", "title_itrans", "title") if s.get(k))
        print(f"  {sid}: {title}")
        if re.search(r"z?[sS]h?A?r[ṅ~N]*g|शार्ङ्ग|शाङ्र्ग|sharng|zAr|SAr", title, re.I):
            targets.append((sid, title))

    if not targets:
        print("\nNo Śārṅgadhara entry matched automatically -- the list above "
              "will tell us its id.")
        return

    for sid, title in targets:
        print(f"\n=== Probing {sid}: {title} ===")
        call(f"sam{sid}_getselsamhitadet", request="getselsamhitadet", sam_id=sid)
        sthanas = call(f"sam{sid}_getstanadets", request="getstanadets", sam_id=sid)
        if not isinstance(sthanas, list) or not sthanas:
            continue
        st = sthanas[0]
        stid = first(st, "sthana_id", "sth_id", "stn_id", "sat_id", "id")
        chapters = call(f"sam{sid}_stn{stid}_getseladhyayadet",
                        request="getseladhyayadet", sam_id=sid, sat_id=stid)
        if not isinstance(chapters, list) or not chapters:
            continue
        ch = chapters[0]
        adid = first(ch, "adhyaya_id", "adhy_id", "ady_id", "id")
        call(f"sam{sid}_stn{stid}_ady{adid}_fullChapter",
             request="fullChapter", sam_id=sid, stn_id=stid, ady_id=adid)
        adhis = call(f"sam{sid}_stn{stid}_ady{adid}_getadhikaranadets",
                     request="getadhikaranadets", sam_id=sid, stn_id=stid, adhy_id=adid)
        adh = 1
        if isinstance(adhis, list) and adhis:
            adh = first(adhis[0], "adhi_no", "adh_id", "adhiseq", "id") or 1
        call(f"sam{sid}_stn{stid}_ady{adid}_adh{adh}_getvakyapadadet",
             request="getvakyapadadet", sam_id=sid, stn_id=stid, adhy_id=adid, ady_id=adid, adh_id=adh)
        call(f"sam{sid}_stn{stid}_ady{adid}_adh{adh}_getselvakyadet",
             request="getselvakyadet", sam_id=sid, stn_id=stid, ady_id=adid, adh_id=adh)

    print("\nDone. Please zip up  ccras_probe/  and send it back.")


if __name__ == "__main__":
    main()
