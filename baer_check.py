"""
baer_check.py - poll for an official BAER / post-fire severity product for Hawk.

HONEST FRAMING
There is no authoritative national BAER ArcGIS service to query. BAER Imagery
Support Program products are published as downloads per-incident, and MTBS lags
by a year or more. So this polls the places a Hawk product would actually appear
and tells you whether one exists yet. It will report "nothing yet" for weeks,
and possibly forever.

WHY POSSIBLY FOREVER
BAER is a FEDERAL post-fire response. It is triggered when a fire burns federal
land and threatens federal values at risk. Peavine Mountain is a patchwork of
BLM, City of Reno, and private parcels. If the burn is largely non-federal there
may never be a BAER soil burn severity map for it - in which case the Sentinel-2
dNBR from burn_severity.py is the best severity product that will exist.

    pixi run baer
"""
import json, urllib.request, urllib.parse

UA = {"User-Agent": "(peavine-watch, brooksg@zillowgroup.com)"}
FIRE = "Hawk"
STATE = "NV"
YEAR = 2026


def _get(url, timeout=30, as_json=True):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout)
        raw = r.read()
        return json.loads(raw) if as_json else raw.decode("utf-8", "ignore")
    except Exception as e:
        return {"__err__": str(e)[:90]}


def check_arcgis_online():
    """Someone often publishes a one-off severity layer per incident."""
    hits = []
    for q in [f'{FIRE} fire soil burn severity',
              f'{FIRE} fire {YEAR} burn severity',
              f'{FIRE} fire BAER']:
        p = {"q": q, "f": "json", "num": 10, "sortField": "modified", "sortOrder": "desc"}
        d = _get("https://www.arcgis.com/sharing/rest/search?" + urllib.parse.urlencode(p))
        if "__err__" in d:
            continue
        for r in d.get("results", []):
            title = (r.get("title") or "")
            if FIRE.lower() not in title.lower():
                continue
            hits.append((title, r.get("owner"), r.get("url") or r.get("id")))
    return hits


def check_wfigs_perimeter():
    """Confirm the incident is still in WFIGS and get its current state."""
    B = ("https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/"
         "WFIGS_Interagency_Perimeters_YearToDate/FeatureServer/0")
    w = urllib.parse.quote(f"attr_IncidentName = '{FIRE}' AND attr_POOState = 'US-{STATE}'")
    d = _get(f"{B}/query?where={w}&outFields=attr_IncidentName,poly_GISAcres,"
             "attr_PercentContained,attr_FireOutDateTime,attr_POOCounty"
             "&returnGeometry=false&f=json")
    return d.get("features", []) if "__err__" not in d else []


def main():
    print("=== Hawk Fire status (WFIGS) ===")
    for f in check_wfigs_perimeter():
        a = f["attributes"]
        out = a.get("attr_FireOutDateTime")
        print(f"  {a.get('poly_GISAcres',0):,.0f} acres | "
              f"{a.get('attr_PercentContained')}% contained | "
              f"{a.get('attr_POOCounty')} | out: {'yes' if out else 'no'}")

    print("\n=== searching for a published severity product ===")
    hits = check_arcgis_online()
    if hits:
        for t, o, u in hits:
            print(f"  FOUND  {t[:58]:<60}{o}")
            print(f"         {u}")
    else:
        print("  nothing published yet")
        print("\n  Check manually, in likely order of appearance:")
        print("    InciWeb incident page        https://inciweb.wildfire.gov")
        print("    BAER Imagery Support         https://burnseverity.cr.usgs.gov/baer/")
        print("    MTBS (lags ~1 yr)            https://mtbs.gov")
        print("    NV Div. of Forestry / BLM Carson City District")
        print("\n  Meanwhile: pixi run severity  gives you a Sentinel-2 dNBR now.")


if __name__ == "__main__":
    main()
