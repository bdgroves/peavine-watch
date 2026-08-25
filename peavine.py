"""
peavine.py - shared helpers. Sentinel-2 L2A from AWS Earth Search (no auth, no key).

SITE
  GC1CG0A "Basque Sheepherder: The High Camp"
  39.58475 N, -119.94228 W  |  2,309 m / 7,574 ft  |  SE aspect, 13.3 deg
  Sits in a drainage: 214 cells flow accumulation, 31 m from a mapped channel.

FIRE
  Hawk Fire, human-caused, ignited 2026-08-22 18:23 UTC (11:23 PDT), ~5 mi N of Reno.
  VIIRS put fire 315 m from the site 92 minutes after ignition; 79 m by 14:16 PDT.
  Brightness temperature saturated the sensor (367 K) on most nearby detections.

BANDS (Earth Search asset keys)
  green=B03 10m   red=B04 10m   nir=B08 10m   swir16=B11 20m   swir22=B12 20m
  scl  = Scene Classification Layer, 20m (cloud/shadow/snow/etc per pixel)
  NBR  = (nir - swir22) / (nir + swir22)      burn severity
  NDSI = (green - swir16) / (green + swir16)  snow index

WHY SAME-TILE MATTERS (fixed 2026-08-25)
Peavine sits ~2 km east of the UTM zone 10/11 boundary, so it is covered by two
MGRS tiles (10SGJ and 11SKD). Picking pre and post scenes independently by cloud
cover alone can silently pick one from each tile - different reprojection and
resampling paths for the same ground, which introduces registration error right
at feature boundaries (like a grove edge) where it matters most. find_pair()
below only considers same-tile combinations.

WHY THE SCL MASK MATTERS (fixed 2026-08-25)
An early run of snow_watch.py reported NDSI = +0.31 and +0.35 (looks like snow)
on two Aug 23 scenes with 22-25% cloud, while two cleaner scenes the same day
read -0.37 to -0.40 (correctly bare). Smoke and cloud share the same green-bright /
SWIR-dark signature NDSI is built on, so a smoky scene can fake a snow signal.
Both nbr() and ndsi() now mask out SCL classes 3 (cloud shadow), 8/9 (cloud
medium/high probability), and 10 (thin cirrus) before computing anything.
"""
import os
import numpy as np
import rioxarray  # noqa: F401  (registers .rio accessor)
from collections import defaultdict
from pystac_client import Client

STAC = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-l2a"

CACHE_LAT, CACHE_LON = 39.58475, -119.94228
PARK_LAT, PARK_LON = 39.583667, -119.936350
IGNITION = "2026-08-22T18:23:00Z"
BOX_DEG = 0.035          # ~3.5 km half-width around the site
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

# SCL classes to exclude before any index is computed. 11 (snow/ice) is kept -
# ndsi's whole job is finding that class, so masking it out would be circular.
SCL_INVALID = {0, 1, 3, 8, 9, 10}   # no-data, saturated, cloud shadow, cloud x2, cirrus


def aoi():
    return (CACHE_LON - BOX_DEG, CACHE_LAT - BOX_DEG,
            CACHE_LON + BOX_DEG, CACHE_LAT + BOX_DEG)


def tile_id(item):
    """MGRS tile from the item id, e.g. 'S2A_11SKD_20260803_1_L2A' -> '11SKD'."""
    parts = item.id.split("_")
    return parts[1] if len(parts) > 1 else item.id


def _cloud(item):
    c = item.properties.get("eo:cloud_cover")
    return float(c) if c is not None else 100.0


def search(start, end, max_cloud=35, limit=100):
    """Scenes over the site in a date range, least cloudy first."""
    cat = Client.open(STAC)
    res = cat.search(collections=[COLLECTION], bbox=aoi(),
                     datetime=f"{start}/{end}",
                     query={"eo:cloud_cover": {"lt": max_cloud}}, limit=limit)
    items = list(res.items())
    items.sort(key=_cloud)
    return items


