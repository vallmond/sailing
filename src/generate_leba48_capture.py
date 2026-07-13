#!/usr/bin/env python3
"""
Generate a VERTICAL (1080x1920) capture-optimised page for the 48h race replay,
designed to be frame-stepped by a headless browser -> PNG frames -> ffmpeg -> MP4
for Instagram / TikTok.

LIGHT theme (CARTO Voyager), broadcast-style HUD, and a FOLLOW-CAMERA that keeps
both boats framed and zoomed in (not a static overview) so the tacking detail is
large on screen. No controls / autoplay: exposes
    window.CAP = { T0, T1, SPAN, ready, tilesPending(), renderAt(t) }.

Reuses timing + track data from generate_leba48_replay.build_race().
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_leba48_replay import build_race, OUT  # noqa: E402

TEMPLATE = r"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<title>48h Łeba — capture</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  * { box-sizing:border-box; margin:0; padding:0; }
  html,body { width:1080px; height:1920px; overflow:hidden; background:#dbe7ef;
              font-family:"Inter","Helvetica Neue",system-ui,-apple-system,sans-serif; color:#0f172a; }
  #map { position:fixed; inset:0; width:1080px; height:1920px; background:#dbe7ef; }
  .leaflet-container { background:#dbe7ef; }
  #hud { position:fixed; inset:0; pointer-events:none; z-index:600;
         display:flex; flex-direction:column; justify-content:space-between; }
  /* top */
  .top { padding:56px 60px 0; text-align:center;
         background:linear-gradient(180deg, rgba(247,250,252,0.96) 0%, rgba(247,250,252,0.72) 52%, rgba(247,250,252,0) 100%); }
  .title { font-size:40px; font-weight:800; letter-spacing:6px; color:#0f172a; }
  .subtitle { margin-top:8px; font-size:22px; font-weight:700; letter-spacing:3px; color:#5b6b7d; text-transform:uppercase; }
  .clock { margin-top:24px; display:inline-flex; align-items:baseline; gap:20px; padding:14px 34px;
           background:rgba(255,255,255,0.82); border:1px solid rgba(15,23,42,0.10); border-radius:22px;
           box-shadow:0 10px 30px rgba(15,23,42,0.14); backdrop-filter:blur(6px); }
  .clock .cday { font-size:26px; font-weight:800; letter-spacing:4px; color:#64748b; text-transform:uppercase; }
  .clock .ctime { font-size:64px; font-weight:800; letter-spacing:2px; color:#0f172a; font-variant-numeric:tabular-nums; line-height:1; }
  /* bottom */
  .bottom { padding:0 48px 70px;
            background:linear-gradient(0deg, rgba(247,250,252,0.97) 0%, rgba(247,250,252,0.80) 55%, rgba(247,250,252,0) 100%); }
  .lead { text-align:center; font-size:30px; font-weight:800; letter-spacing:2px; margin-bottom:8px; color:#0f172a;
          white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .lead .gap { color:#5b6b7d; font-weight:700; letter-spacing:2px; }
  .boats { display:flex; flex-direction:column; gap:16px; margin-top:22px; }
  .brow { display:flex; align-items:center; gap:22px; padding:22px 28px; border-radius:20px;
          background:rgba(255,255,255,0.90); border:1px solid rgba(15,23,42,0.08); border-left-width:8px;
          box-shadow:0 8px 24px rgba(15,23,42,0.12); }
  .brow .dot { width:26px; height:26px; border-radius:50%; flex:none; box-shadow:0 0 0 4px color-mix(in srgb, var(--c) 22%, transparent); background:var(--c); }
  .brow .nm { font-size:36px; font-weight:800; letter-spacing:0.5px; min-width:300px; color:#0f172a; }
  .brow .ph { font-size:24px; font-weight:700; color:#64748b; flex:1; white-space:nowrap; }
  .brow .stat { text-align:right; font-variant-numeric:tabular-nums; }
  .brow .stat .v { font-size:40px; font-weight:800; line-height:1; color:#0f172a; }
  .brow .stat .l { font-size:20px; font-weight:700; color:#8b97a7; letter-spacing:1px; }
  .brow .stat.spd { min-width:130px; }
  .brow .stat.dst { min-width:210px; }
  .progress { margin-top:30px; height:10px; border-radius:6px; background:rgba(15,23,42,0.12); overflow:hidden; }
  .progress .pfill { height:100%; width:0%; background:linear-gradient(90deg,#e6550d,#f59e0b); }
  /* boat markers */
  .bmk { position:relative; }
  .bmk .core { position:absolute; left:50%; top:50%; width:22px; height:22px; border-radius:50%;
     transform:translate(-50%,-50%); background:var(--c); border:4px solid #fff;
     box-shadow:0 0 0 2px var(--c), 0 3px 8px rgba(15,23,42,0.45); }
  .bmk .arw { position:absolute; left:50%; top:50%; width:0; height:0;
     border-left:9px solid transparent; border-right:9px solid transparent; border-bottom:22px solid var(--c);
     transform-origin:50% 100%; filter:drop-shadow(0 1px 2px rgba(255,255,255,0.9)); }
  .bmk .tag { position:absolute; left:50%; top:30px; transform:translateX(-50%); background:var(--c); color:#fff;
     font-size:22px; font-weight:800; letter-spacing:0.5px; padding:4px 14px; border-radius:10px; white-space:nowrap;
     box-shadow:0 3px 10px rgba(15,23,42,0.35); }
  .city { font-size:26px; font-weight:800; letter-spacing:5px; color:#1f2d3d;
     text-shadow:0 0 7px #fff,0 0 12px #fff,0 0 3px #fff; white-space:nowrap; }
</style>
</head>
<body>
<div id="map"></div>
<div id="hud">
  <div class="top">
    <div class="title">GDAŃSK ⇄ ŁEBA · 48H</div>
    <div class="subtitle">Aries vs Notre Dame</div>
    <div class="clock"><span class="cday" id="cday">PIĄTEK 10.07</span><span class="ctime" id="ctime">19:48</span></div>
  </div>
  <div class="bottom">
    <div class="lead" id="lead">—</div>
    <div class="boats" id="boats"></div>
    <div class="progress"><div class="pfill" id="pfill"></div></div>
  </div>
</div>

<script>
const RACE = __RACE__;
const DAY_META = [{name:"PIĄTEK",date:"10.07"},{name:"SOBOTA",date:"11.07"},{name:"NIEDZIELA",date:"12.07"}];
const D2R = Math.PI/180;
function hav(a,b){const R=6371000,la1=a[0]*D2R,la2=b[0]*D2R,dla=(b[0]-a[0])*D2R,dlo=(b[1]-a[1])*D2R;
  const h=Math.sin(dla/2)**2+Math.cos(la1)*Math.cos(la2)*Math.sin(dlo/2)**2;return 2*R*Math.asin(Math.sqrt(h));}
function bearing(a,b){const y=Math.sin((b[1]-a[1])*D2R)*Math.cos(b[0]*D2R);
  const x=Math.cos(a[0]*D2R)*Math.sin(b[0]*D2R)-Math.sin(a[0]*D2R)*Math.cos(b[0]*D2R)*Math.cos((b[1]-a[1])*D2R);
  return (Math.atan2(y,x)/D2R+360)%360;}
function prep(leg){const c=leg.coords,cum=new Float64Array(c.length);
  for(let i=1;i<c.length;i++)cum[i]=cum[i-1]+hav(c[i-1],c[i]);leg.cum=cum;leg.total=cum[c.length-1];}
RACE.boats.forEach(b=>{prep(b.out);prep(b.ret);});
const T0=Math.min(...RACE.boats.map(b=>b.out.start));
const T1=Math.max(...RACE.boats.map(b=>b.ret.end));
const SPAN=T1-T0;
function locOnLeg(leg,f){const c=leg.coords,cum=leg.cum,target=Math.max(0,Math.min(1,f))*leg.total;
  if(target<=0)return{lat:c[0][0],lon:c[0][1],idx:1};
  if(target>=leg.total){const n=c.length-1;return{lat:c[n][0],lon:c[n][1],idx:n};}
  let lo=1,hi=c.length-1;while(lo<hi){const mid=(lo+hi)>>1;if(cum[mid]<target)lo=mid+1;else hi=mid;}
  const i=lo,seg=cum[i]-cum[i-1],w=seg?(target-cum[i-1])/seg:0;
  return{lat:c[i-1][0]+(c[i][0]-c[i-1][0])*w,lon:c[i-1][1]+(c[i][1]-c[i-1][1])*w,idx:i};}
function boatState(b,t){const{out,ret}=b;
  const spOut=out.total/(out.end-out.start),spRet=ret.total/(ret.end-ret.start);
  if(t<out.start){const p=out.coords[0];return{phase:"pre",lat:p[0],lon:p[1],idx:1,leg:out,speed:0,destLeft:out.total,rank:0};}
  if(t<=out.end){const f=(t-out.start)/(out.end-out.start),L=locOnLeg(out,f);
    return{phase:"out",lat:L.lat,lon:L.lon,idx:L.idx,leg:out,speed:spOut,destLeft:(1-f)*out.total,rank:1+f};}
  if(t<ret.start){const n=out.coords.length-1,p=out.coords[n];
    return{phase:"stop",lat:p[0],lon:p[1],idx:n,leg:out,speed:0,destLeft:0,rank:2};}
  if(t<=ret.end){const f=(t-ret.start)/(ret.end-ret.start),L=locOnLeg(ret,f);
    return{phase:"ret",lat:L.lat,lon:L.lon,idx:L.idx,leg:ret,speed:spRet,destLeft:(1-f)*ret.total,rank:3+f};}
  const n=ret.coords.length-1,p=ret.coords[n];
  return{phase:"fin",lat:p[0],lon:p[1],idx:n,leg:ret,speed:0,destLeft:0,rank:5};}

const map=L.map("map",{zoomControl:false,attributionControl:false,preferCanvas:true,
  fadeAnimation:false,zoomAnimation:false,inertia:false,zoomSnap:0});
map.setView([54.6,18.15],10);
const base=L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png",
  {subdomains:"abcd",maxZoom:19}).addTo(map);
let pending=0;
base.on("tileloadstart",()=>{pending++;});
base.on("tileload",()=>{pending=Math.max(0,pending-1);});
base.on("tileerror",()=>{pending=Math.max(0,pending-1);});

const RS=[];
RACE.boats.forEach(b=>{
  const faint={color:b.color,weight:2,opacity:0.30,lineJoin:"round"};
  L.polyline(b.out.coords,faint).addTo(map);
  L.polyline(b.ret.coords,faint).addTo(map);
  const casing={color:"#ffffff",weight:8,opacity:0.9,lineJoin:"round",lineCap:"round"};
  const bright={color:b.color,weight:4.5,opacity:1,lineJoin:"round",lineCap:"round"};
  const cO=L.polyline([],casing).addTo(map), cR=L.polyline([],casing).addTo(map);
  const pO=L.polyline([],bright).addTo(map), pR=L.polyline([],bright).addTo(map);
  const mk=L.marker([b.out.coords[0][0],b.out.coords[0][1]],{icon:makeIcon(b,0,"pre"),zIndexOffset:1000,interactive:false}).addTo(map);
  RS.push({b,cO,cR,pO,pR,mk});
});
function makeIcon(b,hdg,phase){const label=b.name;
  const arw=(phase==="out"||phase==="ret")?`<div class="arw" style="transform:translate(-50%,-100%) rotate(${hdg}deg);"></div>`:"";
  const dim=phase==="pre"?"opacity:.55;":"";
  const tagTop=b.name==="Notre Dame"?"top:-40px":"top:30px";  // stagger tags so they don't collide
  return L.divIcon({className:"",iconSize:[22,22],iconAnchor:[11,11],
    html:`<div class="bmk" style="--c:${b.color};${dim}">${arw}<div class="core"></div><div class="tag" style="${tagTop}">${label}</div></div>`});}
function mean(g){const a=RACE.boats.map(g);return[a.reduce((s,p)=>s+p[0],0)/a.length,a.reduce((s,p)=>s+p[1],0)/a.length];}
function city(pos,txt){L.marker(pos,{icon:L.divIcon({className:"",iconSize:[0,0],html:`<div class="city">${txt}</div>`}),interactive:false}).addTo(map);}
city(mean(b=>b.out.coords[0]),"GDAŃSK");
city(mean(b=>b.out.coords[b.out.coords.length-1]),"ŁEBA");

// build boat rows
const boatsEl=document.getElementById("boats");
RACE.boats.forEach((b,i)=>{const el=document.createElement("div");el.className="brow";el.id="br"+i;
  el.style.setProperty("--c",b.color);el.style.borderLeftColor=b.color;
  el.innerHTML=`<div class="dot"></div><div class="nm">${b.name}</div><div class="ph" data-f="ph">—</div>
    <div class="stat spd"><div class="v" data-f="spd">—</div><div class="l">węzły</div></div>
    <div class="stat dst"><div class="v" data-f="dst">—</div><div class="l" data-f="dstl">do celu</div></div>`;
  boatsEl.appendChild(el);});

const STATUS={pre:"przed startem",out:"→ do Łeby",stop:"postój w Łebie",ret:"← do Gdańska",fin:"na mecie 🏁"};

// follow-camera tuning (filled per variant)
const FOLLOW_MULT=__FOLLOW_MULT__;       // context around the boat separation
const MIN_DLAT=__MIN_DLAT__, MIN_DLON=__MIN_DLON__;   // min view so close/coincident boats aren't over-zoomed
const CAM_PAD_TL=[46,300], CAM_PAD_BR=[46,380], CAM_MAXZOOM=__CAM_MAXZOOM__;

function renderAt(t){
  const states=RACE.boats.map(b=>boatState(b,t));
  RS.forEach((rs,i)=>{const st=states[i],b=rs.b;
    if(st.phase==="pre"){rs.pO.setLatLngs([]);rs.cO.setLatLngs([]);rs.pR.setLatLngs([]);rs.cR.setLatLngs([]);}
    else if(st.phase==="out"){const seg=b.out.coords.slice(0,st.idx).concat([[st.lat,st.lon]]);
      rs.cO.setLatLngs(seg);rs.pO.setLatLngs(seg);rs.cR.setLatLngs([]);rs.pR.setLatLngs([]);}
    else if(st.phase==="stop"){rs.cO.setLatLngs(b.out.coords);rs.pO.setLatLngs(b.out.coords);rs.cR.setLatLngs([]);rs.pR.setLatLngs([]);}
    else if(st.phase==="ret"){rs.cO.setLatLngs(b.out.coords);rs.pO.setLatLngs(b.out.coords);
      const seg=b.ret.coords.slice(0,st.idx).concat([[st.lat,st.lon]]);rs.cR.setLatLngs(seg);rs.pR.setLatLngs(seg);}
    else {rs.cO.setLatLngs(b.out.coords);rs.pO.setLatLngs(b.out.coords);rs.cR.setLatLngs(b.ret.coords);rs.pR.setLatLngs(b.ret.coords);}
    const c=st.leg.coords,j=Math.max(1,Math.min(st.idx,c.length-1));
    rs.mk.setLatLng([st.lat,st.lon]);rs.mk.setIcon(makeIcon(b,bearing(c[j-1],c[j]),st.phase));
    const row=document.getElementById("br"+i);
    row.querySelector('[data-f="ph"]').textContent=STATUS[st.phase];
    row.querySelector('[data-f="spd"]').textContent=st.speed>0?(st.speed*1.94384).toFixed(1):"—";
    row.querySelector('[data-f="dst"]').textContent=(st.phase==="out"||st.phase==="ret")?(st.destLeft/1852).toFixed(1):(st.phase==="fin"?"0.0":"—");
    row.querySelector('[data-f="dstl"]').textContent=st.phase==="out"?"Mm do Łeby":st.phase==="ret"?"Mm do Gdańska":st.phase==="fin"?"ukończono":st.phase==="stop"?"w Łebie":"do startu";
  });
  // headline
  const[A,N]=states;const dr=A.rank-N.rank;
  const sep=(hav([A.lat,A.lon],[N.lat,N.lon])/1852);
  function nm(i){return `<span style="color:${RACE.boats[i].color}">${RACE.boats[i].name.toUpperCase()}</span>`;}
  let lead;
  if(A.phase==="fin"&&N.phase==="fin"){lead=`META 🏁 · ${nm(0)} WYGRYWA`;}
  else if(A.phase===N.phase && (A.phase==="out"||A.phase==="ret")){
    const li=A.destLeft<=N.destLeft?0:1, margin=Math.abs(A.destLeft-N.destLeft)/1852;
    lead=`PROWADZI ${nm(li)} <span class="gap">· ${margin.toFixed(1)} Mm przewagi</span>`;
  }else if(Math.abs(dr)<0.001){lead="RÓWNO";}
  else{const li=dr>0?0:1;lead=`PROWADZI ${nm(li)} <span class="gap">· ${sep.toFixed(1)} Mm od siebie</span>`;}
  document.getElementById("lead").innerHTML=lead;
  // clock
  let tt=((t%86400)+86400)%86400,day=Math.floor(t/86400);
  const dm=DAY_META[Math.max(0,Math.min(day,2))];
  document.getElementById("cday").textContent=`${dm.name} ${dm.date}`;
  document.getElementById("ctime").textContent=String(Math.floor(tt/3600)).padStart(2,"0")+":"+String(Math.floor((tt%3600)/60)).padStart(2,"0");
  document.getElementById("pfill").style.width=(((t-T0)/SPAN)*100).toFixed(2)+"%";
  // follow-camera: frame both boats, zoomed in
  const clat=(A.lat+N.lat)/2, clon=(A.lon+N.lon)/2;
  const dlat=Math.max(Math.abs(A.lat-N.lat)*FOLLOW_MULT, MIN_DLAT);
  const dlon=Math.max(Math.abs(A.lon-N.lon)*FOLLOW_MULT, MIN_DLON);
  const bnds=L.latLngBounds([clat-dlat/2,clon-dlon/2],[clat+dlat/2,clon+dlon/2]);
  map.fitBounds(bnds,{paddingTopLeft:CAM_PAD_TL,paddingBottomRight:CAM_PAD_BR,maxZoom:CAM_MAXZOOM,animate:false});
}

let tilesLoaded=false;
base.on("load",()=>{tilesLoaded=true;});
window.CAP={T0,T1,SPAN,get ready(){return tilesLoaded;},tilesPending(){return pending;},renderAt};
renderAt(T0);
</script>
</body>
</html>
"""


