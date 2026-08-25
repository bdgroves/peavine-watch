"""
snow_watch.py - NDSI snow tracking at 7,574 ft, and the deadline it creates.

WHY THIS MATTERS HERE
Two reasons, pulling in opposite directions.

1. SNOW CLOSES THE ASSESSMENT WINDOW.
   dNBR needs a clear look at the ground. Once Peavine holds snow, optical burn
   severity is impossible until melt-out. At 2,309 m in the Carson Range that is
   roughly November through May. So there is a window - now until first
   persistent snow - to get a clean severity read. After that, nothing until spring.

2. SNOW IS ALSO THE SPRING HAZARD.
   Post-fire debris flows are usually discussed as a monsoon problem. At this
   elevation the bigger driver is snowmelt: hydrophobic soil, no canopy to
   intercept, no roots to hold, and weeks of sustained meltwater instead of a
   30-minute cloudburst. The cache sits in a drainage 31 m from a channel with
   214 cells of upslope contribution. Spring melt is when that channel moves.

NDSI = (green - swir16) / (green + swir16);  > 0.4 is the usual snow threshold.

FIXED 2026-08-25: an early run reported NDSI +0.31 and +0.35 (looks like snow)
on two smoky/cloudy Aug 23 scenes, while cleaner scenes the same day correctly
read -0.37 to -0.40. Smoke shares NDSI's green-bright/SWIR-dark signature with
snow. ndsi() now masks cloud/shadow/cirrus via the Scene Classification Layer
before computing anything, and this script also reports what fraction of the
site box survived masking - a low fraction means "don't trust this row," not
"no snow."

Also fixed: a crash on exit when eo:cloud_cover was missing from a scene's
properties (formatting None as a float). Guarded below.

    pixi run snow
"""
import os
import numpy as np
from peavine import search, ndsi, at_site, ring_stats, OUT

THRESHOLD = 0.4
MIN_VALID_FRAC = 0.5   # below this, don't trust the row


def main():
    os.makedirs(OUT, exist_ok=True)
    items = search("2026-08-23", "2027-06-30", max_cloud=60, limit=150)
    if not items:
        print("no post-fire scenes yet")
        return
    items.sort(key=lambda i: i.datetime)
    print(f"{len(items)} post-fire scenes\n")
    print(f"{'date':<12}{'cloud':>7}{'valid%':>8}{'NDSI@site':>11}{'mean150m':>10}  state")
    print("-" * 64)
    rows = []
    for it in items:
        cloud = it.properties.get("eo:cloud_cover")
        cloud = float(cloud) if cloud is not None else float("nan")
        try:
            d = ndsi(it)
            v = at_site(d)
            s = ring_stats(d, radius_m=150)
        except Exception as e:
            print(f"{it.datetime:%Y-%m-%d}  read failed: {str(e)[:40]}")
            continue

        valid_frac = s.get("valid_frac", 0.0)
        m = s.get("mean", float("nan"))
        if valid_frac < MIN_VALID_FRAC:
            state = "UNRELIABLE (too cloudy after masking)"
        else:
            state = "SNOW" if (np.isfinite(v) and v > THRESHOLD) else "bare"

        print(f"{it.datetime:%Y-%m-%d}{cloud:>7.1f}{100*valid_frac:>7.0f}%"
              f"{v:>11.3f}{m:>10.3f}  {state}")
        rows.append((it.datetime, v, m, state, valid_frac))

    usable = [r for r in rows if r[4] >= MIN_VALID_FRAC]
    bare = [r for r in usable if r[3] == "bare"]
    snow = [r for r in usable if r[3] == "SNOW"]
    skipped = len(rows) - len(usable)
    print(f"\n  {len(bare)} bare-ground scenes | {len(snow)} snow-covered | "
          f"{skipped} unreliable (skipped from the counts above)")
    if snow:
        print(f"  first RELIABLE snow detection: {snow[0][0]:%Y-%m-%d}")
        print("  -> optical burn severity is unreliable from this date until melt-out")
    else:
        print("  no reliable snow detection yet - the assessment window is still open")
        if bare:
            print(f"  most recent clear look: {bare[-1][0]:%Y-%m-%d}")


if __name__ == "__main__":
    main()
