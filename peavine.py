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
  NBR  = (nir - swir22) / (nir + swir22)      burn severity
  NDSI = (green - swir16) / (green + swir16)  snow index
"""
import os, json
import numpy as np
import rioxarray  # noqa: F401  (registers .rio accessor)
import xarray as xr
from pystac_client import Client

STAC = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-l2a"

CACHE_LAT, CACHE_LON = 39.58475, -119.94228
PARK_LAT, PARK_LON = 39.583667, -119.936350
IGNITION = "2026-08-22T18:23:00Z"
BOX_DEG = 0.035          # ~3.5 km half-width around the site
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def aoi():
    return (CACHE_LON - BOX_DEG, CACHE_LAT - BOX_DEG,
            CACHE_LON + BOX_DEG, CACHE_LAT + BOX_DEG)


def search(start, end, max_cloud=35, limit=60):
    """Scenes over the site in a date range, least cloudy first."""
    cat = Client.open(STAC)
    res = cat.search(collections=[COLLECTION], bbox=aoi(),
                     datetime=f"{start}/{end}",
                     query={"eo:cloud_cover": {"lt": max_cloud}}, limit=limit)
    items = list(res.items())
    items.sort(key=lambda i: i.properties.get("eo:cloud_cover", 100))
    return items


def band(item, key):
    """Read one band clipped to the AOI, as a float array in EPSG:4326."""
    href = item.assets[key].href
    da = rioxarray.open_rasterio(href, masked=True, chunks=None)
    da = da.rio.reproject("EPSG:4326")
    x0, y0, x1, y1 = aoi()
    da = da.rio.clip_box(minx=x0, miny=y0, maxx=x1, maxy=y1)
    return da.squeeze().astype("float32")


def ratio(a, b):
    """Normalised difference, matching grids if resolutions differ."""
    if a.shape != b.shape:
        b = b.rio.reproject_match(a)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = (a - b) / (a + b)
    return out


def nbr(item):
    return ratio(band(item, "nir"), band(item, "swir22"))


def ndsi(item):
    return ratio(band(item, "green"), band(item, "swir16"))


def at_site(da, lat=CACHE_LAT, lon=CACHE_LON):
    """Value at the cache pixel."""
    try:
        return float(da.sel(x=lon, y=lat, method="nearest").values)
    except Exception:
        return float("nan")


def ring_stats(da, lat=CACHE_LAT, lon=CACHE_LON, deg=0.0027):
    """Stats in a ~300 m box around the site - one VIIRS pixel's worth."""
    sub = da.sel(x=slice(lon - deg, lon + deg), y=slice(lat + deg, lat - deg))
    v = sub.values[np.isfinite(sub.values)]
    if v.size == 0:
        return {}
    return {"n": int(v.size), "mean": float(v.mean()), "min": float(v.min()),
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
            print(f"   {i.datetime:%Y-%m-%d}  cloud {i.properties.get('eo:cloud_cover',0):5.1f}%  {i.id}")
        print()
