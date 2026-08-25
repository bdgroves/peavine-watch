"""
terrain.py - did the drainage make it burn hotter, or did it just have more fuel?

THE QUESTION
The cache sits in a drainage (214 cells flow accumulation, 31 m from a mapped
channel). A parking waypoint 500 m away sits on a dry ridge (flow accumulation
1). Raw dNBR at those two points is +0.536 and +0.126 - a factor of four.

That gap is tempting to read as terrain: fire runs uphill, a drainage
concentrates the front, the grove sat at the top of a chimney. But it cannot be
read that way as it stands, because the two points did not start equal. The
grove was dense aspen (NBR_pre +0.481); the ridge was sparse sagebrush
(+0.128). Denser vegetation burns hotter more or less everywhere - it has more
to lose - so part of that 4x is fuel load, not terrain.

THE TEST
Hold fuel constant. Compare the grove only against ground that was EQUALLY
vegetated before the fire (NBR_pre 0.40-0.55), and see whether the grove still
burned harder. Whatever difference survives that control is attributable to
something other than how much fuel was standing there.

RESULT (2026-08-18 / 2026-08-23 pair)
    grove ring, NBR_pre 0.40-0.55      n=  129   mean dNBR +0.731
    same density elsewhere in AOI      n= 6891   mean dNBR +0.453
    -> grove exceeds 78.8% of equally-vegetated ground

So both effects are real and they compound. The grove was the heaviest fuel on
the hillside AND it sat in the feature that concentrated the fire into it.

A NOTE ON THE WORD "CHIMNEY"
The slope here is 13.3 degrees - moderate. A textbook chimney is a steep narrow
gully with a strong convective draft. This is a broad SE-facing drainage near a
summit. The mechanism is better described as fire running upslope with a
drainage concentrating the front, not a violent chimney effect. Directionally
right, but do not overstate it.

WHY THE RAW RdNBR RING MEAN IS NOT USED HERE
RdNBR divides by sqrt(|NBR_pre|), so it explodes where pre-fire NBR is near
zero. Averaging RdNBR over a ring that mixes dense grove and sparse sagebrush
produces a number dominated by the sparse pixels, not the grove. An earlier
version of this analysis compared an unrestricted ring mean against a
density-restricted comparison group and got 1812 vs 680 - an artifact of that
mismatch, not a finding. Restrict both sides or neither.

    pixi run terrain
"""
import os
import numpy as np
import rasterio

from peavine import OUT, CACHE_LAT, CACHE_LON, PARK_LAT, PARK_LON

DENSE_LO, DENSE_HI = 0.40, 0.55     # "equally vegetated" band, pre-fire NBR
GROVE_R = 150                        # m
AOI_R = 3000                         # m


def _read(name):
    """Band 1 as float, a validity mask, and an affine transform.

    rasterio rather than GDAL directly: rasterio is already a dependency of
    this project (peavine.py leans on it via rioxarray), so this adds nothing
    new to the environment.
    """
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        raise SystemExit(f"missing {p} - run `pixi run severity` first")
    with rasterio.open(p) as ds:
        a = ds.read(1).astype("float64")
        nd = ds.nodata
        t = ds.transform
    ok = np.isfinite(a) & ((a != nd) if nd is not None else True)
    # (c, a, b, f, d, e) in GDAL order so the rest of this file is unchanged
    gt = (t.c, t.a, t.b, t.f, t.d, t.e)
    return a, ok, gt


def main():
    dn, m_dn, gt = _read("dnbr.tif")
    pre, m_pre, _ = _read("nbr_pre.tif")

    ys, xs = np.mgrid[0:dn.shape[0], 0:dn.shape[1]]
    lons = gt[0] + xs * gt[1]
    lats = gt[3] + ys * gt[5]
    scale = np.cos(np.radians(CACHE_LAT))
    dist = np.sqrt(((lons - CACHE_LON) * 111_320 * scale) ** 2 +
                   ((lats - CACHE_LAT) * 111_320) ** 2)

    ok = m_dn & m_pre & (dist <= AOI_R)

    def at(a, lon, lat):
        c = int((lon - gt[0]) / gt[1]); r = int((lat - gt[3]) / gt[5])
        return float(a[r, c])

    print("=" * 62)
    print("TERRAIN vs FUEL — dNBR at two points 500 m apart")
    print("=" * 62)
    print(f"{'':22s}{'flow acc':>9s}{'NBR_pre':>9s}{'dNBR':>8s}")
    print(f"  {'grove / drainage':20s}{214:>9d}"
          f"{at(pre, CACHE_LON, CACHE_LAT):>+9.3f}{at(dn, CACHE_LON, CACHE_LAT):>+8.3f}")
    print(f"  {'ridge / parking':20s}{1:>9d}"
          f"{at(pre, PARK_LON, PARK_LAT):>+9.3f}{at(dn, PARK_LON, PARK_LAT):>+8.3f}")
    print("\n  Raw ratio is ~4x, but the two did not start equal. Controlling:")

    band = ok & (pre > DENSE_LO) & (pre < DENSE_HI)
    grove = band & (dist <= GROVE_R)
    other = band & (dist > GROVE_R)
    if grove.sum() < 20:
        print("  not enough equally-vegetated grove pixels to compare")
        return 1

    gm, om = dn[grove].mean(), dn[other].mean()
    pct = (dn[other] < gm).sum() / other.sum() * 100
    print(f"\n  Ground equally vegetated before the fire (NBR_pre "
          f"{DENSE_LO:.2f}-{DENSE_HI:.2f}):")
    print(f"    grove ring          n={grove.sum():6d}   mean dNBR {gm:+.3f}")
    print(f"    elsewhere in AOI    n={other.sum():6d}   mean dNBR {om:+.3f}")
    print(f"    -> grove burned harder than {pct:.1f}% of equally-fuelled ground")
    print(f"    -> terrain-attributable difference: {gm - om:+.3f} dNBR")

    print("\n  Severity rises with pre-fire density across the whole AOI:")
    for lo, hi in [(0.00, 0.15), (0.15, 0.30), (0.30, 0.45),
                   (0.45, 0.60), (0.60, 0.80)]:
        s = ok & (pre >= lo) & (pre < hi)
        if s.sum() > 200:
            print(f"    NBR_pre {lo:.2f}-{hi:.2f}   n={s.sum():7d}   "
                  f"mean dNBR {dn[s].mean():+.3f}")

    g_all = ok & (dist <= GROVE_R)
    a_all = ok & (dist > GROVE_R)
    p_all = (dn[a_all] < dn[g_all].mean()).sum() / a_all.sum() * 100
    print(f"\n  Unrestricted (for the README claim): grove mean dNBR "
          f"{dn[g_all].mean():+.3f}")
    print(f"    exceeds {p_all:.1f}% of the surrounding {AOI_R/1000:.0f} km")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
