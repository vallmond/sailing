#!/usr/bin/env python3
"""
Generate two self-contained Leaflet maps for the 48h Gdansk <-> Leba race:

  * outbound (Gdansk -> Leba)  : Aries + Notre Dame
  * return   (Leba -> Gdansk)  : Aries + Notre Dame

The GPX files are Garmin *Courses* (no per-point timestamps), so this is a
static route overlay -- no animated replay -- with both boats on one map.
"""

import re
import math
import json
import os

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")

# boat name -> (colour, {leg: gpx file})
LEGS = {
    "outbound": {
        "file": "leba-48h-outbound.html",
        "title": "48h Gdańsk → Łeba — droga tam",
        "subtitle": "Trasa obu jachtów w drodze z Gdańska do Łeby. Tory kursu (Garmin Course, bez znaczników czasu) — nałożone na jedną mapę.",
        "start_label": "GDAŃSK",
        "end_label": "ŁEBA",
        "boats": [
            {"name": "Aries", "color": "#e6550d", "file": "COURSE_486976431.gpx"},
            {"name": "Notre Dame", "color": "#1d72f3", "file": "COURSE_486976930.gpx"},
        ],
    },
    "return": {
        "file": "leba-48h-return.html",
        "title": "48h Łeba → Gdańsk — droga powrotna",
        "subtitle": "Trasa obu jachtów w drodze powrotnej z Łeby do Gdańska. Tory kursu (Garmin Course, bez znaczników czasu) — nałożone na jedną mapę.",
        "start_label": "ŁEBA",
        "end_label": "GDAŃSK",
        "boats": [
            {"name": "Aries", "color": "#e6550d", "file": "COURSE_486972380.gpx"},
            {"name": "Notre Dame", "color": "#1d72f3", "file": "COURSE_486977137.gpx"},
        ],
    },
}


def parse_gpx(path):
    txt = open(path, encoding="utf-8").read()
    pts = re.findall(r'<trkpt lat="([-\d.]+)" lon="([-\d.]+)"', txt)
    return [(float(a), float(b)) for a, b in pts]