# follow-camera variants. v1 = original (max zoom-in ~13.5). v2 = less max scale:
# pulls back when boats are close so more surrounding detail is visible.
VARIANTS = {
    "v1": {"page": "leba-48h-capture.html",
           "follow_mult": 2.0, "min_dlat": 0.055, "min_dlon": 0.095, "maxzoom": 13.5},
    "v2": {"page": "leba-48h-capture-v2.html",
           "follow_mult": 2.0, "min_dlat": 0.095, "min_dlon": 0.165, "maxzoom": 12.2},
}


def build():
    print("Building vertical capture pages (light theme + follow-cam)...")
    race = build_race()
    race_json = json.dumps(race, ensure_ascii=False)
    for name, v in VARIANTS.items():
        html = (TEMPLATE
                .replace("__RACE__", race_json)
                .replace("__FOLLOW_MULT__", str(v["follow_mult"]))
                .replace("__MIN_DLAT__", str(v["min_dlat"]))
                .replace("__MIN_DLON__", str(v["min_dlon"]))
                .replace("__CAM_MAXZOOM__", str(v["maxzoom"])))
        path = os.path.join(OUT, v["page"])
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  [{name}] maxzoom={v['maxzoom']}  -> {path}  ({os.path.getsize(path)/1024:.0f} KB)")


if __name__ == "__main__":
    build()
