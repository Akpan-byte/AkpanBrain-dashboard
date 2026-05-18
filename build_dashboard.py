#!/usr/bin/env python3
"""Build the complete AkpanBrain v3 dashboard HTML"""
import os

# ─── COLOR SCHEME: Red, Black, Silver Chrome ───
# Primary: Red (#FF0000), Secondary: Silver Chrome (#C0C0C0), Dark: #0a0a0a

HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5, user-scalable=yes">
<title>AKPANBRAIN — Neural Command</title>
<style>
:root {
  --red: #FF0000;
  --red-dim: #800000;
  --red-glow: rgba(255,0,0,.3);
  --silver: #C0C0C0;
  --silver-dim: #707070;
  --silver-dark: #404040;
  --black: #0a0a0a;
  --black-mid: #111111;
  --black-light: #1a1a1a;
  --panel: rgba(10,10,10,.95);
  --border: rgba(192,192,192,.1);
}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--black);color:var(--silver);font-family:'Courier New',monospace;overflow:hidden;height:100vh;width:100vw;cursor:default;touch-action:none}
#three{position:fixed;top:0;left:0;width:100%;height:100%;z-index:1;touch-action:none}
#hud{position:fixed;top:0;left:0;width:100%;height:100%;z-index:10;pointer-events:none;display:grid;grid-template-columns:240px 1fr 240px;grid-template-rows:40px 1fr 120px;}
@media(max-width:900px){#hud{grid-template-columns:1fr;grid-template-rows:36px auto 1fr auto 90px}#lpanel{grid-row:2;max-height:150px;overflow-x:auto;border-right:none;border-bottom:1px solid var(--border)}#center{grid-row:3}#rpanel{grid-row:4;border-left:none;border-top:1px solid var(--border);max-height:150px}#bottom{grid-row:5;max-height:90px}}
#topbar{grid-column:1/-1;display:flex;align-items:center;justify-content:space-between;padding:0 12px;border-bottom:1px solid var(--border);background:var(--black-mid);pointer-events:auto}
.logo{font-size:12px;font-weight:900;letter-spacing:4px;color:var(--red);text-shadow:0 0 10px var(--red-glow)}
.clock{font-size:9px;color:var(--silver);letter-spacing:2px}
.tab{padding:3px 10px;font-size:8px;letter-spacing:1px;border:1px solid var(--border);border-radius:2px;cursor:pointer;text-decoration:none;color:var(--silver);text-transform:uppercase;transition:all .2s;pointer-events:auto}
.tab:hover{border-color:var(--red);color:#fff}
#lpanel{grid-row:2;padding:8px;overflow-y:auto;pointer-events:auto;background:var(--black-mid);border-right:1px solid var(--border)}
#rpanel{grid-row:2;padding:8px;overflow-y:auto;pointer-events:auto;background:var(--black-mid);border-left:1px solid var(--border)}
#bottom{grid-column:1/-1;padding:8px 12px;overflow-y:auto;pointer-events:auto;border-top:1px solid var(--border);background:var(--black-mid);-webkit-overflow-scrolling:touch}
.stitle{font-size:9px;letter-spacing:3px;color:var(--red);text-transform:uppercase;margin-bottom:6px;font-weight:700;border-bottom:1px solid var(--border);padding-bottom:3px}
.agcard{display:flex;align-items:center;gap:6px;padding:5px 8px;margin-bottom:3px;background:var(--black-light);border-radius:3px;border:1px solid transparent;cursor:pointer;transition:all .2s}
.agcard:hover{border-color:var(--red)}
.agdot{width:8px;height:8px;border-radius:50%;flex-shrink:0;box-shadow:0 0 6px}
.agcard:hover .agdot{box-shadow:0 0 12px}
.agcard.off .agdot{background:#333!important;box-shadow:none}
.agcard.off{opacity:.3}
.agnam{font-size:10px;font-weight:700;flex:1;color:var(--silver)}
.agcard.off .agnam{color:#333}
.agreg{font-size:8px;color:var(--silver-dim)}
.sec{margin-bottom:8px}
.rrow{display:flex;justify-content:space-between;padding:3px 0;font-size:9px}
.rlbl{color:var(--silver-dim)}
.rval{color:var(--silver);font-weight:700}
.rbar{height:3px;background:rgba(255,0,0,.1);border-radius:1px;margin-top:2px;overflow:hidden}
.rfill{height:100%;background:var(--red);box-shadow:0 0 4px var(--red-glow);transition:width .5s}
.logline{font-size:8px;padding:2px 0;display:flex;gap:6px;opacity:.8}
.lt{color:var(--silver-dim);flex-shrink:0}
.la{font-size:7px;font-weight:700;flex-shrink:0}
#detail-overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.7);z-index:99;display:none}
#detail-overlay.open{display:block}
#detail-panel{position:fixed;z-index:100;pointer-events:auto;display:none;overflow-y:auto;box-shadow:0 0 40px rgba(192,192,192,.1);background:rgba(10,10,10,.98);border:1px solid var(--silver)}@media(min-width:901px){#detail-panel{top:50%;left:50%;transform:translate(-50%,-50%);width:480px;max-height:80vh;border-radius:8px}}@media(max-width:900px){#detail-panel{bottom:0;left:0;width:100%;max-height:70vh;border-top:1px solid var(--silver);border-radius:16px 16px 0 0}}
#detail-panel.open{display:block;animation:panelIn .2s ease-out}
@keyframes panelIn{0%{opacity:0;transform:scale(.92)}100%{opacity:1;transform:scale(1)}}
#dp-header{display:flex;align-items:center;gap:10px;padding:14px 16px;border-bottom:1px solid var(--border)}
#dp-icon{width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:900;flex-shrink:0;background:var(--red);box-shadow:0 0 15px var(--red-glow)}
#dp-title{font-size:14px;font-weight:900;letter-spacing:2px;flex:1;color:var(--silver)}
#dp-close{font-size:22px;cursor:pointer;color:var(--silver-dim);transition:color .2s;padding:6px}
#dp-close:hover{color:#fff}
#dp-body{padding:14px 16px}
.dp-section{margin-bottom:14px}
.dp-label{font-size:8px;letter-spacing:3px;color:var(--red);text-transform:uppercase;margin-bottom:5px;font-weight:700}
.dp-text{font-size:11px;line-height:1.6;color:var(--silver)}
.dp-stats{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.dp-stat{background:var(--black-light);padding:8px 10px;border-radius:4px;border:1px solid var(--border)}
.dp-stat-label{font-size:7px;letter-spacing:1px;color:var(--silver-dim);text-transform:uppercase}
.dp-stat-val{font-size:14px;font-weight:900;color:var(--silver)}
.dp-files{list-style:none;padding:0}
.dp-files li{font-size:9px;padding:3px 6px;margin:2px 0;background:var(--black-light);border-radius:3px;border:1px solid var(--border);color:var(--silver);word-break:break-all;display:flex;justify-content:space-between}
.dp-files li .fname{color:var(--silver);font-weight:700}
.dp-files li .fsize{color:var(--silver-dim);font-size:7px}
#loading{position:fixed;top:0;left:0;width:100%;height:100%;background:var(--black);z-index:9999;display:flex;align-items:center;justify-content:center;flex-direction:column;transition:opacity .5s}
#loading.hide{opacity:0;pointer-events:none}
.ltxt{font-size:12px;letter-spacing:3px;color:var(--red);animation:pulse 1s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.lbar{width:160px;height:2px;background:rgba(255,0,0,.2);margin-top:10px;border-radius:1px;overflow:hidden}
.lprog{height:100%;background:var(--red);transition:width .3s}
::-webkit-scrollbar{width:3px}
::-webkit-scrollbar-thumb{background:rgba(255,0,0,.2);border-radius:1px}
</style>
</head>
<body>
<div id="loading"><div class="ltxt">INITIALIZING NEURAL CORE</div><div class="lbar"><div class="lprog" id="lprog"></div></div></div>
<canvas id="three"></canvas>
<div id="hud">
<div id="topbar">
<div class="logo">AKPANBRAIN</div>
<div class="clock" id="clock"></div>
<div>
<a class="tab" href="https://brain-gules-eight.vercel.app" target="_self">CMD</a>
<a class="tab" id="tab-9router" href="/9router/dashboard" target="_blank">9ROUTER</a>
<a class="tab" id="tab-nullclaw" href="#" onclick="showNullclaw()">NULLCLAW</a>
<a class="tab" href="https://drive.google.com" target="_blank">DRIVE</a>
</div>
</div>
<div id="lpanel"><div class="sec"><div class="stitle">ACTIVE AGENTS</div><div id="agent-list"></div></div></div>
<div id="center"></div>
<div id="rpanel">
<div class="sec"><div class="stitle">BRAIN REGIONS</div><div id="region-list"></div></div>
<div class="sec"><div class="stitle">SYNC STATUS</div><div id="sync-info"></div></div>
</div>
<div id="bottom"><div class="stitle">ACTIVITY FEED</div><div id="activity-feed"></div></div>
</div>
<div id="detail-overlay" onclick="closeDetail()"></div>
<div id="detail-panel">
<div id="dp-header"><div id="dp-icon">🧠</div><div id="dp-title"></div><div id="dp-close" onclick="closeDetail()">✕</div></div>
<div id="dp-body"></div>
</div>

<script type="importmap">{"imports":{"three":"https://unpkg.com/three@0.160.0/build/three.module.js","three/addons/":"https://unpkg.com/three@0.160.0/examples/jsm/"}}</script>
<script type="module">
import * as THREE from 'three';import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
window.THREE=THREE; window.OrbitControls=OrbitControls;

const API='http://localhost:8199';
const TUNNELS=['https://icons-lambda-distances-emotions.trycloudflare.com'];
let apiURL='';
async function findAPI(){if(apiURL)return apiURL;apiURL=API;if(location.hostname!=='localhost'&&location.hostname!=='127.0.0.1'){for(const t of TUNNELS){try{const r=await fetch(t+'/api/agents',{signal:AbortSignal.timeout(3000)});if(r.ok){apiURL=t;break}}catch{}}}return apiURL;}
const RCOL={semantic:'#C0C0C0',graph:'#808080',episodic:'#FF0000',working:'#A0A0A0',procedural:'#FF3333',sensory:'#D0D0D0'};
const RPOS={semantic:{x:0,y:.2,z:-.6,r:.35},graph:{x:0,y:-.1,z:0,r:.25},episodic:{x:.5,y:0,z:.1,r:.27},working:{x:0,y:.5,z:.3,r:.29},procedural:{x:0,y:.6,z:-.05,r:.22},sensory:{x:0,y:.55,z:.4,r:.21}};
let scene,camera,renderer,controls,raycaster,mouse,agents={},regions={},fileNodes={},activity=[],logs=[];
let agentData={},fileData={},clock=new THREE.Clock();
let fileMeshes=[],neuronMeshes=[];
function init3D(){
  scene=new THREE.Scene();scene.fog=new THREE.FogExp2(0x0a0a0a,.1);
  camera=new THREE.PerspectiveCamera(50,innerWidth/innerHeight,.01,200);
  camera.position.set(0,.5,4);
  renderer=new THREE.WebGLRenderer({canvas:document.getElementById('three'),antialias:true,alpha:true,preserveDrawingBuffer:true});
  renderer.setSize(innerWidth,innerHeight);renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.2;
  controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.08;controls.rotateSpeed=.6;controls.zoomSpeed=1.2;controls.minDistance=1;controls.maxDistance=15;controls.autoRotate=true;controls.autoRotateSpeed=.3;
  raycaster=new THREE.Raycaster();mouse=new THREE.Vector2();
  const amb=new THREE.AmbientLight(0x221111,.6);scene.add(amb);
  const p1=new THREE.PointLight(0xFF0000,.6,20);p1.position.set(2,2,2);scene.add(p1);
  const p2=new THREE.PointLight(0x808080,.3,20);p2.position.set(-2,2,-2);scene.add(p2);
  buildBrain();buildRegions();buildFileNodes();setupInteraction();
  window.addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight)});
  animate();
  setTimeout(()=>document.getElementById('loading').classList.add('hide'),1500);
}
function buildBrain(){
  const group=new THREE.Group();
  function hemi(flipX){
    const geo=new THREE.SphereGeometry(1,64,64);
    const mat=new THREE.MeshPhongMaterial({color:0x1a0a0a,transparent:true,opacity:.35,shininess:60,specular:0xFF0000,side:THREE.DoubleSide,depthWrite:false});
    const mesh=new THREE.Mesh(geo,mat);
    mesh.position.x=flipX?.05:-.05;
    mesh.renderOrder=1;
    return mesh;
  }
  group.add(hemi(false));group.add(hemi(true));
  const stem=new THREE.Mesh(new THREE.CylinderGeometry(.12,.08,.6,16),new THREE.MeshPhongMaterial({color:0x111111,transparent:true,opacity:.4,side:THREE.DoubleSide}));
  stem.position.set(0,-.9,-.2);stem.rotation.x=.3;group.add(stem);
  const cb=new THREE.Mesh(new THREE.SphereGeometry(.3,32,32),new THREE.MeshPhongMaterial({color:0x111111,transparent:true,opacity:.4}));cb.position.set(0,-.6,-.55);group.add(cb);
  scene.add(group);
}
function buildRegions(){
  Object.entries(RPOS).forEach(([name,rc])=>{
    const col=new THREE.Color(RCOL[name]);
    const geo=new THREE.SphereGeometry(rc.r*.15,8,8);
    const mat=new THREE.MeshBasicMaterial({color:col,transparent:true,opacity:.5});
    const mesh=new THREE.Mesh(geo,mat);mesh.position.set(rc.x,rc.y,rc.z);
    mesh.userData={type:'region',name};scene.add(mesh);
  });
}
async function buildFileNodes(){
  try{await findAPI();const r=await fetch(apiURL+'/api/files');const data=await r.json();
    Object.entries(data).forEach(([region,files])=>{
      if(!files.length)return;const rc=RPOS[region]||RPOS.semantic;
      files.forEach((f,i)=>{
        const ext=(f.name||'').split('.').pop()||'';
        const col=ext==='py'?'#FF0000':ext==='json'?'#C0C0C0':ext==='md'?'#D0D0D0':ext==='db'?'#404040':ext==='html'?'#808080':'#505050';
        const geo=new THREE.BoxGeometry(.02,.02,.02);
        const mat=new THREE.MeshBasicMaterial({color:col});
        const mesh=new THREE.Mesh(geo,mat);
        const a=i*2.5;const r2=rc.r*.3+(Math.random()-.5)*.1;
        mesh.position.set(rc.x+Math.cos(a)*r2,rc.y+Math.sin(a)*r2,rc.z+Math.random()*.1-.05);
        mesh.userData={type:'file',name:f.name,path:f.path,size:f.size};scene.add(mesh);fileMeshes.push(mesh);
      });
    });
  }catch(e){console.error('File nodes error:',e)}
}
function setupInteraction(){
  renderer.domElement.addEventListener('pointerdown',e=>{
    mouse.x=(e.clientX/innerWidth)*2-1;mouse.y=-(e.clientY/innerHeight)*2+1;
    raycaster.setFromCamera(mouse,camera);
    const hits=raycaster.intersectObjects(fileMeshes);if(hits.length){showFileDetail(hits[0].object.userData);}
  });
}
async function refresh(){
  try{await findAPI();const[a,b,s]=await Promise.all([fetch(apiURL+'/api/agents').catch(()=>null),fetch(apiURL+'/api/brain').catch(()=>null),fetch(apiURL+'/api/sync').catch(()=>null)]);
    if(a){const d=await a.json();updateAgents(d)}
    if(b){const d=await b.json();updateRegions(d)}
    if(s){const d=await s.json();document.getElementById('sync-info').innerHTML='<div class="rrow"><span class="rlbl">Status</span><span class="rval" style="color:'+(d.status==='connected'?'#00ff00':'#FF0000')+'">'+d.status+'</span></div><div class="rrow"><span class="rlbl">Last Sync</span><span class="rval">'+d.last_sync+'</span></div>'}
    const act=await fetch(apiURL+'/api/activity').catch(()=>null);if(act){const d=await act.json();d.forEach(a=>addLog(a.action+': '+a.target,a.agent))}
  }catch(e){console.error('refresh error:',e)}
}
function updateAgents(d){
  let h='';const sorted=Object.entries(d).sort((a,b)=>{const o={active:0,inactive:1,dormant:2};return(o[a[1].status]||3)-(o[b[1].status]||3)});
  sorted.forEach(([name,a])=>{
    const off=a.status!=='active'?' off':'';
    h+=`<div class="agcard${off}" onclick="showAgentDetail('${name}')"><div class="agdot" style="background:${a.color||'#333'}"></div><div class="agnam">${name}</div><div class="agreg">${a.region||'unknown'}</div></div>`;
  });
  document.getElementById('agent-list').innerHTML=h;
}
function updateRegions(d){
  let h='';Object.entries(d).forEach(([k,v])=>{
    h+=`<div class="sec" onclick="showRegionDetail('${k}')" style="cursor:pointer"><div class="rrow"><span class="rlbl" style="color:${v.color}">${v.name}</span><span class="rval">${v.file_count||0}</span></div><div class="rbar"><div class="rfill" style="width:${Math.min(v.file_count*5,100)}%;background:${v.color}"></div></div></div>`;
  });
  document.getElementById('region-list').innerHTML=h;
}
function addLog(msg,agent){if(logs.some(l=>l.msg===msg&&l.agent===agent))return;logs.unshift({t:new Date().toTimeString().split(' ')[0],msg,agent});if(logs.length>35)logs.length=35;document.getElementById('activity-feed').innerHTML=logs.map(l=>`<div class="logline"><span class="lt">${l.t}</span><span class="la" style="color:${RCOL[agent]||'#fff'}">${agent}</span>${l.msg}</div>`).join('');}
function showAgentDetail(name){const col=agentData[name]?.color||'#333';let h='<div class="dp-section"><div class="dp-label">Status</div><div class="dp-text">'+name+'</div></div>';openDetail(h,'A',''+name.toUpperCase(),'#333',name);}
function showRegionDetail(name){const col=RCOL[name]||'#333';let h='<div class="dp-section"><div class="dp-label">Region</div><div class="dp-text">'+name+'</div></div>';openDetail(h,'R','REGION','#333',name);}
function showFileDetail(f){let h='<div class="dp-section"><div class="dp-label">File</div><div class="dp-text">'+f.name+'</div></div><div class="dp-section"><div class="dp-label">Size</div><div class="dp-text">'+f.size+' bytes</div></div>';openDetail(h,'F','FILE','#333',f.name);}
function showNullclaw(){let h='<div class="dp-section"><div class="dp-label">Nullclaw Router</div><div class="dp-text">AI Router / load balancer. Routes LLM requests between multiple providers. Shares the same process as 9Router on localhost:20128.</div></div>';openDetail(h,'N','NULLCLAW','#333','Router Status');}
function openDetail(html,icon,title,statusCol,statusText){document.getElementById('dp-icon').textContent=icon;document.getElementById('dp-title').textContent=title;document.getElementById('dp-icon').style.background=statusCol;document.getElementById('dp-body').innerHTML=document.getElementById('dp-body').innerHTML+html;document.getElementById('detail-panel').classList.add('open');document.getElementById('detail-overlay').classList.add('open');}
window.closeDetail=function(){document.getElementById('detail-panel').classList.remove('open');document.getElementById('detail-overlay').classList.remove('open');};
function animate(){requestAnimationFrame(animate);const t=clock.getElapsedTime();controls.update();fileMeshes.forEach((m,i)=>{m.rotation.x+=.01;m.rotation.y+=.01;m.position.y+=Math.sin(t*2+i)*.001;});renderer.render(scene,camera);}
function boot(){init3D();refresh();setInterval(refresh,5000);document.getElementById('clock').textContent=new Date().toTimeString().split(' ')[0];setInterval(()=>document.getElementById('clock').textContent=new Date().toTimeString().split(' ')[0],1000);let p=0;const pi=setInterval(()=>{p+=15;document.getElementById('lprog').style.width=p+'%';if(p>=100)clearInterval(pi)},100);}
window.showAgentDetail=showAgentDetail;window.showRegionDetail=showRegionDetail;window.showFileDetail=showFileDetail;window.showNullclaw=showNullclaw;window.closeDetail=closeDetail;
try{boot()}catch(e){console.error(e);}
</script>
</body>
</html>'''

os.makedirs('/config/brain/dashboard', exist_ok=True)
with open('/config/brain/dashboard/index.html', 'w') as f:
    f.write(HTML)
print(f"Wrote {len(HTML)} bytes to index.html")
