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

    pixi run snow
"""
import os
import numpy as np
from peavine import search, ndsi, at_site, ring_stats, OUT

THRESHOLD = 0.4


def main():
    os.makedirs(OUT, exist_ok=True)
    items = search("2026-08-23", "2027-06-30", max_cloud=45, limit=120)
    if not items:
        print("no post-fire scenes yet"); return
    items.sort(key=lambda i: i.datetime)
    print(f"{len(items)} post-fire scenes\n")
    print(f"{'date':<12}{'cloud':>7}{'NDSI@site':>11}{'mean300m':>10}  state")
    print("-" * 56)
    rows = []
    for it in items:
        try:
            d = ndsi(it)
            v = at_site(d)
            s = ring_stats(d)
        except Exception as e:
            print(f"{it.datetime:%Y-%m-%d}  read failed: {str(e)[:34]}")
            continue
        m = s.get("mean", float("nan"))
        state = "SNOW" if (np.isfinite(v) and v > THRESHOLD) else "bare"
        print(f"{it.datetime:%Y-%m-%d}{it.properties.get('eo:cloud_cover',0):>7.1f}"
              f"{v:>11.3f}{m:>10.3f}  {state}")
        rows.append((it.datetime, v, m, state))

    bare = [r for r in rows if r[3] == "bare"]
    snow = [r for r in rows if r[3] == "SNOW"]
    print(f"\n  {len(bare)} bare-ground scenes | {len(snow)} snow-covered")
    if snow:
        print(f"  first snow detected: {snow[0][0]:%Y-%m-%d}")
        print("  -> optical burn severity is unreliable from this date until melt-out")
    else:
        print("  no snow yet - the assessment window is still open")
        if bare:
            print(f"  most recent clear look: {bare[-1][0]:%Y-%m-%d}")


if __name__ == "__main__":
    main()