def find_pair(pre_start, pre_end, post_start, post_end, max_cloud=40,
             prefer_recent_pre=True):
    """Best same-tile pre/post pair. Returns (pre_item, post_item) or (None, None).

    Only pairs sharing an MGRS tile are considered, so pre and post never come
    from different UTM zones. Within a tile: post picks lowest cloud; pre picks
    lowest cloud too, unless prefer_recent_pre, in which case it prefers the
    most recent scene under a stricter 15% cloud cap (closer to the fire date
    means less chance of vegetation state drifting between the two looks).
    """
    pre_items = search(pre_start, pre_end, max_cloud=max_cloud)
    post_items = search(post_start, post_end, max_cloud=max_cloud)
    if not pre_items or not post_items:
        return None, None

    pre_by_tile, post_by_tile = defaultdict(list), defaultdict(list)
    for i in pre_items:
        pre_by_tile[tile_id(i)].append(i)
    for i in post_items:
        post_by_tile[tile_id(i)].append(i)

    shared = set(pre_by_tile) & set(post_by_tile)
    if not shared:
        return None, None

    candidates = []
    for t in shared:
        ps = pre_by_tile[t]
        clean = [i for i in ps if _cloud(i) < 15]
        if prefer_recent_pre and clean:
            pre_best = max(clean, key=lambda i: i.datetime)
        else:
            pre_best = min(ps, key=_cloud)
        post_best = min(post_by_tile[t], key=_cloud)
        candidates.append((_cloud(pre_best) + _cloud(post_best), t, pre_best, post_best))

    candidates.sort(key=lambda x: x[0])
    _, tile, pre, post = candidates[0]
    return pre, post


def band(item, key):
    """Read one band clipped to the AOI, as a float array in EPSG:4326."""
    href = item.assets[key].href
    da = rioxarray.open_rasterio(href, masked=True, chunks=None)
    da = da.rio.reproject("EPSG:4326")
    x0, y0, x1, y1 = aoi()
    da = da.rio.clip_box(minx=x0, miny=y0, maxx=x1, maxy=y1)
    return da.squeeze().astype("float32")


def cloud_mask(item, like):
    """True where SCL says the pixel is usable, reprojected onto `like`'s grid."""
    scl = band(item, "scl")
    if scl.shape != like.shape:
        scl = scl.rio.reproject_match(like)
    invalid = np.isin(np.round(scl.values), list(SCL_INVALID))
    return ~invalid


def ratio(a, b, mask=None):
    """Normalised difference, matching grids if resolutions differ."""
    if a.shape != b.shape:
        b = b.rio.reproject_match(a)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = (a - b) / (a + b)
    if mask is not None:
        out = out.where(mask if hasattr(mask, "shape") and mask.shape == out.shape
                        else np.asarray(mask))
    return out


def nbr(item, masked=True):
    n = band(item, "nir")
    r = ratio(n, band(item, "swir22"))
    if masked:
        m = cloud_mask(item, r)
        r = r.where(m)
    return r


def ndsi(item, masked=True):
    r = ratio(band(item, "green"), band(item, "swir16"))
    if masked:
        m = cloud_mask(item, r)
        r = r.where(m)
    return r


