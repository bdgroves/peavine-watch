# 🔥 peavine-watch

*What did the fire actually do to a mountain, a spring, and a hundred years of carved names — and can you find out from a couch 800 miles away, for free?*

On **22 August 2026 at 11:23 AM**, someone started a fire five miles north of Reno, Nevada. Ninety-two minutes later, a satellite in low Earth orbit saw it burning **315 meters from a spot marked by a small yellow star on the maps below** — the location of geocache **GC1CG0A**, hidden in 2008 at an old Basque sheep camp, in a meadow fed by a mountain spring, under aspen trees carved with a century of names.

This repo is what happened next: using nothing but public satellites and open compute, from a laptop 800 miles away in Washington State.

<p align="center">
  <img src="out/burn_severity.png" width="100%" alt="NBR before, NBR after, dNBR, RdNBR — four panels showing the burn at the cache site">
</p>

---

## The site

A sheep camp, a spring, and a grove — and it turns out the geography explains all three at once.

| | |
|---|---|
| Coordinates | `39.58475 N, -119.94228 W` |
| Elevation | 2,309 m / 7,574 ft |
| Aspect | SE-facing, 13.3° slope |
| **Flow accumulation** | **214 cells** — a real drainage |
| **Distance to nearest mapped channel** | **31 m** |
| Cache placed | 2008-05-21 · ammo can · 63 finds · 5 favourites |

A GRASS `r.watershed` run over USGS 3DEP elevation data shows the cache sitting almost on top of a drainage line. A parking waypoint 500 m away, by contrast, has a flow accumulation of **1** — flat, dry ridge. That's not a coincidence. **The spring is why the grove exists, and the grove is why the sheepherders camped there.** Water finds this exact spot on the mountain, and it has for a very long time.

## The fire, minute by minute

VIIRS is a thermal sensor on two polar-orbiting satellites, passing over any given point roughly twice a day. It doesn't usually let you watch a fire arrive at a specific coordinate in real time — but Hawk moved fast enough, and the passes lined up well enough, that it basically does here.

| Time (PDT) | Distance from cache | What VIIRS saw |
|---|---:|---|
| 11:23 AM | — | **Ignition** (WFIGS discovery time) |
| 12:55 PM | 315 m | First detection — 92 minutes after ignition |
| 1:40 PM | 222 m | High confidence, 216 MW |
| **2:16 PM** | **79 m** | High confidence, 142.7 MW |
| 2:36 PM | 282 m | 230 MW |

Fire radiative power in that range is an active flaming front, not a smoulder. Brightness temperature on most of these detections **saturated the sensor's measurement ceiling (367 K)** — VIIRS simply couldn't register anything hotter. By the next morning the fire had run out to 6.6 km and covered over 15,000 acres.

## What burned, and how we know

This project computes two standard remote-sensing burn indices from **Sentinel-2**, the European Space Agency's free 10-meter imaging satellite, using a *before* and *after* scene of the exact same ground:

**NBR** (Normalized Burn Ratio) contrasts near-infrared against shortwave-infrared. Healthy leaves are bright in NIR and dark in SWIR — high NBR. Fire strips that away and exposes bare soil and char, which flips it. Taking the *change* — `dNBR = NBR_before − NBR_after` — isolates what the fire did from what was simply *there* to begin with, which matters a lot on this mountain: an aspen grove and the surrounding sagebrush start from very different baselines, and only the delta tells you how much each one actually lost.

**RdNBR** goes one step further and normalizes for that starting baseline (Miller & Thode, 2007) — the direct fix for exactly the grove-vs-sagebrush comparison this project cares about.

