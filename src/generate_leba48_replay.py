#!/usr/bin/env python3
"""
Generate a time-synced REPLAY of the 48h Gdansk <-> Leba race for Aries + Notre Dame.

The GPX files are Garmin *Courses* (no per-point timestamps). We anchor each leg
with its real start time + elapsed duration (from Garmin activity pages) and
interpolate position along the track *by distance* -> constant-speed-per-leg model.

All times are CEST (UTC+02:00). t is measured in seconds from Friday 00:00.
  Friday   = 2026-07-10
  Saturday = 2026-07-11
  Sunday   = 2026-07-12
"""

import re
import math
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "docs")


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


def hms(h, m, s):
    return h * 3600 + m * 60 + s


# --- timing anchors (CEST) ---------------------------------------------------
#  day 0 = Friday, day 1 = Saturday.  start = seconds from Friday 00:00
RACE_DEF = {
    "boats": [
        {
            "name": "Aries", "color": "#e6550d",
            "out": {"file": "COURSE_486976431.gpx",
                    "start": 1 * 0 + hms(19, 48, 0), "dur": hms(25, 43, 33)},   # Fri 19:48
            "ret": {"file": "COURSE_486972380.gpx",
                    "start": 86400 + hms(22, 43, 0), "dur": hms(13, 33, 56)},   # Sat 22:43
        },
        {
            "name": "Notre Dame", "color": "#1d72f3",
            "out": {"file": "COURSE_486976930.gpx",
                    "start": hms(20, 44, 0), "dur": hms(24, 18, 24)},           # Fri 20:44
            "ret": {"file": "COURSE_486977137.gpx",
                    "start": 86400 + hms(22, 49, 0), "dur": hms(16, 14, 0)},    # Sat 22:49
        },
    ],
}


def leg_payload(leg):
    pts = parse_gpx(os.path.join(DATA, leg["file"]))
    coords = round_pts(decimate(pts))
    nm = total_distance(pts) / 1852.0
    return {
        "start": leg["start"],
        "end": leg["start"] + leg["dur"],
        "nm": round(nm, 1),
        "coords": coords,
    }, len(pts), len(coords), nm


def build_race():
    boats = []
    for b in RACE_DEF["boats"]:
        out, no, nco, nmo = leg_payload(b["out"])
        ret, nr, ncr, nmr = leg_payload(b["ret"])
        boats.append({"name": b["name"], "color": b["color"], "out": out, "ret": ret})
        print(f"  {b['name']:11s} out {no:>6}->{nco:<5} ({nmo:5.1f} NM)   ret {nr:>6}->{ncr:<5} ({nmr:5.1f} NM)")
    return {"boats": boats}