def rdnbr(dnbr_da, nbr_pre_da):
    """Relativized dNBR (Miller & Thode 2007): dNBR_scaled / sqrt(|NBR_pre_scaled| / 1000).

    Normalises for pre-fire vegetation density. A dense aspen grove and sparse
    sagebrush losing the "same" dNBR are not equally burned - the grove had far
    more canopy to lose. RdNBR corrects for that baseline, which is exactly the
    grove-vs-sagebrush comparison this project cares about.

    FIXED 2026-08-25: the first version of this function divided by
    sqrt(|NBR_pre_scaled|) instead of sqrt(|NBR_pre_scaled| / 1000), which is
    missing a sqrt(1000) ~ 31.6x factor - it understated every RdNBR value by
    that much (reported +24 where the correct figure is +774). Caught by
    sanity-checking the first real output against published RdNBR ranges
    before trusting it. The two scale-by-1000 operations algebraically cancel
    to dnbr*1000/sqrt(|nbr_pre|), which is what's implemented below - simpler
    than it looks, but arrived at by working the formula through by hand
    rather than trusting the refactor.

    No hard severity thresholds are applied here: published RdNBR breakpoints
    were calibrated on specific ecosystems and do not transfer cleanly to a
    Great Basin aspen/sagebrush mosaic. Report the value; do not invent a
    classification for it.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        out = (dnbr_da * 1000.0) / np.sqrt(np.abs(nbr_pre_da))
    return out


def at_site(da, lat=CACHE_LAT, lon=CACHE_LON):
    """Value at the cache pixel."""
    try:
        return float(da.sel(x=lon, y=lat, method="nearest").values)
    except Exception:
        return float("nan")


def ring_stats(da, lat=CACHE_LAT, lon=CACHE_LON, radius_m=150):
    """Stats in a box of the given RADIUS (so ~2*radius_m across) around the site.

    Previous version took a `deg` half-width and mislabeled the printed size -
    deg=0.0027 is a 150 m radius / ~300 m box, but was printed as "~300 m" when
    it was actually being called with a value that produced a 600 m box in one
    caller. This version takes meters directly so the label always matches
    what was actually sampled.
    """
    deg = radius_m / 111_320.0
    sub = da.sel(x=slice(lon - deg, lon + deg), y=slice(lat + deg, lat - deg))
    total = sub.size
    v = sub.values[np.isfinite(sub.values)]
    if v.size == 0:
        return {"n": 0, "total": total, "valid_frac": 0.0}
    return {"n": int(v.size), "total": int(total), "valid_frac": v.size / total,
            "mean": float(v.mean()), "min": float(v.min()),
            "max": float(v.max()), "p50": float(np.percentile(v, 50))}


# USGS / FIREMON dNBR severity classes
DNBR_CLASSES = [
    (-9.99, -0.251, "Enhanced regrowth, high"),
    (-0.25, -0.101, "Enhanced regrowth, low"),
    (-0.10,  0.099, "Unburned"),
    ( 0.10,  0.269, "Low severity"),
    ( 0.27,  0.439, "Moderate-low severity"),
    ( 0.44,  0.659, "Moderate-high severity"),
    ( 0.66,  9.99,  "High severity"),
]


def classify(v):
    if v is None or not np.isfinite(v):
        return "no data"
    for lo, hi, name in DNBR_CLASSES:
        if lo <= v <= hi:
            return name
    return "out of range"


if __name__ == "__main__":
    print("Scenes over Peavine / GC1CG0A\n")
    for lbl, s, e in [("PRE-FIRE  (Jul 1 - Aug 22)", "2026-07-01", "2026-08-22"),
                      ("POST-FIRE (Aug 23 onward)", "2026-08-23", "2026-12-31")]:
        items = search(s, e)
        print(f"{lbl}: {len(items)} scenes under 35% cloud")
        for i in items[:8]:
            print(f"   {i.datetime:%Y-%m-%d}  cloud {_cloud(i):5.1f}%  tile {tile_id(i)}  {i.id}")
        print()

    print("Best same-tile pre/post pair:")
    pre, post = find_pair("2026-07-01", "2026-08-22", "2026-08-23", "2026-12-31")
    if pre and post:
        print(f"   PRE  {pre.datetime:%Y-%m-%d}  cloud {_cloud(pre):.1f}%  tile {tile_id(pre)}  {pre.id}")
        print(f"   POST {post.datetime:%Y-%m-%d}  cloud {_cloud(post):.1f}%  tile {tile_id(post)}  {post.id}")
    else:
        print("   no same-tile pair found in range")
