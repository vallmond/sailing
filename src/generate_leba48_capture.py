#!/usr/bin/env python3
"""
Generate a VERTICAL (1080x1920) capture-optimised page for the 48h race replay,
designed to be frame-stepped by a headless browser -> PNG frames -> ffmpeg -> MP4
for Instagram / TikTok.

Dark CARTO basemap, glowing tracks, broadcast-style HUD. No controls / autoplay:
exposes window.CAP = { T0, T1, SPAN, ready, renderAt(t) }.

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
  html,body { width:1080px; height:1920px; overflow:hidden; background:#05070d;
              font-family:"Inter","Helvetica Neue",system-ui,-apple-system,sans-serif; color:#fff; }
  #map { position:fixed; inset:0; width:1080px; height:1920px; background:#05070d; }
  .leaflet-container { background:#05070d; }
  #hud { position:fixed; inset:0; pointer-events:none; z-index:600;
         display:flex; flex-direction:column; justify-content:space-between; }
  /* top */
  .top { padding:60px 60px 0; text-align:center;
         background:linear-gradient(180deg, rgba(5,7,13,0.92) 0%, rgba(5,7,13,0.6) 55%, rgba(5,7,13,0) 100%); }
  .title { font-size:40px; font-weight:800; letter-spacing:6px; color:#e2e8f0; }
  .subtitle { margin-top:8px; font-size:22px; font-weight:600; letter-spacing:3px; color:#7c8798; text-transform:uppercase; }
  .clock { margin-top:26px; display:inline-flex; align-items:baseline; gap:20px; padding:14px 34px;
           background:rgba(15,23,42,0.55); border:1px solid rgba(148,163,184,0.28); border-radius:22px;
           backdrop-filter:blur(6px); }
  .clock .cday { font-size:26px; font-weight:700; letter-spacing:4px; color:#94a3b8; text-transform:uppercase; }
  .clock .ctime { font-size:64px; font-weight:800; letter-spacing:2px; color:#fff; font-variant-numeric:tabular-nums; line-height:1; }
  /* bottom */
  .bottom { padding:0 48px 70px;
            background:linear-gradient(0deg, rgba(5,7,13,0.94) 0%, rgba(5,7,13,0.72) 55%, rgba(5,7,13,0) 100%); }
  .lead { text-align:center; font-size:30px; font-weight:800; letter-spacing:2px; margin-bottom:8px;
          white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .lead .gap { color:#94a3b8; font-weight:700; letter-spacing:2px; }
  .boats { display:flex; flex-direction:column; gap:16px; margin-top:22px; }
  .brow { display:flex; align-items:center; gap:22px; padding:22px 28px; border-radius:20px;
          background:rgba(15,23,42,0.6); border:1px solid rgba(148,163,184,0.20); border-left-width:8px; }
  .brow .dot { width:26px; height:26px; border-radius:50%; flex:none; box-shadow:0 0 18px 3px var(--c); background:var(--c); }
  .brow .nm { font-size:38px; font-weight:800; letter-spacing:1px; min-width:230px; }
  .brow .ph { font-size:24px; font-weight:600; color:#9aa6b6; flex:1; }
  .brow .stat { text-align:right; font-variant-numeric:tabular-nums; }
  .brow .stat .v { font-size:40px; font-weight:800; line-height:1; }
  .brow .stat .l { font-size:20px; font-weight:600; color:#8b97a7; letter-spacing:1px; }
  .brow .stat.spd { min-width:150px; }
  .brow .stat.dst { min-width:210px; }
  .progress { margin-top:30px; height:10px; border-radius:6px; background:rgba(148,163,184,0.22); overflow:hidden; }
  .progress .pfill { height:100%; width:0%; background:linear-gradient(90deg,#e6550d,#f59e0b); }
  /* boat markers */
  .bmk { position:relative; }
  .bmk .glow { position:absolute; left:50%; top:50%; width:34px; height:34px; border-radius:50%;
     transform:translate(-50%,-50%); background:var(--c); opacity:0.35; filter:blur(6px); }
  .bmk .core { position:absolute; left:50%; top:50%; width:18px; height:18px; border-radius:50%;
     transform:translate(-50%,-50%); background:var(--c); border:3px solid #fff; box-shadow:0 0 12px var(--c); }
  .bmk .arw { position:absolute; left:50%; top:50%; width:0; height:0;
     border-left:8px solid transparent; border-right:8px solid transparent; border-bottom:20px solid var(--c);
     transform-origin:50% 100%; filter:drop-shadow(0 0 6px var(--c)); }
  .bmk .tag { position:absolute; left:50%; top:26px; transform:translateX(-50%); background:var(--c); color:#fff;
     font-size:22px; font-weight:800; letter-spacing:1px; padding:3px 12px; border-radius:9px; white-space:nowrap;
     box-shadow:0 2px 10px rgba(0,0,0,.5); }
  .city { font-size:24px; font-weight:800; letter-spacing:5px; color:#cbd5e1;
     text-shadow:0 0 8px #000,0 0 14px #000; white-space:nowrap; }
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

const map=L.map("map",{zoomControl:false,attributionControl:false,preferCanvas:true,fadeAnimation:false,zoomAnimation:false});
const base=L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
  {subdomains:"abcd",maxZoom:19}).addTo(map);

const allPts=[]; const RS=[];
RACE.boats.forEach(b=>{
  const faint={color:b.color,weight:2,opacity:0.18,lineJoin:"round"};
  L.polyline(b.out.coords,faint).addTo(map);
  L.polyline(b.ret.coords,faint).addTo(map);
  const glowStyle={color:b.color,weight:11,opacity:0.22,lineJoin:"round",lineCap:"round"};
  const brightStyle={color:b.color,weight:4,opacity:1,lineJoin:"round",lineCap:"round"};
  const gO=L.polyline([],glowStyle).addTo(map), gR=L.polyline([],glowStyle).addTo(map);
  const pO=L.polyline([],brightStyle).addTo(map), pR=L.polyline([],brightStyle).addTo(map);
  const mk=L.marker([b.out.coords[0][0],b.out.coords[0][1]],{icon:makeIcon(b,0,"pre"),zIndexOffset:1000,interactive:false}).addTo(map);
  RS.push({b,gO,gR,pO,pR,mk});
  b.out.coords.forEach(c=>allPts.push(c)); b.ret.coords.forEach(c=>allPts.push(c));
});
function makeIcon(b,hdg,phase){const short=b.name==="Notre Dame"?"ND":"ARIES";
  const arw=(phase==="out"||phase==="ret")?`<div class="arw" style="transform:translate(-50%,-100%) rotate(${hdg}deg);"></div>`:"";
  const dim=phase==="pre"?"opacity:.5;":"";
  const tagTop=b.name==="Notre Dame"?"top:-38px":"top:26px";  // stagger tags so they don't collide
  return L.divIcon({className:"",iconSize:[18,18],iconAnchor:[9,9],
    html:`<div class="bmk" style="--c:${b.color};${dim}"><div class="glow"></div>${arw}<div class="core"></div><div class="tag" style="${tagTop}">${short}</div></div>`});}
function mean(g){const a=RACE.boats.map(g);return[a.reduce((s,p)=>s+p[0],0)/a.length,a.reduce((s,p)=>s+p[1],0)/a.length];}
function city(pos,txt){L.marker(pos,{icon:L.divIcon({className:"",iconSize:[0,0],html:`<div class="city">${txt}</div>`}),interactive:false}).addTo(map);}
city(mean(b=>b.out.coords[0]),"GDAŃSK");
city(mean(b=>b.out.coords[b.out.coords.length-1]),"ŁEBA");
map.fitBounds(L.latLngBounds(allPts),{paddingTopLeft:[50,360],paddingBottomRight:[50,520]});

// build boat rows
const boatsEl=document.getElementById("boats");
RACE.boats.forEach((b,i)=>{const el=document.createElement("div");el.className="brow";el.id="br"+i;
  el.style.setProperty("--c",b.color);el.style.borderLeftColor=b.color;
  el.innerHTML=`<div class="dot"></div><div class="nm">${b.name}</div><div class="ph" data-f="ph">—</div>
    <div class="stat spd"><div class="v" data-f="spd">—</div><div class="l">węzły</div></div>
    <div class="stat dst"><div class="v" data-f="dst">—</div><div class="l" data-f="dstl">do celu</div></div>`;
  boatsEl.appendChild(el);});

const STATUS={pre:"przed startem",out:"→ do Łeby",stop:"postój w Łebie",ret:"← do Gdańska",fin:"na mecie 🏁"};

function renderAt(t){
  const states=RACE.boats.map(b=>boatState(b,t));
  RS.forEach((rs,i)=>{const st=states[i],b=rs.b;
    if(st.phase==="pre"){rs.pO.setLatLngs([]);rs.gO.setLatLngs([]);rs.pR.setLatLngs([]);rs.gR.setLatLngs([]);}
    else if(st.phase==="out"){const seg=b.out.coords.slice(0,st.idx).concat([[st.lat,st.lon]]);
      rs.pO.setLatLngs(seg);rs.gO.setLatLngs(seg);rs.pR.setLatLngs([]);rs.gR.setLatLngs([]);}
    else if(st.phase==="stop"){rs.pO.setLatLngs(b.out.coords);rs.gO.setLatLngs(b.out.coords);rs.pR.setLatLngs([]);rs.gR.setLatLngs([]);}
    else if(st.phase==="ret"){rs.pO.setLatLngs(b.out.coords);rs.gO.setLatLngs(b.out.coords);
      const seg=b.ret.coords.slice(0,st.idx).concat([[st.lat,st.lon]]);rs.pR.setLatLngs(seg);rs.gR.setLatLngs(seg);}
    else {rs.pO.setLatLngs(b.out.coords);rs.gO.setLatLngs(b.out.coords);rs.pR.setLatLngs(b.ret.coords);rs.gR.setLatLngs(b.ret.coords);}
    const c=st.leg.coords,j=Math.max(1,Math.min(st.idx,c.length-1));
    rs.mk.setLatLng([st.lat,st.lon]);rs.mk.setIcon(makeIcon(b,bearing(c[j-1],c[j]),st.phase));
    const row=document.getElementById("br"+i);
    row.querySelector('[data-f="ph"]').textContent=STATUS[st.phase];
    row.querySelector('[data-f="spd"]').textContent=st.speed>0?(st.speed*1.94384).toFixed(1):"—";
    row.querySelector('[data-f="dst"]').textContent=(st.phase==="out"||st.phase==="ret")?(st.destLeft/1852).toFixed(1):(st.phase==="fin"?"0.0":"—");
    row.querySelector('[data-f="dstl"]').textContent=st.phase==="out"?"Mm do Łeby":st.phase==="ret"?"Mm do Gdańska":st.phase==="fin"?"ukończono":st.phase==="stop"?"w Łebie":"do startu";
  });
  const[A,N]=states;const dr=A.rank-N.rank;
  const sep=(hav([A.lat,A.lon],[N.lat,N.lon])/1852);
  function nm(i){return `<span style="color:${RACE.boats[i].color}">${RACE.boats[i].name.toUpperCase()}</span>`;}
  let lead;
  if(A.phase==="fin"&&N.phase==="fin"){
    lead=`META 🏁 · ${nm(0)} WYGRYWA`;
  }else if(A.phase===N.phase && (A.phase==="out"||A.phase==="ret")){
    // both on the same leg -> real racing margin = difference in distance-to-mark
    const li=A.destLeft<=N.destLeft?0:1, margin=Math.abs(A.destLeft-N.destLeft)/1852;
    lead=`PROWADZI ${nm(li)} <span class="gap">· ${margin.toFixed(1)} Mm przewagi</span>`;
  }else if(Math.abs(dr)<0.001){
    lead="RÓWNO";
  }else{
    const li=dr>0?0:1;
    lead=`PROWADZI ${nm(li)} <span class="gap">· ${sep.toFixed(1)} Mm od siebie</span>`;
  }
  document.getElementById("lead").innerHTML=lead;
  let tt=((t%86400)+86400)%86400,day=Math.floor(t/86400);
  const dm=DAY_META[Math.max(0,Math.min(day,2))];
  document.getElementById("cday").textContent=`${dm.name} ${dm.date}`;
  document.getElementById("ctime").textContent=String(Math.floor(tt/3600)).padStart(2,"0")+":"+String(Math.floor((tt%3600)/60)).padStart(2,"0");
  document.getElementById("pfill").style.width=(((t-T0)/SPAN)*100).toFixed(2)+"%";
}

let tilesLoaded=false;
base.on("load",()=>{tilesLoaded=true;});
window.CAP={T0,T1,SPAN,get ready(){return tilesLoaded;},renderAt};
renderAt(T0);
</script>
</body>
</html>
"""


def build():
    print("Building vertical capture page...")
    race = build_race()
    html = TEMPLATE.replace("__RACE__", json.dumps(race, ensure_ascii=False))
    path = os.path.join(OUT, "leba-48h-capture.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {path}  ({os.path.getsize(path)/1024:.0f} KB)")


if __name__ == "__main__":
    build()