```
NBR pre-fire   +0.481   (Aug 18, 4 days before ignition, 0.9% cloud)
NBR post-fire  -0.055   (Aug 23, fire still burning, 15.1% cloud)
dNBR           +0.536   →  Moderate-high severity
RdNBR          +772.8   →  in the range most published studies call high severity
```
*(Provisional — the post-fire scene predates full containment; see [Limits](#limits-stated-plainly).)*

**The aspen grove itself burned hotter than the ground around it** — its 100 m mean dNBR exceeds 90% of the surrounding 3 km. Counterintuitively, that's partly *because* it was healthier: dense, moist canopy has more to lose than sparse, dry sagebrush, which is exactly the effect RdNBR exists to correct for.

## Terrain vs fuel: why *this* grove

The cache sits in a drainage. A parking waypoint 500 m away sits on a dry ridge.
Same fire, same afternoon:

| | flow accumulation | NBR pre-fire | dNBR |
|---|---|---|---|
| **Grove / drainage** | 214 cells | +0.481 | **+0.536** |
| Ridge / parking | 1 cell | +0.128 | +0.126 |

Four times the burn severity, 500 metres apart. Tempting to call that terrain —
fire runs uphill, a drainage concentrates the front — but it can't be read that
way as it stands, because **the two points didn't start equal.** The grove was
dense aspen; the ridge was sparse sagebrush. Denser vegetation burns hotter more
or less everywhere, because it has more to lose. Part of that 4× is fuel load.

So hold fuel constant. Compare the grove only against ground that was *equally
vegetated* before the fire (NBR_pre 0.40–0.55):

```
grove ring, equally vegetated      n=  129    mean dNBR  +0.731
same density elsewhere in AOI      n= 6,891   mean dNBR  +0.453
                                   terrain-attributable  +0.278
```

The grove still burned harder than 79% of equally-fuelled ground. That residual
can't be fuel load — fuel load is what was controlled for. What's left is terrain
and moisture regime.

Both effects are real and they compound. Across the whole AOI, severity climbs
steadily with pre-fire density (+0.344 on the sparsest ground, +0.657 on the
densest). The grove sat at the intersection: the heaviest fuel on the hillside,
in the feature that concentrated the fire into it.

Which closes an unpleasant loop. Water collects in that drainage. Water grew the
aspens. The aspens were the heaviest fuel on the hill, standing in the feature
that funnelled the fire to them. Every reason the grove existed is a reason it
burned.

*A note on the word "chimney":* the slope is 13.3°, which is moderate. A textbook
chimney is a steep narrow gully with a strong convective draft. This is a broad
SE-facing drainage near a summit — fire running upslope with a drainage
concentrating the front, not a violent chimney effect. Directionally right, but
don't overstate it.

![dNBR across the AOI](docs/img/map_dnbr_aoi.png)

*USGS/FIREMON severity ramp over Esri imagery. The grove ring (150 m, dashed
gold) against the surrounding burn mosaic. Only 20.3% of the AOI reached
moderate-high or above; the grove mean of +0.548 exceeds 92.1% of the
surrounding 3 km.*

![The fire's approach](docs/img/map_dnbr_site.png)

*VIIRS thermal detections walking up the drainage, sized by fire radiative power:
315 m at 12:55 PM, 222 m at 1:40, **79 m at 2:16**, 282 m at 2:36. Brightness
temperature saturated the sensor (367 K) on most of these — VIIRS could not
register anything hotter.*

    pixi run terrain

## Watching what happens next

`pixi run watch` records one row per Sentinel-2 pass into `out/timeseries.json` —
NBR, NDVI and NDSI at the cache pixel and averaged over the grove, plus dNBR and
RdNBR against a **pinned** pre-fire baseline. It's idempotent, so a daily
GitHub Actions job can poll a ~5-day satellite revisit without duplicating
anything, and the baseline never drifts.

Live at **[bdgroves.github.io/peavine-watch](https://bdgroves.github.io/peavine-watch/)**.

### What the recovery curve will and won't tell us

NDVI is the index that moves first when aspen resprouts. But a strong recovery
curve is **not** evidence the carvings survived — it's closer to the opposite.

Aspen suckering is suppressed by auxin flowing down from the living parent stem.
Kill the stem and that suppression lifts, which is exactly why aspen regenerates
so aggressively after fire. Vigorous regrowth is *caused by* the death of the
overstory. The healthier the recovery looks, the more confident you can be that
the carved trunks are dead.

Roughly what to expect at the grove:

| NDVI, summer 2027 | reading |
|---|---|
| climbs to 0.3–0.5 | vigorous suckering, root system alive, carved stems dead |
| stays near 0.1–0.15 | roots died too — rarer, and the worse outcome |

Pre-fire grove NDVI was 0.45; it read 0.09 five days after the fire.

**No satellite index can see bark.** NDVI and NBR measure canopy and soil from
786 km up; the carvings are millimetres deep in cambium. That question needs
someone standing in the grove.


## The two-sided problem with snow

Peavine sits at 7,574 feet in the Carson Range, and that single fact drives almost everything about what happens next.

**It closes the window.** Optical satellites need bare, cloud-free ground. Above roughly 2,300 m here, persistent snow runs November to May. There's a stretch of weeks each autumn to get a clean read — then nothing until spring.

**It's also the actual hazard.** Post-fire debris flows usually get discussed as a monsoon problem — a 30-minute cloudburst on burnt, water-repellent soil. At this elevation the bigger driver is **snowmelt**: no canopy to intercept it, no roots to hold the slope, and *weeks* of sustained meltwater instead of one storm. The cache sits 31 meters from the channel that will carry it, come spring.

```bash
pixi run snow
```
tracks NDSI (the equivalent index, built for snow instead of fire) over time and flags the first date the window closes.

## The carvings, and why they matter more than the can

The cache itself is a steel ammo can — the single best-case container for surviving a fast-moving grass and brush fire. A flame front like this passes in a minute or two, not hours. It's scorched almost certainly, and it's plausibly still there.

**The arborglyphs are a different story.** They live in aspen bark and cambium — living tissue, thin enough to carve, which is exactly why it holds no defense against heat. The grove will very likely come back; aspen regenerates aggressively from root suckers after fire. **The names carved into this generation of trees will not come back with it.**

An ammo can is replaceable. A hundred years of a vanishing culture's handwriting on a mountainside is not. That's the actual thing this repo is trying to find out about.

## Run it yourself

```bash
pixi install         # exact environment from pixi.lock — nothing to solve
pixi run scenes       # what Sentinel-2 imagery exists over the site
pixi run severity      # dNBR + RdNBR — the main product, writes out/*.tif + the figure above
pixi run snow          # NDSI snow tracking + the assessment deadline
pixi run baer          # poll for an official BAER severity product
```

Everything pulls from **AWS Earth Search** — no API key, no login, no cost. The whole point is that this kind of analysis, which used to require a federal agency's imagery contract, is now something anyone can run from a laptop.

## Limits, stated plainly

- **The headline number above is provisional.** The only post-fire scene available so far was taken while Hawk was still actively burning (0% contained) — active flame and smoke both distort NBR upward. Re-run `pixi run severity` once a clear scene exists after containment.
- **dNBR and RdNBR are not soil burn severity.** They measure surface and canopy change from above. Soil burn severity — the number that actually drives debris-flow risk — needs a field team (BAER) on the ground. A site can read high on dNBR with only lightly-burned soil underneath, or the reverse.
- **BAER may never exist for this fire.** BAER is a *federal* emergency response, and Peavine is a patchwork of BLM, City of Reno, and private land. If the burn is mostly non-federal, there may be no official product — in which case what's in this repo becomes the only severity assessment this hillside ever gets.
- **Pre/post scenes must share an MGRS satellite tile.** Peavine sits almost exactly on the UTM zone 10/11 boundary. An early version of this code differenced scenes from different tiles without realizing it — different reprojection paths for the same ground, introducing registration error right at feature boundaries like a grove edge. Fixed; see `CLAUDE.md` for the full account, including a since-corrected RdNBR formula bug worth knowing about if you extend this code.

## Data sources

Sentinel-2 L2A · [AWS Earth Search](https://earth-search.aws.element84.com/v1) — no auth
Fire perimeters & VIIRS detections · NIFC WFIGS, NASA VIIRS via Esri Living Atlas
Elevation · USGS 3DEP · Hydrology · GRASS `r.watershed` / `r.stream.extract`

## Licence

MIT for the code. Underlying data is public domain (NASA, USGS, ESA/Copernicus, NIFC).

---

*Whether the carvings survived is worth knowing, and — as far as I can tell — nobody else was going to check.*
