# peavine-watch

Post-fire satellite monitoring for the **Hawk Fire** and geocache **GC1CG0A**
— *"Basque Sheepherder: The High Camp"* — on Peavine Mountain, Washoe County, Nevada.

A geocache placed in 2008 at an old Basque sheep camp, in a spring-fed aspen grove
whose draw was the sheepherders' arborglyphs carved into the trunks. On 22 August
2026 the Hawk Fire burned through it. This repo works out what happened, using only
free and open data.

## The site

| | |
|---|---|
| Coordinates | 39.58475 N, −119.94228 W |
| Elevation | 2,309 m / 7,574 ft |
| Slope / aspect | 13.3°, SE-facing |
| Hydrology | 214 cells flow accumulation, **31 m from a mapped channel** |
| Cache | Placed 2008-05-21, ammo can, 63 finds, 5 favourites |

The terrain analysis explains the site: it sits in a genuine drainage swale. A
parking waypoint 500 m away has a flow accumulation of **1**. That spring is why
aspen grew there, and why Basque sheepherders camped there.

## The fire

Human-caused, ignited **2026-08-22 18:23 UTC (11:23 PDT)**, about five miles north
of Reno. VIIRS thermal detections put fire **315 m from the site 92 minutes after
ignition**, and 79 m by 14:16 PDT, with brightness temperature saturating the sensor
at 367 K. The fire reached 15,040 acres at 0% containment within 48 hours.

## What this does

```bash
pixi run scenes     # what Sentinel-2 imagery exists over the site
pixi run severity   # dNBR burn severity — the main product
pixi run snow       # NDSI snow tracking and the assessment deadline
pixi run baer       # poll for an official BAER product
```

### dNBR burn severity

`dNBR = NBR_prefire − NBR_postfire`, where `NBR = (NIR − SWIR2) / (NIR + SWIR2)`.

Healthy vegetation is bright in NIR and dark in SWIR2. Fire strips chlorophyll and
canopy moisture and exposes char, which inverts that. Taking the *difference*
isolates what the fire did rather than what the site looked like beforehand — which
matters here, because an aspen grove and a sagebrush slope have very different
baseline NBR. Only dNBR shows how much each actually changed.

### Snow, which cuts both ways

At 2,309 m in the Carson Range, persistent snow runs roughly November to May.

1. **It closes the assessment window.** Optical burn severity needs bare ground.
   There are a few weeks each autumn to get a clean read, then nothing until melt-out.
2. **It is also the hazard.** Post-fire debris flow is usually framed as a monsoon
   problem. At this elevation the driver is snowmelt — hydrophobic soil, no canopy,
   no roots, and weeks of sustained meltwater rather than a 30-minute cloudburst.
   The cache sits 31 m from the channel that will carry it.

## Data

**Sentinel-2 L2A** via [AWS Earth Search](https://earth-search.aws.element84.com/v1).
No key, no auth, no registration. Cloud-optimised GeoTIFFs read windowed to a ~7 km
box, so no full scenes are downloaded.

Bands: `green` B03, `red` B04, `nir` B08 (10 m), `swir16` B11, `swir22` B12 (20 m).
The 20 m bands are `reproject_match`ed to the 10 m grid before ratioing.

Fire perimeters and VIIRS thermal detections come from NIFC WFIGS and NASA VIIRS via
Esri Living Atlas. Terrain from USGS 3DEP; hydrology derived with GRASS
`r.watershed` / `r.stream.extract`.

## Limits, stated plainly

- **dNBR is not soil burn severity.** It measures surface and vegetation change from
  above. Soil burn severity drives debris-flow risk and requires field assessment.
  A grove can read moderate on dNBR while the soil beneath is severely burned.
- **The first post-fire scene is compromised.** 2026-08-23 was 22.7% cloud with the
  fire still actively burning; smoke and active flame corrupt NBR. Wait for a clear
  scene after the fire is out. Sentinel-2 revisits every ~5 days.
- **BAER may never exist for this fire.** BAER is a *federal* post-fire response, and
  Peavine is a patchwork of BLM, City of Reno, and private land. If the burn is
  largely non-federal there may be no official severity map — in which case the
  Sentinel-2 dNBR here is the best product that will exist.

## Why bother

The arborglyphs were the point of the cache. Carvings live in the bark and cambium of
living aspen, and aspen bark is thin and photosynthetic — the same property that makes
it hold a carving for a century makes it almost defenceless against fire. The grove
will regenerate by root suckering; the carvings will not come back with it.

Whether they survived is worth knowing, and nobody else is going to check.

## Licence

MIT for the code. Underlying data is public domain (NASA, USGS, ESA/Copernicus, NIFC).
