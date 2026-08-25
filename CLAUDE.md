# CLAUDE.md — peavine-watch

Read this first if you're picking this project back up.

## What this is

Post-fire satellite monitoring for **GC1CG0A**, "Basque Sheepherder: The High
Camp" — a geocache placed in 2008 at an old Basque sheep camp in a spring-fed
aspen grove on Peavine Mountain, Washoe County NV. The draw was the aspen
arborglyphs the sheepherders carved into the trunks. The **Hawk Fire** burned
through the site on 2026-08-22.

Owner is a GIS analyst (Brooks Groves, Zillow) who does wildfire/hydrology
work professionally and treated his own cache site as a case study, using the
same VIIRS/WFIGS/GRASS toolchain from his day job. This repo is the follow-on
satellite piece: did the grove and the carvings survive, using nothing but
free public data.

## The site, for reference

| | |
|---|---|
| Coordinates | 39.58475 N, −119.94228 W |
| Elevation | 2,309 m / 7,574 ft |
| Slope / aspect | 13.3°, SE-facing |
| Hydrology | 214 cells flow accumulation, **31 m from a mapped channel** — a real drainage, which is why the spring/grove/sheep camp were all there |
| Fire arrival | VIIRS detected fire 315 m away 92 min after ignition, 79 m by 14:16 PDT, brightness temp saturated the sensor (367 K) |

## Confirmed result (as of 2026-08-25, provisional — see below)

```
NBR pre-fire   +0.481   (S2C_10SGJ_20260818, 0.9% cloud, 4 days before ignition)
NBR post-fire  -0.055   (S2A_10SGJ_20260823, 15.1% cloud, fire still burning)
dNBR           +0.536   -> MODERATE-HIGH SEVERITY
RdNBR          +772.8   -> in the range most published studies call HIGH severity
```

**This is provisional.** The post-fire scene predates full containment (fire
was still 0% contained). Active flame and smoke both distort NBR upward. The
task list below starts with getting a clean re-run once there's a clear
post-Hawk scene.

## Bugs fixed this session (read before trusting old output)

1. **Cross-tile pre/post pairing.** Peavine sits near the UTM 10/11 boundary;
   an early run diffed a zone-11 pre scene against a zone-10 post scene.
   `find_pair()` in `peavine.py` now only pairs scenes sharing an MGRS tile.
2. **Smoke misread as snow.** `snow_watch.py` reported NDSI +0.31/+0.35 (looks
   like snow) on smoky/cloudy scenes that should have read like the two clean
   scenes at −0.37 to −0.40. Fixed by masking SCL cloud/shadow/cirrus classes
   before computing any index, and reporting `valid_frac` — rows below 50%
   valid print `UNRELIABLE` instead of a number. **Verified working**: the
   three contaminated scenes now correctly show 0% valid / UNRELIABLE, the two
   clean scenes show 100% valid and agree with each other.
3. **RdNBR formula bug — the one that mattered most.** First implementation
   was off by a factor of √1000 (≈31.6×): reported +24.4 when the correct
   value, verified by hand against Miller & Thode (2007), is **+772.8**. Caught
   by sanity-checking the output against published RdNBR ranges rather than
   trusting the refactor. This is the difference between "mild correction,
   no severity class asserted" and a number sitting in the range most studies
   label high severity — do not reintroduce this without re-deriving the
   formula by hand first.
4. `snow_watch.py` crashed on exit if `eo:cloud_cover` was ever `None` in a
   scene's STAC properties (formatting `None` as `:.1f}`). Guarded.
5. `ring_stats()` took a `deg` half-width but was documented and labeled as a
   diameter in one caller and a radius in another — the printed "~300 m" box
   size didn't always match what was actually sampled. Now takes `radius_m`
   directly so the label is always correct.

## Environment

```bash
pixi install     # reproduces the exact env from pixi.lock — no solving needed
pixi run scenes     # what Sentinel-2 imagery exists over the site
pixi run severity   # dNBR + RdNBR — the main product
pixi run snow       # NDSI snow tracking + the assessment deadline
pixi run baer       # poll for an official BAER product (likely none — see README)
```

All Sentinel-2 access is via **AWS Earth Search** (`earth-search.aws.element84.com`),
no key, no auth. If that endpoint ever changes shape, `peavine.py::search()` and
`::band()` are the only two functions that touch it.

## Next steps, roughly in order

1. **Re-run `pixi run severity` once Hawk is fully out and a clear post-fire
   scene exists.** Sentinel-2 revisits every ~5 days. The provisional number
   above needs replacing with a clean one before it goes anywhere public-facing.
2. **Watch `pixi run snow` weekly.** First reliable snow detection closes the
   optical assessment window until spring melt-out (roughly Nov–May at this
   elevation). Once that happens, severity work is done for the season.
3. **Run `pixi run baer` occasionally** — low expectation of a hit. Peavine is
   BLM/City of Reno/private, not a clean federal parcel, so BAER (a *federal*
   post-fire response) may never publish a product for this specific fire. If
   it never does, the Sentinel-2 dNBR/RdNBR here becomes the only severity
   product that will exist for this hillside.
4. **Spring 2027: watch the channel.** The cache sits 31 m from a mapped
   drainage with real upslope contribution. Snowmelt on hydrophobic burned
   soil, not the monsoon, is the debris-flow risk here — see README.
5. **If/when the owner physically visits the site**, that's ground truth this
   repo doesn't have. Worth a note in the repo either way — can the ammo can
   be found, did it move, what does the grove actually look like at ground
   level. Would also be worth reaching out to UNR's Center for Basque Studies,
   who catalog Peavine's arborglyphs — they may want to know, and may already
   have documentation of what was there.

## Style notes for future me

- This repo is written to be read, not just run — the docstrings carry the
  reasoning (why dNBR, why RdNBR, why same-tile matters, why SCL masking
  matters), not just the mechanics. Keep that up.
- State limits plainly rather than letting a number imply more certainty than
  it has. "Provisional," "UNRELIABLE," "no hard class applied" are doing real
  work in this codebase — don't remove them to make output look cleaner.
- When editing `peavine.py`'s math, hand-verify against a real published
  formula before trusting a refactor. The RdNBR bug is why.
