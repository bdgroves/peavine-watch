"""
burn_severity.py - dNBR burn severity at the GC1CG0A cache site.

dNBR = NBR_prefire - NBR_postfire

NBR uses NIR vs SWIR2. Healthy vegetation is bright in NIR and dark in SWIR2,
so NBR is high. Fire strips chlorophyll and canopy moisture and exposes char
and bare soil, which flips that relationship - NBR drops hard. The DIFFERENCE
between before and after isolates the change caused by the fire rather than
whatever the site looked like to begin with. That matters here: an aspen grove
and a sagebrush slope have very different baseline NBR, and only dNBR tells you
how much each one actually changed.

CAVEAT WORTH KEEPING IN MIND
dNBR measures vegetation and surface change from above. It is NOT soil burn
severity - that is what BAER field teams assess, and it drives debris-flow risk.
A grove can read moderate on dNBR while the soil underneath is severely burned,
or the reverse. Treat this as an indicator, not a verdict.

    pixi run severity
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from peavine import (search, nbr, at_site, ring_stats, classify, OUT,
                     CACHE_LAT, CACHE_LON, DNBR_CLASSES)


def pick(items, label):
    if not items:
        print(f"  no {label} scene found"); return None
    it = items[0]
    print(f"  {label:<10} {it.datetime:%Y-%m-%d}  cloud {it.properties.get('eo:cloud_cover',0):.1f}%  {it.id}")
    return it


def main():
    os.makedirs(OUT, exist_ok=True)
    print("Searching Sentinel-2 (AWS Earth Search, no auth)...")
    pre  = pick(search("2026-07-15", "2026-08-22", max_cloud=15), "PRE-FIRE")
    post = pick(search("2026-08-23", "2026-12-31", max_cloud=35), "POST-FIRE")
    if pre is None or post is None:
        print("\nNeed both a pre and post scene. If post is missing, Sentinel-2 "
              "revisits every ~5 days - try again in a few days.")
        return

    gap = (post.datetime - pre.datetime).days
    print(f"\n  {gap} days between scenes\n")

    print("Reading bands and computing NBR...")
    nbr_pre, nbr_post = nbr(pre), nbr(post)
    if nbr_pre.shape != nbr_post.shape:
        nbr_post = nbr_post.rio.reproject_match(nbr_pre)
    dnbr = nbr_pre - nbr_post

    v_pre, v_post, v_d = at_site(nbr_pre), at_site(nbr_post), at_site(dnbr)
    stats = ring_stats(dnbr)

    print("\n" + "=" * 66)
    print("BURN SEVERITY AT THE CACHE  (39.58475 N, -119.94228 W)")
    print("=" * 66)
    print(f"  NBR pre-fire   {v_pre:+.3f}")
    print(f"  NBR post-fire  {v_post:+.3f}")
    print(f"  dNBR           {v_d:+.3f}   ->  {classify(v_d).upper()}")
    if stats:
        print(f"\n  within ~300 m ({stats['n']} pixels)")
        print(f"    mean dNBR {stats['mean']:+.3f}  ->  {classify(stats['mean'])}")
        print(f"    range     {stats['min']:+.3f} to {stats['max']:+.3f}")
        print(f"    median    {stats['p50']:+.3f}")

    vals = dnbr.values[np.isfinite(dnbr.values)]
    if vals.size:
        print(f"\n  severity mix across the {vals.size:,}-pixel AOI:")
        for lo, hi, name in DNBR_CLASSES:
            n = int(((vals >= lo) & (vals <= hi)).sum())
            if n:
                print(f"    {name:<28}{n:>8,}  {100*n/vals.size:>5.1f}%")

    dnbr.rio.to_raster(os.path.join(OUT, "dnbr.tif"))
    nbr_pre.rio.to_raster(os.path.join(OUT, "nbr_pre.tif"))
    nbr_post.rio.to_raster(os.path.join(OUT, "nbr_post.tif"))

    fig, ax = plt.subplots(1, 3, figsize=(16, 5))
    for a, d, t, cm, vr in [
        (ax[0], nbr_pre,  f"NBR pre-fire {pre.datetime:%b %d}",  "RdYlGn", (-1, 1)),
        (ax[1], nbr_post, f"NBR post-fire {post.datetime:%b %d}", "RdYlGn", (-1, 1)),
        (ax[2], dnbr,     "dNBR (burn severity)",                 "inferno_r", (-0.1, 1.0))]:
        im = a.imshow(d.values, cmap=cm, vmin=vr[0], vmax=vr[1],
                      extent=[float(d.x.min()), float(d.x.max()),
                              float(d.y.min()), float(d.y.max())])
        a.plot(CACHE_LON, CACHE_LAT, marker="*", ms=16, mfc="cyan", mec="black", mew=1.2)
        a.set_title(t, fontsize=10); a.set_xticks([]); a.set_yticks([])
        plt.colorbar(im, ax=a, fraction=0.046)
    plt.suptitle("Hawk Fire / GC1CG0A - Peavine Mountain NV", fontsize=12)
    plt.tight_layout()
    png = os.path.join(OUT, "burn_severity.png")
    plt.savefig(png, dpi=140)
    print(f"\n  wrote dnbr.tif, nbr_pre.tif, nbr_post.tif")
    print(f"  wrote {png}")
    print("\n  Load dnbr.tif in QGIS to see it against the VIIRS detections and drainage.")


if __name__ == "__main__":
    main()
