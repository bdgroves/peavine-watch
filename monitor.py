"""
monitor.py - one row per Sentinel-2 pass, appended to out/timeseries.json.

WHAT THIS IS FOR
burn_severity.py answers "how bad was it" once. This answers "what is happening
now", every time the satellite comes back, and keeps every previous answer. The
question the repo actually cares about - whether the aspen grove resprouts - is
not a single number, it is a curve over several growing seasons.

WHAT IT RECORDS, PER SCENE
  NBR   burn/recovery of canopy+soil moisture   (SWIR2-based, slow to recover)
  NDVI  green-up                                (red-based, moves first)
  NDSI  snow                                    (closes the optical window)
each at the cache pixel, averaged over a 150 m radius around the grove, AND
averaged over an unburned control stand 3 km away, plus dNBR and RdNBR against
a fixed pre-fire baseline.

WHY A CONTROL
Vegetation senesces every autumn and greens up every spring regardless of fire.
Without a reference, an October NDVI decline at the grove cannot be told apart
from continued fire-driven decline, and next May's green-up cannot be told apart
from ordinary phenology. The control stand experiences the same season, sun
angle and atmosphere, so `delta` (grove minus control) isolates what the fire
did. That difference, not the raw grove curve, is the number to watch.

DESIGN NOTES
  - Idempotent. Scenes already in the file are skipped, so this can run daily
    against a ~5 day satellite revisit without duplicating anything.
  - The pre-fire baseline is pinned to ONE scene and reused forever. Re-deriving
    it per run would let the reference drift, and every dNBR in the series would
    stop being comparable to the ones before it.
  - Same-tile discipline from find_pair() applies here too: an observation is
    only compared against a baseline from the same MGRS tile. Cross-tile rows
    are recorded but flagged, never silently differenced.
  - Anything under 50% valid pixels after SCL masking is written with
    reliable=false rather than dropped. A smoky scene is data about smoke.

    pixi run watch
"""
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

from peavine import (search, band, cloud_mask, nbr, ndvi, ndsi, rdnbr, at_site,
                     ring_stats, classify, tile_id, _cloud, OUT,
                     CACHE_LAT, CACHE_LON, CTRL_LAT, CTRL_LON, IGNITION)

SERIES = os.path.join(OUT, "timeseries.json")
GROVE_RADIUS_M = 150
MIN_VALID = 0.50


def load():
    if os.path.exists(SERIES):
        with open(SERIES, encoding="utf-8") as f:
            return json.load(f)
    return {
        "site": {
            "name": "GC1CG0A - Basque Sheepherder: The High Camp",
            "lat": CACHE_LAT, "lon": CACHE_LON,
            "elevation_m": 2309, "aspect": "SE", "slope_deg": 13.3,
            "fire": "Hawk Fire", "ignition_utc": IGNITION,
        },
        "baseline": None,
        "observations": [],
    }


def measure(item):
    """All three indices at the site and over the grove, for one scene."""
    row = {
        "scene_id": item.id,
        "date": item.datetime.strftime("%Y-%m-%d"),
        "datetime_utc": item.datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tile": tile_id(item),
        "cloud_pct": round(_cloud(item), 1),
    }
    site, grove, control = {}, {}, {}
    valid = 0.0
    for name, fn in (("nbr", nbr), ("ndvi", ndvi), ("ndsi", ndsi)):
        da = fn(item)
        v = at_site(da)
        site[name] = None if not np.isfinite(v) else round(float(v), 4)

        st = ring_stats(da, radius_m=GROVE_RADIUS_M)
        if st.get("n"):
            grove[name] = round(st["mean"], 4)
            valid = max(valid, st["valid_frac"])
        else:
            grove[name] = None

        ct = ring_stats(da, lat=CTRL_LAT, lon=CTRL_LON, radius_m=GROVE_RADIUS_M)
        control[name] = round(ct["mean"], 4) if ct.get("n") else None

    row["site"] = site
    row["grove"] = grove
    row["control"] = control

    # The headline recovery number. Season, sun angle and atmosphere hit both
    # stands equally, so the difference isolates what the fire did - and, later,
    # how much of the grove has come back relative to ground that never burned.
    row["delta"] = {
        k: (None if grove.get(k) is None or control.get(k) is None
            else round(grove[k] - control[k], 4))
        for k in ("nbr", "ndvi", "ndsi")
    }
    row["valid_frac"] = round(valid, 3)
    row["reliable"] = valid >= MIN_VALID
    return row