def haversine(a, b):
    R = 6371000.0
    la1, lo1 = math.radians(a[0]), math.radians(a[1])
    la2, lo2 = math.radians(b[0]), math.radians(b[1])
    dla, dlo = la2 - la1, lo2 - lo1
    h = math.sin(dla / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlo / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def total_distance(pts):
    return sum(haversine(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def decimate(pts, min_gap=6.0):
    """Keep points at least `min_gap` metres apart (preserves tack shape, cuts size)."""
    if not pts:
        return pts
    kept = [pts[0]]
    for p in pts[1:-1]:
        if haversine(kept[-1], p) >= min_gap:
            kept.append(p)
    kept.append(pts[-1])
    return kept


def round_pts(pts, nd=5):
    return [[round(la, nd), round(lo, nd)] for la, lo in pts]


TEMPLATE = r"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<link rel="icon" type="image/svg+xml" href="assets/north-star.svg">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  :root { color-scheme: light; --panel:#ffffff; --text:#1f2933; --muted:#52606d; --border:#d9dde7; }
  * { box-sizing: border-box; }
  html, body { margin:0; height:100%; }
  body { font-family:"Inter","Segoe UI",system-ui,-apple-system,sans-serif; color:var(--text);
         display:flex; flex-direction:column; }
  header { padding:0.85rem clamp(0.9rem,3vw,1.6rem); background:linear-gradient(135deg,#0f172a,#1e293b);
           color:#fff; box-shadow:0 6px 18px rgba(15,23,42,0.25); z-index:1000; }
  header h1 { margin:0 0 0.2rem; font-size:clamp(1.05rem,2.1vw,1.5rem); font-weight:600; }
  header p { margin:0; color:rgba(255,255,255,0.75); max-width:80ch; line-height:1.45; font-size:0.86rem; }
  .nav { margin-top:0.5rem; display:flex; gap:0.5rem; flex-wrap:wrap; }
  .nav a { font-size:0.8rem; text-decoration:none; color:#e5edff; border:1px solid rgba(148,163,184,0.45);
           padding:0.2rem 0.7rem; border-radius:999px; }
  .nav a.active { background:#e5edff; color:#0f172a; font-weight:600; border-color:#e5edff; }
  #map { flex:1; width:100%; }
  .legend { background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:0.7rem 0.85rem;
            box-shadow:0 10px 24px rgba(15,23,42,0.18); font-size:0.85rem; min-width:190px; }
  .legend h2 { margin:0 0 0.55rem; font-size:0.78rem; letter-spacing:0.05em; text-transform:uppercase; color:var(--muted); }
  .legend .row { display:flex; align-items:center; gap:0.55rem; padding:0.2rem 0; cursor:pointer; user-select:none; }
  .legend .row input { margin:0; }
  .legend .swatch { width:26px; height:5px; border-radius:3px; flex:none; }
  .legend .name { font-weight:600; }
  .legend .dist { margin-left:auto; color:var(--muted); font-variant-numeric:tabular-nums; }
  .legend .hint { margin-top:0.55rem; font-size:0.72rem; color:var(--muted); line-height:1.35; }
  .city-label { font-weight:800; font-size:0.72rem; letter-spacing:0.12em; color:#0f172a;
                text-shadow:0 0 3px #fff,0 0 6px #fff,0 1px 2px #fff; white-space:nowrap; }
  .leaflet-container { background:#aad3df; }
</style>
</head>
<body>
<header>
  <h1>__TITLE__</h1>
  <p>__SUBTITLE__</p>
  <div class="nav">
    <a href="leba-48h-outbound.html" __ACTIVE_OUT__>➜ Droga tam (Gdańsk → Łeba)</a>
    <a href="leba-48h-return.html" __ACTIVE_RET__>⬅ Droga powrotna (Łeba → Gdańsk)</a>
  </div>
</header>
<div id="map"></div>
<script>
const BOATS = __BOATS__;
const START_LABEL = "__START_LABEL__";
const END_LABEL = "__END_LABEL__";

const map = L.map('map', { zoomControl:true, preferCanvas:true });

const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom:19, attribution:'&copy; OpenStreetMap contributors'
}).addTo(map);
const seamark = L.tileLayer('https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png', {
  maxZoom:18, opacity:0.9, attribution:'&copy; OpenSeaMap'
}).addTo(map);
L.control.layers({ 'OpenStreetMap': osm }, { 'Znaki nawigacyjne (OpenSeaMap)': seamark },
                 { collapsed:true }).addTo(map);

const allLatLngs = [];
const layers = {};

function startIcon(color){ return L.divIcon({className:'', iconSize:[16,16], iconAnchor:[8,8],
  html:`<div style="width:14px;height:14px;border-radius:50%;background:${color};border:2.5px solid #fff;box-shadow:0 0 0 1.5px ${color}"></div>`}); }
function endIcon(color){ return L.divIcon({className:'', iconSize:[18,18], iconAnchor:[9,9],
  html:`<div style="width:14px;height:14px;background:${color};border:2.5px solid #fff;box-shadow:0 0 0 1.5px ${color};transform:rotate(45deg)"></div>`}); }

BOATS.forEach(b => {
  const grp = L.layerGroup();
  const line = L.polyline(b.coords, { color:b.color, weight:3, opacity:0.9, lineJoin:'round', lineCap:'round' });
  grp.addLayer(line);
  const s = b.coords[0], e = b.coords[b.coords.length-1];
  L.marker(s, { icon:startIcon(b.color) }).bindTooltip(`${b.name} — start`, {direction:'top'}).addTo(grp);
  L.marker(e, { icon:endIcon(b.color) }).bindTooltip(`${b.name} — meta`, {direction:'top'}).addTo(grp);
  grp.addTo(map);
  layers[b.name] = grp;
  b.coords.forEach(c => allLatLngs.push(c));
});

// city labels at the mean of boat start / end points
function mean(getter){ const a = BOATS.map(getter); return [a.reduce((s,p)=>s+p[0],0)/a.length, a.reduce((s,p)=>s+p[1],0)/a.length]; }
function cityLabel(pos, text){ L.marker(pos, { icon:L.divIcon({className:'', iconSize:[0,0],
  html:`<div class="city-label">${text}</div>`}), interactive:false }).addTo(map); }
cityLabel(mean(b=>b.coords[0]), START_LABEL);
cityLabel(mean(b=>b.coords[b.coords.length-1]), END_LABEL);

map.fitBounds(L.latLngBounds(allLatLngs).pad(0.08));

// legend + toggles
const legend = L.control({ position:'topright' });
legend.onAdd = function(){
  const d = L.DomUtil.create('div','legend');
  L.DomEvent.disableClickPropagation(d);
  let rows = BOATS.map(b =>
    `<label class="row"><input type="checkbox" data-boat="${b.name}" checked>
       <span class="swatch" style="background:${b.color}"></span>
       <span class="name">${b.name}</span>
       <span class="dist">${b.distNm.toFixed(1)} Mm</span></label>`).join('');
  d.innerHTML = `<h2>Jachty</h2>${rows}
    <div class="hint">● start &nbsp; ◆ meta<br>Bez replay: tory kursu nie mają czasu.</div>`;
  return d;
};
legend.addTo(map);

document.querySelectorAll('.legend input[data-boat]').forEach(cb => {
  cb.addEventListener('change', e => {
    const g = layers[e.target.dataset.boat];
    if (e.target.checked) g.addTo(map); else map.removeLayer(g);
  });
});
</script>
</body>
</html>
"""


def build():
    for leg_key, leg in LEGS.items():
        boats_json = []
        for b in leg["boats"]:
            pts = parse_gpx(os.path.join(DATA, b["file"]))
            dist_nm = total_distance(pts) / 1852.0
            coords = round_pts(decimate(pts))
            boats_json.append({
                "name": b["name"], "color": b["color"],
                "distNm": round(dist_nm, 1), "coords": coords,
            })
            print(f"  {b['name']:11s} {b['file']}: {len(pts)} -> {len(coords)} pts, {dist_nm:.1f} NM")

        html = (TEMPLATE
                .replace("__TITLE__", leg["title"])
                .replace("__SUBTITLE__", leg["subtitle"])
                .replace("__START_LABEL__", leg["start_label"])
                .replace("__END_LABEL__", leg["end_label"])
                .replace("__ACTIVE_OUT__", 'class="active"' if leg_key == "outbound" else "")
                .replace("__ACTIVE_RET__", 'class="active"' if leg_key == "return" else "")
                .replace("__BOATS__", json.dumps(boats_json, ensure_ascii=False)))

        out_path = os.path.join(OUT, leg["file"])
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        size_kb = os.path.getsize(out_path) / 1024
        print(f"[{leg_key}] wrote {out_path}  ({size_kb:.0f} KB)\n")


if __name__ == "__main__":
    print("Generating 48h Łeba race maps...\n")
    build()
    print("Done.")
