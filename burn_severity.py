"""
burn_severity.py - dNBR and RdNBR burn severity at the GC1CG0A cache site.

dNBR = NBR_prefire - NBR_postfire

NBR uses NIR vs SWIR2. Healthy vegetation is bright in NIR and dark in SWIR2,
so NBR is high. Fire strips chlorophyll and canopy moisture and exposes char
and bare soil, which flips that relationship - NBR drops hard. The DIFFERENCE
between before and after isolates the change caused by the fire rather than
whatever the site looked like to begin with.

RdNBR = dNBR / sqrt(|NBR_prefire|), USGS-scaled
A dense aspen grove and sparse sagebrush losing the "same" dNBR are not equally
burned - the grove had far more canopy to lose. RdNBR corrects for that
pre-fire baseline. Reported alongside dNBR, not in place of it: no hard severity
thresholds are applied to RdNBR here, because published breakpoints were
calibrated on other ecosystems and do not transfer cleanly to a Great Basin
aspen/sagebrush mosaic (see peavine.rdnbr docstring).

CAVEAT WORTH KEEPING IN MIND
Both indices measure vegetation and surface change from above. Neither is soil
burn severity - that is what BAER field teams assess, and it drives debris-flow
risk. A grove can read high on dNBR while the soil underneath is only lightly
burned, or the reverse.

DATA QUALITY GUARDS (added 2026-08-25)
  - Pre and post scenes are required to share an MGRS tile (see find_pair()).
  - Both scenes are cloud/shadow/cirrus masked via the Scene Classification
    Layer before any ratio is computed.
  - If less than half the ~300 m box around the site is valid after masking,
    the site-level numbers are flagged UNRELIABLE rather than reported as fact.

    pixi run severity
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from peavine import (find_pair, nbr, rdnbr, at_site, ring_stats, classify, OUT,
                     CACHE_LAT, CACHE_LON, DNBR_CLASSES, tile_id)


def main():
    os.makedirs(OUT, exist_ok=True)
    print("Searching Sentinel-2 for a same-tile pre/post pair (AWS Earth Search, no auth)...")
    pre, post = find_pair("2026-07-01", "2026-08-22", "2026-08-23", "2026-12-31", max_cloud=40)
    if pre is None or post is None:
        print("\n  No same-tile pre/post pair found yet.")
        print("  Sentinel-2 revisits every ~5 days - try again shortly, or widen the")
        print("  post-fire date range once more cloud-free scenes exist.")
        return

    print(f"  PRE  {pre.datetime:%Y-%m-%d}  cloud {pre.properties.get('eo:cloud_cover',0):.1f}%  tile {tile_id(pre)}  {pre.id}")
    print(f"  POST {post.datetime:%Y-%m-%d}  cloud {post.properties.get('eo:cloud_cover',0):.1f}%  tile {tile_id(post)}  {post.id}")
    gap = (post.datetime - pre.datetime).days
    print(f"\n  {gap} days between scenes, same MGRS tile\n")

    fire_out_cutoff = post.datetime.tzinfo is not None
    cutoff = np.datetime64("2026-08-24T00:00:00")
    post_naive = post.datetime.replace(tzinfo=None) if fire_out_cutoff else post.datetime
    if np.datetime64(post_naive) < cutoff:
        print("  NOTE: this post-fire scene may predate full containment. Active flame")
        print("        and heavy smoke both distort NBR - treat an early read as provisional")
        print("        and re-run once the fire is out and a clear scene exists.\n")

    print("Reading bands, masking clouds/shadow/cirrus via SCL, computing NBR...")
    nbr_pre, nbr_post = nbr(pre), nbr(post)
    if nbr_pre.shape != nbr_post.shape:
        nbr_post = nbr_post.rio.reproject_match(nbr_pre)
    dnbr = nbr_pre - nbr_post
    rd = rdnbr(dnbr, nbr_pre)

    v_pre, v_post, v_d, v_rd = at_site(nbr_pre), at_site(nbr_post), at_site(dnbr), at_site(rd)
    stats = ring_stats(dnbr, radius_m=150)
    reliable = stats.get("valid_frac", 0) >= 0.5

    print("\n" + "=" * 66)
    print("BURN SEVERITY AT THE CACHE  (39.58475 N, -119.94228 W)")
    print("=" * 66)
    if not reliable:
        print("  *** LOW CONFIDENCE: fewer than half the nearby pixels survived   ***")
        print("  *** cloud/shadow masking. Numbers below may be noise. Re-run     ***")
        print("  *** once a clearer post-fire scene is available.                ***\n")
    print(f"  NBR pre-fire   {v_pre:+.3f}")
    print(f"  NBR post-fire  {v_post:+.3f}")
    print(f"  dNBR           {v_d:+.3f}   ->  {classify(v_d).upper()}")
    print(f"  RdNBR          {v_rd:+.1f}  (relativized; no hard class applied - see docstring)")
    if stats.get("n"):
        print(f"\n  within {150} m radius (~{300} m box): {stats['n']}/{stats['total']} pixels valid "
              f"({100*stats['valid_frac']:.0f}%)")
        print(f"    mean dNBR {stats['mean']:+.3f}  ->  {classify(stats['mean'])}")
        print(f"    range     {stats['min']:+.3f} to {stats['max']:+.3f}")
        print(f"    median    {stats['p50']:+.3f}")
    else:
        print("\n  no valid pixels within 150 m after cloud masking")

    vals = dnbr.values[np.isfinite(dnbr.values)]
    if vals.size:
        print(f"\n  severity mix across the {vals.size:,} valid pixels in the AOI:")
        for lo, hi, name in DNBR_CLASSES:
            n = int(((vals >= lo) & (vals <= hi)).sum())
            if n:
                print(f"    {name:<28}{n:>8,}  {100*n/vals.size:>5.1f}%")

    dnbr.rio.to_raster(os.path.join(OUT, "dnbr.tif"))
    rd.rio.to_raster(os.path.join(OUT, "rdnbr.tif"))
    nbr_pre.rio.to_raster(os.path.join(OUT, "nbr_pre.tif"))
    nbr_post.rio.to_raster(os.path.join(OUT, "nbr_post.tif"))

    fig, ax = plt.subplots(1, 4, figsize=(21, 5))
    panels = [
        (ax[0], nbr_pre,  f"NBR pre-fire {pre.datetime:%b %d}",  "RdYlGn", (-1, 1)),
        (ax[1], nbr_post, f"NBR post-fire {post.datetime:%b %d}", "RdYlGn", (-1, 1)),
        (ax[2], dnbr,     "dNBR (burn severity)",                 "inferno_r", (-0.1, 1.0)),
        (ax[3], rd,       "RdNBR (relativized)",                  "inferno_r", (-200, 1200)),
    ]
    for a, d, t, cm, vr in panels:
        im = a.imshow(d.values, cmap=cm, vmin=vr[0], vmax=vr[1],
                      extent=[float(d.x.min()), float(d.x.max()),
                              float(d.y.min()), float(d.y.max())])
        a.plot(CACHE_LON, CACHE_LAT, marker="*", ms=16, mfc="cyan", mec="black", mew=1.2)
        a.set_title(t, fontsize=10); a.set_xticks([]); a.set_yticks([])
        plt.colorbar(im, ax=a, fraction=0.046)
    plt.suptitle(f"Hawk Fire / GC1CG0A - Peavine Mountain NV  "
                f"(tile {tile_id(pre)}, {gap}d apart, cloud-masked)", fontsize=12)
    plt.tight_layout()
    png = os.path.join(OUT, "burn_severity.png")
    plt.savefig(png, dpi=140)
    print("\n  wrote dnbr.tif, rdnbr.tif, nbr_pre.tif, nbr_post.tif")
    print(f"  wrote {png}")
    print("\n  Load dnbr.tif in QGIS to see it against the VIIRS detections and drainage.")


if __name__ == "__main__":
    main()