def set_baseline(doc):
    """Pin the pre-fire reference to a single clean scene, once."""
    if doc.get("baseline"):
        return doc["baseline"]
    print("No baseline yet - selecting a clean pre-fire scene...")
    items = search("2026-06-01", "2026-08-22", max_cloud=15)
    if not items:
        print("  none found under 15% cloud")
        return None
    item = max(items, key=lambda i: i.datetime)   # closest to the fire
    row = measure(item)
    row["note"] = "pre-fire baseline, pinned - do not recompute"
    doc["baseline"] = row
    print(f"  baseline {row['date']}  tile {row['tile']}  "
          f"cloud {row['cloud_pct']}%  NBR {row['site']['nbr']}")
    return row


def main():
    os.makedirs(OUT, exist_ok=True)
    doc = load()
    base = set_baseline(doc)

    seen = {o["scene_id"] for o in doc["observations"]}
    if base:
        seen.add(base["scene_id"])

    print(f"\n{len(doc['observations'])} observations on file. Searching for new passes...")
    items = search("2026-08-23", "2027-12-31", max_cloud=60)
    new = [i for i in items if i.id not in seen]
    if not new:
        print("  nothing new since last run")
    new.sort(key=lambda i: i.datetime)

    for item in new:
        print(f"\n  {item.datetime:%Y-%m-%d}  tile {tile_id(item)}  cloud {_cloud(item):.1f}%")
        try:
            row = measure(item)
        except Exception as e:
            print(f"    skipped - {type(e).__name__}: {e}")
            continue

        if base and row["tile"] == base["tile"] and row["reliable"] \
                and row["site"]["nbr"] is not None and base["site"]["nbr"] is not None:
            d = base["site"]["nbr"] - row["site"]["nbr"]
            row["dnbr"] = round(d, 4)
            row["dnbr_class"] = classify(d)
            with np.errstate(divide="ignore", invalid="ignore"):
                rv = (d * 1000.0) / np.sqrt(abs(base["site"]["nbr"]))
            row["rdnbr"] = None if not np.isfinite(rv) else round(float(rv), 1)
        else:
            row["dnbr"] = None
            row["dnbr_class"] = None
            row["rdnbr"] = None
            if base and row["tile"] != base["tile"]:
                row["note"] = f"different MGRS tile from baseline ({base['tile']}) - not differenced"
            elif not row["reliable"]:
                row["note"] = "under 50% valid pixels after SCL masking - indices unreliable"

        doc["observations"].append(row)
        flag = "" if row["reliable"] else "  UNRELIABLE"
        print(f"    NBR {row['site']['nbr']}  NDVI {row['site']['ndvi']}  "
              f"NDSI {row['site']['ndsi']}  valid {row['valid_frac']:.0%}{flag}")
        if row["delta"]["ndvi"] is not None:
            print(f"    grove NDVI {row['grove']['ndvi']}  vs unburned control "
                  f"{row['control']['ndvi']}  ->  delta {row['delta']['ndvi']:+.4f}")
        if row.get("dnbr") is not None:
            print(f"    dNBR {row['dnbr']}  ({row['dnbr_class']})  RdNBR {row['rdnbr']}")
        if row.get("note"):
            print(f"    note: {row['note']}")

    doc["observations"].sort(key=lambda o: o["datetime_utc"])
    doc["updated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with open(SERIES, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)

    n_ok = sum(1 for o in doc["observations"] if o["reliable"])
    print(f"\nWrote {SERIES}")
    print(f"  {len(doc['observations'])} observations ({n_ok} reliable), "
          f"{len(new)} added this run")


if __name__ == "__main__":
    sys.exit(main())