TEMPLATE = r"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>48h Gdańsk ⇄ Łeba — replay</title>
<link rel="icon" type="image/svg+xml" href="assets/north-star.svg">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  :root { color-scheme: light; --panel:#ffffff; --text:#1f2933; --muted:#52606d; --border:#d9dde7; --bg:#0f172a; }
  * { box-sizing: border-box; }
  html, body { margin:0; height:100%; }
  body { font-family:"Inter","Segoe UI",system-ui,-apple-system,sans-serif; color:var(--text);
         display:flex; flex-direction:column; height:100vh; overflow:hidden; }
  header { padding:0.6rem clamp(0.8rem,3vw,1.4rem); background:linear-gradient(135deg,#0f172a,#1e293b);
           color:#fff; box-shadow:0 4px 14px rgba(15,23,42,0.25); z-index:1200; }
  header h1 { margin:0 0 0.15rem; font-size:clamp(1rem,2vw,1.35rem); font-weight:600; }
  header p { margin:0; color:rgba(255,255,255,0.7); font-size:0.78rem; line-height:1.35; max-width:95ch; }
  .nav { margin-top:0.4rem; display:flex; gap:0.4rem; flex-wrap:wrap; }
  .nav a { font-size:0.75rem; text-decoration:none; color:#e5edff; border:1px solid rgba(148,163,184,0.45);
           padding:0.15rem 0.6rem; border-radius:999px; }
  .nav a.active { background:#e5edff; color:#0f172a; font-weight:600; border-color:#e5edff; }
  #map { flex:1; width:100%; min-height:0; }
  .panel { background:var(--panel); border-top:1px solid var(--border); box-shadow:0 -6px 18px rgba(15,23,42,0.10);
           padding:0.55rem clamp(0.7rem,3vw,1.3rem) 0.7rem; z-index:1100; }
  .transport { display:flex; align-items:center; gap:0.7rem; flex-wrap:wrap; }
  .play-btn { width:44px; height:44px; border:none; border-radius:50%; background:var(--bg); color:#fff;
              font-size:1.15rem; cursor:pointer; flex:none; display:flex; align-items:center; justify-content:center;
              box-shadow:0 4px 12px rgba(15,23,42,0.35); }
  .play-btn:active { transform:translateY(1px); }
  .clock { font-variant-numeric:tabular-nums; }
  .clock .day { font-size:0.72rem; letter-spacing:0.08em; text-transform:uppercase; color:var(--muted); }
  .clock .time { font-size:1.35rem; font-weight:700; line-height:1.05; }
  #scrub { flex:1; min-width:180px; accent-color:var(--bg); }
  .spd { display:flex; align-items:center; gap:0.35rem; font-size:0.8rem; color:var(--muted); }
  .spd select { font:inherit; padding:0.2rem 0.35rem; border-radius:7px; border:1px solid var(--border); }
  .btn-sec { font:inherit; font-size:0.8rem; padding:0.35rem 0.7rem; border-radius:8px; border:1px solid var(--border);
             background:#f4f6fb; cursor:pointer; }
  .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(215px,1fr)); gap:0.55rem; margin-top:0.6rem; }
  .card { border:1px solid var(--border); border-left-width:4px; border-radius:11px; padding:0.5rem 0.7rem; }
  .card .top { display:flex; align-items:baseline; justify-content:space-between; gap:0.5rem; }
  .card .nm { font-weight:700; font-size:0.95rem; }
  .card .status { font-size:0.78rem; color:var(--muted); }
  .card .stats { margin-top:0.35rem; display:flex; gap:0.9rem; font-size:0.82rem; font-variant-numeric:tabular-nums; }
  .card .stats b { font-weight:700; }
  .card .stats span { color:var(--muted); font-size:0.72rem; display:block; }
  .versus { border-color:#cbd5e1; border-left-color:#64748b; display:flex; flex-direction:column; justify-content:center; }
  .versus .lead { font-weight:700; font-size:0.95rem; }
  .versus .sep { font-size:0.82rem; color:var(--muted); font-variant-numeric:tabular-nums; margin-top:0.15rem; }
  .gantt { margin-top:0.6rem; position:relative; user-select:none; }
  .gantt .grow { position:relative; height:20px; margin:3px 0; }
  .gantt .glabel { position:absolute; left:0; top:0; font-size:0.72rem; font-weight:600; width:74px; line-height:20px; }
  .gantt .gtrack { position:absolute; left:78px; right:0; top:0; height:20px; }
  .gantt .bar { position:absolute; top:3px; height:14px; border-radius:4px; opacity:0.9; }
  .gantt .bar.stopbar { top:8px; height:4px; border-radius:2px; background-image:repeating-linear-gradient(90deg,#94a3b8 0 5px,transparent 5px 9px); }
  .gantt .axis { position:absolute; left:78px; right:0; height:100%; top:0; }
  .gantt .tick { position:absolute; top:0; bottom:16px; width:1px; background:rgba(15,23,42,0.10); }
  .gantt .tlab { position:absolute; bottom:0; font-size:0.62rem; color:var(--muted); transform:translateX(-50%); white-space:nowrap; }
  .gantt .cursor { position:absolute; top:0; bottom:16px; left:78px; width:2px; background:#0f172a; z-index:5; pointer-events:none; }
  .gantt .hit { position:absolute; left:78px; right:0; top:0; bottom:16px; cursor:pointer; }
  .city-label { font-weight:800; font-size:0.72rem; letter-spacing:0.12em; color:#0f172a;
                text-shadow:0 0 3px #fff,0 0 6px #fff,0 1px 2px #fff; white-space:nowrap; }
  .boat-mk { position:relative; }
  .boat-mk .dot { width:16px; height:16px; border-radius:50%; border:2.5px solid #fff; box-shadow:0 0 0 1.5px var(--c),0 1px 4px rgba(0,0,0,.4); }
  .boat-mk .arw { position:absolute; left:50%; top:50%; width:0; height:0;
     border-left:5px solid transparent; border-right:5px solid transparent; border-bottom:13px solid var(--c);
     transform-origin:50% 100%; }
  .boat-mk .tag { position:absolute; left:50%; top:18px; transform:translateX(-50%); background:var(--c); color:#fff;
     font-size:0.66rem; font-weight:700; padding:1px 5px; border-radius:5px; white-space:nowrap; box-shadow:0 1px 3px rgba(0,0,0,.35); }
  .leaflet-container { background:#aad3df; }
  .map-legend { background:#fff; border:1px solid var(--border); border-radius:10px; padding:0.45rem 0.6rem; font-size:0.75rem;
     box-shadow:0 6px 16px rgba(15,23,42,0.15); }
  .map-legend .r { display:flex; align-items:center; gap:0.4rem; }
  .map-legend .sw { width:20px; height:4px; border-radius:2px; }
  @media (max-width:640px){ header p{display:none;} .card .status{font-size:0.72rem;} }
</style>
</head>
<body>
<header>
  <h1>48h Gdańsk ⇄ Łeba — replay wyścigu</h1>
  <p>Aries vs Notre Dame, cała pętla: Gdańsk → Łeba → Gdańsk. Pozycje odtworzone z rzeczywistych czasów startu i długości etapów; wewnątrz etapu ruch interpolowany po dystansie (stała prędkość na etapie). Czas: CEST.</p>
  <div class="nav">
    <a href="leba-48h-replay.html" class="active">▶ Replay (oba jachty)</a>
    <a href="leba-48h-outbound.html">➜ Droga tam</a>
    <a href="leba-48h-return.html">⬅ Droga powrotna</a>
  </div>
</header>
<div id="map"></div>
<div class="panel">
  <div class="transport">
    <button id="play" class="play-btn" title="Play / pauza (spacja)">▶</button>
    <div class="clock"><div class="day" id="clk-day">Piątek 10.07</div><div class="time" id="clk-time">19:48</div></div>
    <input id="scrub" type="range" min="0" max="1000" value="0" step="1">
    <div class="spd">Tempo
      <select id="speed">
        <option value="10">10 min/s</option>
        <option value="30">30 min/s</option>
        <option value="60" selected>60 min/s</option>
        <option value="120">120 min/s</option>
        <option value="300">300 min/s</option>
      </select>
    </div>
    <button id="reset" class="btn-sec">⟲ Reset</button>
  </div>
  <div class="cards" id="cards"></div>
  <div class="gantt" id="gantt"></div>
</div>

<script>
const RACE = __RACE__;
const DAY_META = [
  {name:"Piątek", date:"10.07"},
  {name:"Sobota", date:"11.07"},
  {name:"Niedziela", date:"12.07"},
];
const D2R = Math.PI/180;

function hav(a,b){
  const R=6371000, la1=a[0]*D2R, la2=b[0]*D2R, dla=(b[0]-a[0])*D2R, dlo=(b[1]-a[1])*D2R;
  const h=Math.sin(dla/2)**2+Math.cos(la1)*Math.cos(la2)*Math.sin(dlo/2)**2;
  return 2*R*Math.asin(Math.sqrt(h));
}
function bearing(a,b){
  const y=Math.sin((b[1]-a[1])*D2R)*Math.cos(b[0]*D2R);
  const x=Math.cos(a[0]*D2R)*Math.sin(b[0]*D2R)-Math.sin(a[0]*D2R)*Math.cos(b[0]*D2R)*Math.cos((b[1]-a[1])*D2R);
  return (Math.atan2(y,x)/D2R+360)%360;
}
function prep(leg){
  const c=leg.coords, cum=new Float64Array(c.length);
  for(let i=1;i<c.length;i++) cum[i]=cum[i-1]+hav(c[i-1],c[i]);
  leg.cum=cum; leg.total=cum[c.length-1];
}
RACE.boats.forEach(b=>{ prep(b.out); prep(b.ret); });

const T0 = Math.min(...RACE.boats.map(b=>b.out.start));
const T1 = Math.max(...RACE.boats.map(b=>b.ret.end));
const SPAN = T1 - T0;

function locOnLeg(leg,f){
  const c=leg.coords, cum=leg.cum, target=Math.max(0,Math.min(1,f))*leg.total;
  if(target<=0) return {lat:c[0][0],lon:c[0][1],idx:1};
  if(target>=leg.total){ const n=c.length-1; return {lat:c[n][0],lon:c[n][1],idx:n}; }
  let lo=1, hi=c.length-1;
  while(lo<hi){ const mid=(lo+hi)>>1; if(cum[mid]<target) lo=mid+1; else hi=mid; }
  const i=lo, seg=cum[i]-cum[i-1], w=seg?(target-cum[i-1])/seg:0;
  return {lat:c[i-1][0]+(c[i][0]-c[i-1][0])*w, lon:c[i-1][1]+(c[i][1]-c[i-1][1])*w, idx:i};
}
// phase: pre / out / stop / ret / fin ; returns geometry + metrics
function boatState(b,t){
  const {out,ret}=b;
  const spOut=out.total/(out.end-out.start), spRet=ret.total/(ret.end-ret.start); // m/s
  if(t < out.start){
    const p=out.coords[0];
    return {phase:"pre", lat:p[0], lon:p[1], idx:1, leg:out,
            speed:0, remaining:out.total+ret.total, rank:0};
  }
  if(t <= out.end){
    const f=(t-out.start)/(out.end-out.start), L=locOnLeg(out,f);
    return {phase:"out", lat:L.lat, lon:L.lon, idx:L.idx, leg:out,
            speed:spOut, remaining:(1-f)*out.total+ret.total, destLeft:(1-f)*out.total, rank:1+f};
  }
  if(t < ret.start){
    const n=out.coords.length-1, p=out.coords[n];
    return {phase:"stop", lat:p[0], lon:p[1], idx:n, leg:out,
            speed:0, remaining:ret.total, destLeft:0, rank:2};
  }
  if(t <= ret.end){
    const f=(t-ret.start)/(ret.end-ret.start), L=locOnLeg(ret,f);
    return {phase:"ret", lat:L.lat, lon:L.lon, idx:L.idx, leg:ret,
            speed:spRet, remaining:(1-f)*ret.total, destLeft:(1-f)*ret.total, rank:3+f};
  }
  const n=ret.coords.length-1, p=ret.coords[n];
  return {phase:"fin", lat:p[0], lon:p[1], idx:n, leg:ret, speed:0, remaining:0, destLeft:0, rank:5};
}

// ---- map ----
const map=L.map("map",{zoomControl:true,preferCanvas:true});
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19,attribution:"&copy; OpenStreetMap contributors"}).addTo(map);
L.tileLayer("https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png",{maxZoom:18,opacity:0.85,attribution:"&copy; OpenSeaMap"}).addTo(map);

const allPts=[];
const render_state=[];
RACE.boats.forEach(b=>{
  const faint={color:b.color,weight:2,opacity:0.22,lineJoin:"round"};
  L.polyline(b.out.coords,faint).addTo(map);
  L.polyline(b.ret.coords,faint).addTo(map);
  const progOut=L.polyline([], {color:b.color,weight:3.6,opacity:0.95,lineJoin:"round",lineCap:"round"}).addTo(map);
  const progRet=L.polyline([], {color:b.color,weight:3.6,opacity:0.95,lineJoin:"round",lineCap:"round"}).addTo(map);
  const marker=L.marker([b.out.coords[0][0],b.out.coords[0][1]],{icon:makeIcon(b,0,"pre"),zIndexOffset:1000}).addTo(map);
  render_state.push({b,progOut,progRet,marker});
  b.out.coords.forEach(c=>allPts.push(c));
  b.ret.coords.forEach(c=>allPts.push(c));
});

function makeIcon(b,hdg,phase){
  const short = b.name==="Notre Dame" ? "ND" : b.name;
  const dim = phase==="pre" ? "opacity:.55;" : "";
  const arw = (phase==="out"||phase==="ret")
    ? `<div class="arw" style="transform:translate(-50%,-100%) rotate(${hdg}deg);"></div>` : "";
  return L.divIcon({className:"", iconSize:[16,16], iconAnchor:[8,8],
    html:`<div class="boat-mk" style="--c:${b.color};${dim}">${arw}<div class="dot"></div><div class="tag">${short}</div></div>`});
}

// city labels
function mean(getter){const a=RACE.boats.map(getter);return [a.reduce((s,p)=>s+p[0],0)/a.length,a.reduce((s,p)=>s+p[1],0)/a.length];}
function cityLabel(pos,text){L.marker(pos,{icon:L.divIcon({className:"",iconSize:[0,0],html:`<div class="city-label">${text}</div>`}),interactive:false}).addTo(map);}
cityLabel(mean(b=>b.out.coords[0]),"GDAŃSK");
cityLabel(mean(b=>b.out.coords[b.out.coords.length-1]),"ŁEBA");

map.fitBounds(L.latLngBounds(allPts).pad(0.05));

// map legend
const mleg=L.control({position:"topright"});
mleg.onAdd=function(){const d=L.DomUtil.create("div","map-legend");L.DomEvent.disableClickPropagation(d);
  d.innerHTML=RACE.boats.map(b=>`<div class="r"><span class="sw" style="background:${b.color}"></span>${b.name}</div>`).join("");
  return d;};
mleg.addTo(map);

// ---- cards + gantt DOM ----
const cardsEl=document.getElementById("cards");
RACE.boats.forEach((b,i)=>{
  const el=document.createElement("div");
  el.className="card"; el.style.borderLeftColor=b.color; el.id="card"+i;
  el.innerHTML=`<div class="top"><span class="nm" style="color:${b.color}">${b.name}</span><span class="status" data-f="status">—</span></div>
    <div class="stats">
      <div><b data-f="speed">—</b><span>prędkość</span></div>
      <div><b data-f="dest">—</b><span data-f="destlbl">do celu</span></div>
      <div><b data-f="elapsed">—</b><span>czas etapu</span></div>
    </div>`;
  cardsEl.appendChild(el);
});
const versus=document.createElement("div");
versus.className="card versus";
versus.innerHTML=`<div class="lead" data-f="lead">—</div><div class="sep" data-f="sep">—</div>`;
cardsEl.appendChild(versus);

// gantt
const gEl=document.getElementById("gantt");
function pct(t){return ((t-T0)/SPAN)*100;}
let gantt_html="";
RACE.boats.forEach(b=>{
  const ob=`left:${pct(b.out.start)}%;width:${pct(b.out.end)-pct(b.out.start)}%;background:${b.color}`;
  const sb=`left:${pct(b.out.end)}%;width:${pct(b.ret.start)-pct(b.out.end)}%`;
  const rb=`left:${pct(b.ret.start)}%;width:${pct(b.ret.end)-pct(b.ret.start)}%;background:${b.color}`;
  gantt_html+=`<div class="grow"><div class="glabel" style="color:${b.color}">${b.name==="Notre Dame"?"Notre Dame":"Aries"}</div>
    <div class="gtrack"><div class="bar" style="${ob}" title="Do Łeby"></div>
      <div class="bar stopbar" style="${sb}" title="Postój w Łebie"></div>
      <div class="bar" style="${rb}" title="Do Gdańska"></div></div></div>`;
});
// axis ticks every 6h
let ticks="";
const startH=Math.ceil(T0/3600), endH=Math.floor(T1/3600);
for(let h=Math.ceil(startH/6)*6; h*3600<=T1; h+=6){
  const ts=h*3600; if(ts<T0) continue;
  const d=Math.floor((ts%86400)/3600);
  ticks+=`<div class="tick" style="left:${pct(ts)}%"></div><div class="tlab" style="left:${pct(ts)}%">${String(d).padStart(2,"0")}:00</div>`;
}
gEl.innerHTML=gantt_html+`<div class="grow" style="height:16px"><div class="axis">${ticks}</div></div>
  <div class="cursor" id="gcursor"></div><div class="hit" id="ghit"></div>`;

// ---- formatting ----
function fmtClock(t){
  let tt=((t%86400)+86400)%86400;
  const day=Math.floor(t/86400);
  const hh=String(Math.floor(tt/3600)).padStart(2,"0");
  const mm=String(Math.floor((tt%3600)/60)).padStart(2,"0");
  return {day:day, hh, mm};
}
function fmtDur(sec){ if(sec<0)sec=0; const h=Math.floor(sec/3600),m=Math.floor((sec%3600)/60); return h>0?`${h}h ${String(m).padStart(2,"0")}m`:`${m}m`;}
const STATUS={pre:"Przed startem",out:"W drodze do Łeby",stop:"Postój w Łebie",ret:"W drodze do Gdańska",fin:"Na mecie 🏁"};

// ---- render ----
let t=T0;
function render(){
  const states=RACE.boats.map(b=>boatState(b,t));
  render_state.forEach((rs,i)=>{
    const st=states[i], b=rs.b;
    // progress polylines
    if(st.phase==="pre"){ rs.progOut.setLatLngs([]); rs.progRet.setLatLngs([]); }
    else if(st.phase==="out"){ rs.progOut.setLatLngs(b.out.coords.slice(0,st.idx).concat([[st.lat,st.lon]])); rs.progRet.setLatLngs([]); }
    else if(st.phase==="stop"){ rs.progOut.setLatLngs(b.out.coords); rs.progRet.setLatLngs([]); }
    else if(st.phase==="ret"){ rs.progOut.setLatLngs(b.out.coords); rs.progRet.setLatLngs(b.ret.coords.slice(0,st.idx).concat([[st.lat,st.lon]])); }
    else { rs.progOut.setLatLngs(b.out.coords); rs.progRet.setLatLngs(b.ret.coords); }
    // marker + heading
    const c=st.leg.coords; const j=Math.max(1,Math.min(st.idx,c.length-1));
    const hdg=bearing(c[j-1],c[j]);
    rs.marker.setLatLng([st.lat,st.lon]);
    rs.marker.setIcon(makeIcon(b,hdg,st.phase));
    // card
    const card=document.getElementById("card"+i);
    card.querySelector('[data-f="status"]').textContent=STATUS[st.phase];
    card.querySelector('[data-f="speed"]').textContent = st.speed>0 ? (st.speed*1.94384).toFixed(1)+" kn" : "—";
    const destName = (st.phase==="out")?"do Łeby":(st.phase==="ret")?"do Gdańska":(st.phase==="pre")?"do startu":"—";
    card.querySelector('[data-f="destlbl"]').textContent=destName;
    card.querySelector('[data-f="dest"]').textContent = (st.phase==="out"||st.phase==="ret") ? (st.destLeft/1852).toFixed(1)+" Mm" : (st.phase==="fin"?"ukończono":st.phase==="stop"?"w Łebie":"—");
    let legElapsed="—";
    if(st.phase==="out") legElapsed=fmtDur(t-b.out.start);
    else if(st.phase==="ret") legElapsed=fmtDur(t-b.ret.start);
    else if(st.phase==="stop") legElapsed="postój "+fmtDur(t-b.out.end);
    else if(st.phase==="fin") legElapsed="—";
    card.querySelector('[data-f="elapsed"]').textContent=legElapsed;
  });
  // versus
  const [A,N]=states;
  const sepNm=(hav([A.lat,A.lon],[N.lat,N.lon])/1852);
  let lead="Równo";
  const dr=A.rank-N.rank;
  if(Math.abs(dr)>0.001){
    const leader = dr>0 ? RACE.boats[0] : RACE.boats[1];
    lead = `Prowadzi ${leader.name}`;
  }
  if(A.phase==="fin"&&N.phase==="fin") lead="Obie na mecie 🏁";
  versus.querySelector('[data-f="lead"]').textContent=lead;
  versus.querySelector('[data-f="sep"]').textContent=`Odległość między jachtami: ${sepNm.toFixed(1)} Mm`;
  // clock
  const {day,hh,mm}=fmtClock(t);
  const dm=DAY_META[Math.max(0,Math.min(day,DAY_META.length-1))];
  document.getElementById("clk-day").textContent=`${dm.name} ${dm.date}`;
  document.getElementById("clk-time").textContent=`${hh}:${mm}`;
  // scrubber + gantt cursor
  document.getElementById("scrub").value=Math.round(((t-T0)/SPAN)*1000);
  const gRect=gEl.getBoundingClientRect(), hRect=document.getElementById("ghit").getBoundingClientRect();
  const leftPx=(hRect.left-gRect.left)+((t-T0)/SPAN)*hRect.width;
  document.getElementById("gcursor").style.left=leftPx+"px";
}

// ---- playback ----
let playing=false, rafId=null, last=0;
let minPerSec=parseFloat(document.getElementById("speed").value);
const playBtn=document.getElementById("play");
function setPlaying(p){
  playing=p; playBtn.textContent=p?"⏸":"▶";
  if(p){ last=0; rafId=requestAnimationFrame(step); }
  else if(rafId){ cancelAnimationFrame(rafId); rafId=null; }
}
function step(ts){
  if(!playing) return;
  if(!last) last=ts;
  const dt=(ts-last)/1000; last=ts;
  t += dt*minPerSec*60;
  if(t>=T1){ t=T1; render(); setPlaying(false); return; }
  render();
  rafId=requestAnimationFrame(step);
}
playBtn.addEventListener("click",()=>setPlaying(!playing));
document.getElementById("speed").addEventListener("change",e=>{minPerSec=parseFloat(e.target.value);});
document.getElementById("reset").addEventListener("click",()=>{ setPlaying(false); t=T0; render(); });
document.getElementById("scrub").addEventListener("input",e=>{ t=T0+(e.target.value/1000)*SPAN; render(); });
// gantt click / drag to scrub
const ghit=document.getElementById("ghit");
function scrubFromEvent(ev){
  const r=ghit.getBoundingClientRect();
  const x=Math.max(0,Math.min(1,(ev.clientX-r.left)/r.width));
  t=T0+x*SPAN; render();
}
let dragging=false;
ghit.addEventListener("pointerdown",e=>{dragging=true;ghit.setPointerCapture(e.pointerId);scrubFromEvent(e);});
ghit.addEventListener("pointermove",e=>{if(dragging)scrubFromEvent(e);});
ghit.addEventListener("pointerup",()=>{dragging=false;});
// keyboard
window.addEventListener("keydown",e=>{
  if(e.code==="Space"){e.preventDefault();setPlaying(!playing);}
  else if(e.code==="ArrowRight"){t=Math.min(T1,t+300);render();}
  else if(e.code==="ArrowLeft"){t=Math.max(T0,t-300);render();}
});

render();
setTimeout(()=>map.invalidateSize(),200);
window.addEventListener("resize",()=>map.invalidateSize());
</script>
</body>
</html>
"""


def build():
    print("Building 48h Łeba replay...\n")
    race = build_race()
    html = TEMPLATE.replace("__RACE__", json.dumps(race, ensure_ascii=False))
    out_path = os.path.join(OUT, "leba-48h-replay.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nWrote {out_path}  ({os.path.getsize(out_path)/1024:.0f} KB)")


if __name__ == "__main__":
    build()
