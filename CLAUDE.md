# peavine-watch

Post-fire monitoring for the **Hawk Fire** and geocache **GC1CG0A**
"Basque Sheepherder: The High Camp", Peavine Mountain, Washoe County NV.

## The site
| | |
|---|---|
| Coords | 39.58475 N, -119.94228 W |
| Elevation | 2,309 m / 7,574 ft |
| Slope / aspect | 13.3 deg, SE-facing (139 deg) |
| Hydrology | 214 cells flow accumulation, **31 m from a mapped channel** |
| Cache placed | 2008-05-21, ammo can, 63 finds |
| Draw | Basque sheepherder aspen arborglyphs |

## The fire
Human-caused, ignited **2026-08-22 18:23 UTC (11:23 PDT)**, ~5 mi N of Reno.
VIIRS put fire **315 m from the site 92 minutes after ignition**, 79 m by 14:16 PDT,
with brightness temperature saturating the sensor (367 K). 15,040 acres, 0% contained
at time of writing.

## Commands
```
pixi run scenes     # what Sentinel-2 imagery exists over the site
pixi run severity   # dNBR burn severity - the main product
pixi run snow       # NDSI snow tracking + the assessment deadline
pixi run baer       # poll for an official BAER product
```

## Data
Sentinel-2 L2A from **AWS Earth Search** (`earth-search.aws.element84.com`).
No key, no auth, no registration. COGs read windowed to a ~7 km box, so nothing
downloads a full scene.

Bands: `green`=B03, `red`=B04, `nir`=B08 (10 m), `swir16`=B11, `swir22`=B12 (20 m).
The 20 m bands get `reproject_match`ed to the 10 m grid before ratioing.

## The two indices
- **NBR** = (nir - swir22) / (nir + swir22) -> **dNBR** = NBR_pre - NBR_post
- **NDSI** = (green - swir16) / (green + swir16), snow above ~0.4

## Limits worth remembering
- **dNBR is not soil burn severity.** It measures surface and vegetation change
  from above. Soil burn severity drives debris-flow risk and needs field work.
- **Snow closes the window.** Above ~2,300 m in the Carson Range, persistent snow
  from roughly November to May makes optical severity assessment impossible.
- **BAER may never exist here.** Peavine is BLM / City of Reno / private. BAER is a
  federal response; a largely non-federal burn may get no official severity map.

## Notes for Claude
- Best pre-fire scene is **2026-08-18** (0.9% cloud, 4 days before ignition).
- First post-fire scene is 2026-08-23, but it was 22.7% cloud and the fire was
  still actively burning - smoke and active flame corrupt NBR. Prefer a later
  clear scene once the fire is out.
- Outputs land in `out/` as GeoTIFFs; load `dnbr.tif` in the QGIS
  "Peavine / Hawk Fire - GC1CG0A case study" group alongside the VIIRS detections
  and the GRASS drainage network.
