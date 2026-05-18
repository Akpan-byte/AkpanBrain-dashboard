#!/usr/bin/env python3
"""Generate the complete AkpanBrain v3 dashboard — RED/BLACK/SILVER CHROME"""
import json

data = json.load(open('/tmp/embedded_data.json'))
all_agents = json.load(open('/tmp/all_agents.json'))
real_files = [f for f in data["local_files"] if not f["path"].startswith(".git/")]

agents_json = json.dumps(all_agents)
files_json = json.dumps(real_files)
brain_json = json.dumps(data["brain"])

TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=5,user-scalable=yes">
<title>AKPANBRAIN — Neural Command</title>
<style>
:root{--red:#FF0000;--red-dim:#800000;--red-glow:rgba(255,0,0,.25);--chrome:#C0C0C0;--chrome-dim:#707070;--chrome-dark:#404040;--black:#0a0a0a;--black-mid:#111;--black-light:#1a1a1a;--border:rgba(192,192,192,.12)}
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;overflow:hidden}
body{background:var(--black);color:var(--chrome);font-family:'Courier New',monospace}
#cv{position:fixed;inset:0;z-index:1;touch-action:none}
#hud{position:fixed;inset:0;z-index:10;pointer-events:none;display:grid;grid-template-columns:220px 1fr 220px;grid-template-rows:38px 1fr 100px;gap:0}
@media(max-width:900px){#hud{grid-template-columns:1fr;grid-template-rows:34px auto 1fr auto 80px}#lp{max-height:140px;overflow-x:auto;border-right:none;border-bottom:1px solid var(--border)}#rp{max-height:140px;border-left:none;border-top:1px solid var(--border)}#bt{max-height:80px}}
#hd{grid-column:1/-1;display:flex;align-items:center;padding:0 10px;border-bottom:1px solid var(--border);background:rgba(10,10,10,.96);pointer-events:auto;gap:8px}
.logo{font-size:11px;font-weight:900;letter-spacing:4px;color:var(--red);text-shadow:0 0 12px var(--red-glow);white-space:nowrap}
.clk{font-size:9px;color:var(--chrome-dim);letter-spacing:2px;flex:1;text-align:center}
.tbtn{padding:3px 8px;font-size:7px;letter-spacing:1px;border:1px solid var(--chrome-dark);border-radius:2px;cursor:pointer;color:var(--chrome-dim);text-transform:uppercase;text-decoration:none;pointer-events:auto;transition:all .15s;background:transparent}
.tbtn:hover{border-color:var(--red);color:var(--red);text-shadow:0 0 6px var(--red-glow)}
#lp{grid-row:2;padding:6px;overflow-y:auto;pointer-events:auto;background:rgba(10,10,10,.92);border-right:1px solid var(--border)}
#rp{grid-row:2;padding:6px;overflow-y:auto;pointer-events:auto;background:rgba(10,10,10,.92);border-left:1px solid var(--border)}
#bt{grid-column:1/-1;padding:6px 10px;overflow-y:auto;pointer-events:auto;border-top:1px solid var(--border);background:rgba(10,10,10,.92)}
.stit{font-size:8px;letter-spacing:3px;color:var(--red);text-transform:uppercase;margin-bottom:5px;font-weight:700;padding-bottom:3px;border-bottom:1px solid var(--border)}
.agc{display:flex;align-items:center;gap:5px;padding:4px 6px;margin-bottom:2px;background:var(--black-light);border-radius:2px;border:1px solid transparent;cursor:pointer;transition:all .15s}
.agc:hover{border-color:var(--red)}
.agc.off{opacity:.25}
.adot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.agc:not(.off) .adot{box-shadow:0 0 6px currentColor}
.anm{font-size:9px;font-weight:700;flex:1;color:var(--chrome)}
.agc.off .anm{color:var(--chrome-dark)}
.ast{font-size:7px;padding:1px 4px;border-radius:1px;letter-spacing:1px}
.ast.on{color:var(--red);border:1px solid var(--red-dim)}
.ast.off{color:var(--chrome-dark);border:1px solid var(--chrome-dark)}
.rrow{display:flex;justify-content:space-between;padding:2px 0;font-size:8px;cursor:pointer}
.rrow:hover .rlbl{color:var(--red)}
.rlbl{color:var(--chrome-dim);transition:color .15s}
.rval{color:var(--chrome);font-weight:700}
.rbar{height:2px;background:rgba(255,0,0,.08);border-radius:1px;margin-top:1px;overflow:hidden}
.rfill{height:100%;background:var(--red);box-shadow:0 0 4px var(--red-glow);transition:width .5s}
.ll{font-size:7px;padding:1px 0;display:flex;gap:5px;opacity:.7}
.lt2{color:var(--chrome-dark);flex-shrink:0;min-width:52px}
.la2{font-weight:700;flex-shrink:0;min-width:60px;color:var(--red)}
#overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:90;display:none;pointer-events:auto}
#overlay.open{display:block}
#dp{position:fixed;z-index:100;pointer-events:auto;display:none;overflow-y:auto;background:rgba(10,10,10,.98);border:1px solid var(--chrome-dark);box-shadow:0 0 40px rgba(255,0,0,.08)}
#dp.open{display:block;animation:slideIn .2s ease-out}
@media(min-width:901px){#dp{top:50%;left:50%;transform:translate(-50%,-50%);width:440px;max-height:80vh;border-radius:6px}}
@media(max-width:900px){#dp{bottom:0;left:0;width:100%;max-height:70vh;border-radius:12px 12px 0 0;border-bottom:none}}
@keyframes slideIn{0%{opacity:0;transform:translateY(20px)}100%{opacity:1;transform:translateY(0)}}
@media(min-width:901px){@keyframes slideIn{0%{opacity:0;transform:translate(-50%,-50%) scale(.95)}100%{opacity:1;transform:translate(-50%,-50%) scale(1)}}}
#dph{display:flex;align-items:center;gap:10px;padding:12px 14px;border-bottom:1px solid var(--border)}
#dpi{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:900;flex-shrink:0;background:var(--red);color:var(--black);box-shadow:0 0 12px var(--red-glow)}
#dpt{font-size:13px;font-weight:900;letter-spacing:2px;flex:1;color:var(--chrome)}
#dpx{font-size:20px;cursor:pointer;color:var(--chrome-dim);padding:4px 8px;transition:color .15s}
#dpx:hover{color:var(--red)}
#dpb{padding:12px 14px}
.ds{margin-bottom:12px}
.dl{font-size:7px;letter-spacing:3px;color:var(--red);text-transform:uppercase;margin-bottom:4px;font-weight:700}
.dt{font-size:10px;line-height:1.5;color:var(--chrome)}
.dsg{display:grid;grid-template-columns:1fr 1fr;gap:4px}
.dsi{background:var(--black-light);padding:6px 8px;border-radius:3px;border:1px solid var(--border)}
.dsil{font-size:6px;letter-spacing:1px;color:var(--chrome-dark);text-transform:uppercase}
.dsiv{font-size:13px;font-weight:900;color:var(--chrome)}
.dfl{list-style:none;padding:0}
.dfl li{font-size:8px;padding:2px 5px;margin:1px 0;background:var(--black-light);border-radius:2px;border:1px solid var(--border);color:var(--chrome-dim);word-break:break-all;display:flex;justify-content:space-between}
.dfl .fn{color:var(--chrome);font-weight:700}
.dfl .fs{color:var(--chrome-dark);font-size:7px}
#ld{position:fixed;inset:0;background:var(--black);z-index:9999;display:flex;align-items:center;justify-content:center;flex-direction:column;transition:opacity .5s}
#ld.hide{opacity:0;pointer-events:none}
.ldt{font-size:11px;letter-spacing:3px;color:var(--red);animation:pulse 1s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.ldb{width:120px;height:2px;background:rgba(255,0,0,.15);margin-top:8px;border-radius:1px;overflow:hidden}
.ldf{height:100%;background:var(--red);transition:width .3s;box-shadow:0 0 6px var(--red-glow)}
::-webkit-scrollbar{width:3px;height:3px}
::-webkit-scrollbar-thumb{background:rgba(255,0,0,.2);border-radius:1px}
::-webkit-scrollbar-track{background:transparent}
</style>
</head>
<body>
<div id="ld"><div class="ldt">AKPANBRAIN NEURAL CORE</div><div class="ldb"><div class="ldf" id="ldf"></div></div></div>
<canvas id="cv"></canvas>
<div id="hud">
<div id="hd">
<div class="logo">AKPANBRAIN</div>
<div class="clk" id="clk"></div>
<div id="cst"></div>
<a class="tbtn" href="/" onclick="location.reload()">REF</a>
<a class="tbtn" id="tb9" href="http://localhost:20128" target="_blank">9R</a>
<a class="tbtn" onclick="showNullclaw()">NULL</a>
<a class="tbtn" href="https://drive.google.com" target="_blank">DRIVE</a>
</div>
<div id="lp"><div class="stit">AGENTS</div><div id="al"></div></div>
<div id="rp">
<div class="stit">BRAIN REGIONS</div><div id="rl"></div>
<div class="stit" style="margin-top:8px">SYNC</div><div id="sl"></div>
<div class="stit" style="margin-top:8px">FILES</div><div id="fl"></div>
</div>
<div id="bt"><div class="stit">ACTIVITY</div><div id="af"></div></div>
</div>
<div id="overlay" onclick="closeDP()"></div>
<div id="dp"><div id="dph"><div id="dpi">A</div><div id="dpt"></div><div id="dpx" onclick="closeDP()">✕</div></div><div id="dpb"></div></div>

<script type="importmap">{"imports":{"three":"https://unpkg.com/three@0.160.0/build/three.module.js","three/addons/":"https://unpkg.com/three@0.160.0/examples/jsm/"}}</script>
<script type="module">
import*as THREE from'three';
import{OrbitControls}from'three/addons/controls/OrbitControls.js';

// ─── EMBEDDED FALLBACK DATA ───
const EA=' + agents_json + ';
const EF=' + files_json + ';
const EB=' + brain_json + ';
const LOCAL_API='http://localhost:8199';
const TUNNELS=['https://clinic-reason-mia-alike.trycloudflare.com'];

// ─── RED/BLACK/SILVER CHROME ───
const C={red:0xFF0000,redDim:0x800000,chrome:0xC0C0C0,chromeDim:0x707070,chromeDark:0x404040,black:0x0a0a0a};
const RCOL={semantic:'#C0C0C0',graph:'#808080',episodic:'#FF0000',working:'#A0A0A0',procedural:'#FF3333',sensory:'#D0D0D0'};
const RPOS={semantic:{x:0,y:.2,z:-.6,r:.35},graph:{x:0,y:-.1,z:0,r:.25},episodic:{x:.5,y:0,z:.1,r:.27},working:{x:0,y:.5,z:.3,r:.29},procedural:{x:0,y:.6,z:-.05,r:.22},sensory:{x:0,y:.55,z:.4,r:.21}};

let scene,camera,renderer,controls,raycaster,mouse=new THREE.Vector2();
let agentMeshes={},fileMeshes=[],regionMeshes={},logs=[];
let clock=new THREE.Clock(),apiURL='',connected=false;
let curA={...EA},curF=[...EF],curB={...EB};

// ─── API DISCOVERY ───
async function findAPI(){
  if(apiURL)return apiURL;
  try{const r=await fetch(LOCAL_API+'/api/agents',{signal:AbortSignal.timeout(3000)});if(r.ok){apiURL=LOCAL_API;connected=true;return apiURL}}catch{}
  for(const t of TUNNELS){try{const r=await fetch(t+'/api/agents',{signal:AbortSignal.timeout(5000)});if(r.ok){apiURL=t;connected=true;return t}}catch{}}
  connected=false;return null;
}

// ─── 3D SCENE ───
function init3D(){
  scene=new THREE.Scene();scene.fog=new THREE.FogExp2(C.black,.08);
  camera=new THREE.PerspectiveCamera(50,innerWidth/innerHeight,.01,200);camera.position.set(0,.4,3.5);
  renderer=new THREE.WebGLRenderer({canvas:document.getElementById('cv'),antialias:true,alpha:false,preserveDrawingBuffer:true});
  renderer.setSize(innerWidth,innerHeight);renderer.setPixelRatio(Math.min(devicePixelRatio,2));
  renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1;renderer.setClearColor(C.black,1);
  controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.08;
  controls.rotateSpeed=.5;controls.zoomSpeed=1;controls.minDistance=1.2;controls.maxDistance=12;
  controls.autoRotate=true;controls.autoRotateSpeed=.25;
  raycaster=new THREE.Raycaster();
  // LIGHTS — red/silver only
  scene.add(new THREE.AmbientLight(0x1a0808,.8));
  const rl=new THREE.PointLight(C.red,.5,25);rl.position.set(3,3,2);scene.add(rl);
  const sl=new THREE.PointLight(C.chrome,.2,25);sl.position.set(-3,2,-3);scene.add(sl);
  const rl2=new THREE.PointLight(C.redDim,.3,15);rl2.position.set(0,-3,0);scene.add(rl2);
  buildShell();buildRegions();buildFiles();buildAgents();setupInput();
  window.addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight)});
  animate();setTimeout(()=>document.getElementById('ld').classList.add('hide'),1200);
}

// ─── BRAIN SHELL ───
function buildShell(){
  const g=new THREE.Group();
  const hGeo=new THREE.SphereGeometry(.95,48,48,0,Math.PI);
  const hMat=new THREE.MeshPhongMaterial({color:0x0d0404,transparent:true,opacity:.18,shininess:80,specular:C.redDim,side:THREE.DoubleSide,depthWrite:false});
  const wMat=new THREE.MeshBasicMaterial({color:C.chromeDark,wireframe:true,transparent:true,opacity:.06,side:THREE.DoubleSide,depthWrite:false});
  const lh=new THREE.Mesh(hGeo,hMat);g.add(lh);const lhw=new THREE.Mesh(hGeo,wMat);g.add(lhw);
  const rh=new THREE.Mesh(hGeo,hMat);rh.rotation.y=Math.PI;g.add(rh);const rhw=new THREE.Mesh(hGeo,wMat);rhw.rotation.y=Math.PI;g.add(rhw);
  const cb=new THREE.Mesh(new THREE.SphereGeometry(.28,24,24),hMat.clone());cb.position.set(0,-.55,-.5);g.add(cb);
  const cw=new THREE.Mesh(new THREE.SphereGeometry(.28,24,24),wMat.clone());cw.position.set(0,-.55,-.5);g.add(cw);
  const st=new THREE.Mesh(new THREE.CylinderGeometry(.08,.06,.5,12),hMat.clone());st.position.set(0,-.85,-.25);st.rotation.x=.3;g.add(st);
  scene.add(g);
}

// ─── REGION CORES ───
function buildRegions(){
  Object.entries(RPOS).forEach(([name,rc])=>{
    const col=new THREE.Color(RCOL[name]||'#808080');
    const geo=new THREE.IcosahedronGeometry(rc.r*.12,1);
    const mat=new THREE.MeshPhongMaterial({color:col,emissive:col,emissiveIntensity:.3,transparent:true,opacity:.6,shininess:40,specular:C.chrome});
    const mesh=new THREE.Mesh(geo,mat);mesh.position.set(rc.x,rc.y,rc.z);mesh.userData={type:'region',name};scene.add(mesh);regionMeshes[name]=mesh;
    const glow=new THREE.Mesh(new THREE.SphereGeometry(rc.r*.18,16,16),new THREE.MeshBasicMaterial({color:col,transparent:true,opacity:.08,side:THREE.BackSide,depthWrite:false}));glow.position.copy(mesh.position);scene.add(glow);
    for(let i=0;i<3;i++){const lg=new THREE.BufferGeometry();const a=Math.random()*Math.PI*2;const end=new THREE.Vector3(rc.x+Math.cos(a)*rc.r*.4,rc.y+Math.sin(a)*rc.r*.4,rc.z+(Math.random()-.5)*.1);lg.setFromPoints([mesh.position,end]);scene.add(new THREE.Line(lg,new THREE.LineBasicMaterial({color:col,transparent:true,opacity:.15})));}
  });
}

// ─── FILE NODES ───
function buildFiles(){
  fileMeshes.forEach(m=>scene.remove(m));fileMeshes=[];
  curF.forEach((f,i)=>{
    const path=f.path||f.name||'';const ext=path.split('.').pop()||'';
    const col=ext==='py'?C.red:ext==='json'||ext==='db'||ext==='index'?C.chrome:ext==='html'||ext==='md'?C.chromeDim:ext==='sh'?C.redDim:C.chromeDark;
    const sz=Math.max(.008,Math.min(.025,Math.sqrt((f.size||100)/5000)*.012));
    const geo=new THREE.OctahedronGeometry(sz,0);
    const mat=new THREE.MeshPhongMaterial({color:col,emissive:col,emissiveIntensity:.2,shininess:60,specular:C.chrome});
    const mesh=new THREE.Mesh(geo,mat);
    let region='semantic';
    if(path.includes('graph'))region='graph';else if(path.includes('episodic')||path.includes('memory')||path.includes('.db'))region='episodic';
    else if(path.includes('working')||path.includes('cache')||path.includes('sync'))region='working';
    else if(path.includes('procedural')||path.includes('skill')||path.includes('api_server'))region='procedural';
    else if(path.includes('sensory')||path.includes('watch'))region='sensory';
    else if(path.includes('dashboard'))region='semantic';else if(path.endsWith('.py'))region='procedural';
    const rc=RPOS[region]||RPOS.semantic;const a=(i/curF.length)*Math.PI*2;const r2=rc.r*.25+Math.random()*.15;
    mesh.position.set(rc.x+Math.cos(a)*r2,rc.y+Math.sin(a)*r2+(Math.random()-.5)*.1,rc.z+(Math.random()-.5)*.15);
    mesh.userData={type:'file',name:path.split('/').pop(),path,size:f.size||0,region};scene.add(mesh);fileMeshes.push(mesh);
  });
}

// ─── AGENT AVATARS ───
function buildAgents(){
  Object.values(agentMeshes).forEach(m=>scene.remove(m.group));agentMeshes={};
  Object.entries(curA).forEach(([name,a],i)=>{
    const col=new THREE.Color(a.color||'#808080');const rc=RPOS[a.region||'semantic']||RPOS.semantic;
    const grp=new THREE.Group();
    const core=new THREE.Mesh(new THREE.SphereGeometry(.025,12,12),new THREE.MeshPhongMaterial({color:col,emissive:col,emissiveIntensity:a.status==='active'?.5:.05,transparent:a.status!=='active',opacity:a.status==='active'?1:.3,shininess:80,specular:C.chrome}));
    grp.add(core);
    if(a.status==='active'){const ring=new THREE.Mesh(new THREE.TorusGeometry(.04,.003,8,32),new THREE.MeshBasicMaterial({color:col,transparent:true,opacity:.4}));ring.rotation.x=Math.PI/2;grp.add(ring);}
    const angle=i*0.52;grp.position.set(rc.x+Math.cos(angle)*rc.r*.5,rc.y+rc.r*.6,rc.z+Math.sin(angle)*rc.r*.3);
    grp.userData={name,angle:i*0.52,region:a.region||'semantic',baseY:rc.y+rc.r*.6,baseX:rc.x,baseZ:rc.z,orbitR:rc.r*.5};
    scene.add(grp);agentMeshes[name]=grp;
  });
}

// ─── INPUT ───
function setupInput(){
  renderer.domElement.addEventListener('pointerdown',e=>{
    const rect=renderer.domElement.getBoundingClientRect();
    mouse.x=((e.clientX-rect.left)/rect.width)*2-1;mouse.y=-((e.clientY-rect.top)/rect.height)*2+1;
    raycaster.setFromCamera(mouse,camera);
    const hits=raycaster.intersectObjects([...fileMeshes,...Object.values(regionMeshes)],true);
    if(hits.length){const ud=hits[0].object.userData;if(ud.type==='file')showFileDetail(ud);else if(ud.type==='region')showRegionDetail(ud.name);}
  });
  renderer.domElement.addEventListener('dblclick',e=>{
    const rect=renderer.domElement.getBoundingClientRect();
    mouse.x=((e.clientX-rect.left)/rect.width)*2-1;mouse.y=-((e.clientY-rect.top)/rect.height)*2+1;
    raycaster.setFromCamera(mouse,camera);
    for(const[name,grp]of Object.entries(agentMeshes)){if(raycaster.intersectObjects(grp.children,true).length){showAgentDetail(name);return;}}
  });
}

// ─── DATA REFRESH ───
async function refresh(){
  const url=await findAPI();
  if(!url){updateUI();return;}
  try{
    const[a,b,f,s,act]=await Promise.all([
      fetch(url+'/api/agents',{signal:AbortSignal.timeout(4000)}).catch(()=>null),
      fetch(url+'/api/brain',{signal:AbortSignal.timeout(4000)}).catch(()=>null),
      fetch(url+'/api/files',{signal:AbortSignal.timeout(4000)}).catch(()=>null),
      fetch(url+'/api/sync',{signal:AbortSignal.timeout(4000)}).catch(()=>null),
      fetch(url+'/api/activity',{signal:AbortSignal.timeout(4000)}).catch(()=>null)
    ]);
    if(a){const d=await a.json();Object.entries(d).forEach(([k,v])=>{curA[k]={...curA[k],...v,status:'active'}});Object.keys(curA).forEach(k=>{if(!d[k])curA[k].status='inactive'});}
    if(b)curB=await b.json();
    if(f){const d=await f.json();curF=Object.values(d).flat();buildFiles();}
    if(s){const d=await s.json();document.getElementById('sl').innerHTML='<div class="rrow"><span class="rlbl">Status</span><span class="rval" style="color:'+(d.status==='connected'?'var(--chrome)':'var(--red)')+'">'+d.status+'</span></div>';}
    if(act){const d=await act.json();d.forEach(x=>addLog(x.action+': '+x.target,x.agent))}
    connected=true;
  }catch(e){connected=false;}
  updateUI();
}

function updateUI(){
  document.getElementById('cst').innerHTML=connected?'<span class="tbtn" style="border-color:var(--red);color:var(--red)">● LIVE</span>':'<span class="tbtn" style="border-color:var(--chrome-dark);color:var(--chrome-dark)">○ LOCAL</span>';
  let h='';const sorted=Object.entries(curA).sort((a,b)=>{const o={active:0,inactive:1};return(o[a[1].status]??2)-(o[b[1].status]??2)});
  sorted.forEach(([name,a])=>{const off=a.status!=='active'?' off':'';const stc=a.status==='active'?' on':' off';
    h+='<div class="agc'+off+'" onclick="showAgentDetail(\\''+name+'\\')"><div class="adot" style="color:'+a.color+';background:'+a.color+'"></div><div class="anm">'+name+'</div><span class="ast'+stc+'">'+a.status+'</span></div>';});
  document.getElementById('al').innerHTML=h;
  let rh='';Object.entries(curB).forEach(([k,v])=>{rh+='<div class="rrow" onclick="showRegionDetail(\\''+k+'\\')"><span class="rlbl" style="color:'+(v.color||'#808080')+'">'+(v.name||k)+'</span><span class="rval">'+(v.file_count||0)+'f</span></div><div class="rbar"><div class="rfill" style="width:'+Math.min((v.file_count||0)*8,100)+'%;background:'+(v.color||'#808080')+'"></div></div>';});
  document.getElementById('rl').innerHTML=rh;
  document.getElementById('fl').innerHTML='<div class="rrow"><span class="rlbl">Local</span><span class="rval">'+curF.length+' files</span></div>';
  buildAgents();
}

function addLog(msg,agent){
  if(logs.some(l=>l.msg===msg&&l.agent===agent))return;
  logs.unshift({t:new Date().toTimeString().split(' ')[0],msg,agent});if(logs.length>40)logs.length=40;
  document.getElementById('af').innerHTML=logs.map(l=>'<div class="ll"><span class="lt2">'+l.t+'</span><span class="la2">'+l.agent+'</span><span>'+l.msg+'</span></div>').join('');
}

// ─── DETAIL PANELS ───
window.showAgentDetail=function(name){
  const a=curA[name]||{};const region=a.region||'unknown';const isActive=a.status==='active';
  let h='<div class="ds"><div class="dl">AGENT</div><div class="dt">'+name+'</div></div>';
  h+='<div class="ds"><div class="dl">STATUS</div><div class="dt" style="color:'+(isActive?'var(--red)':'var(--chrome-dim)')+'">'+a.status+'</div></div>';
  if(a.desc)h+='<div class="ds"><div class="dl">ROLE</div><div class="dt">'+a.desc+'</div></div>';
  if(a.type)h+='<div class="ds"><div class="dl">TYPE</div><div class="dt">'+a.type+'</div></div>';
  h+='<div class="ds"><div class="dl">REGION</div><div class="dt">'+region+'</div></div>';
  if(isActive){h+='<div class="ds"><div class="dl">METRICS</div><div class="dsg"><div class="dsi"><div class="dsil">PID</div><div class="dsiv">'+(a.pid||'?')+'</div></div><div class="dsi"><div class="dsil">CPU</div><div class="dsiv">'+(a.cpu||'0')+'%</div></div><div class="dsi"><div class="dsil">MEM</div><div class="dsiv">'+(a.mem||'0')+'%</div></div><div class="dsi"><div class="dsil">DETECTED</div><div class="dsiv">'+(a.detected_by||'scan')+'</div></div></div></div>';}
  openDP(h,'A',name.toUpperCase(),a.color||'#404040');
};

window.showRegionDetail=function(name){
  const b=curB[name]||{};let h='<div class="ds"><div class="dl">REGION</div><div class="dt">'+(b.name||name)+'</div></div>';
  if(b.description)h+='<div class="ds"><div class="dl">FUNCTION</div><div class="dt">'+b.description+'</div></div>';
  h+='<div class="ds"><div class="dl">STATS</div><div class="dsg"><div class="dsi"><div class="dsil">FILES</div><div class="dsiv">'+(b.file_count||0)+'</div></div><div class="dsi"><div class="dsil">VECTORS</div><div class="dsiv">'+(b.vector_count||0)+'</div></div><div class="dsi"><div class="dsil">NODES</div><div class="dsiv">'+(b.node_count||0)+'</div></div><div class="dsi"><div class="dsil">KEYS</div><div class="dsiv">'+(b.key_count||0)+'</div></div></div></div>';
  const rAgents=Object.entries(curA).filter(([k,v])=>v.region===name&&v.status==='active');
  if(rAgents.length)h+='<div class="ds"><div class="dl">ACTIVE AGENTS</div><div class="dt">'+rAgents.map(([k])=>k).join(', ')+'</div></div>';
  openDP(h,'R',(b.name||name).toUpperCase(),RCOL[name]||'#808080');
};

window.showFileDetail=function(f){
  let h='<div class="ds"><div class="dl">FILE</div><div class="dt">'+(f.name||'?')+'</div></div>';
  h+='<div class="ds"><div class="dl">PATH</div><div class="dt">'+(f.path||'?')+'</div></div>';
  h+='<div class="ds"><div class="dl">SIZE</div><div class="dt">'+((f.size||0)>1024?((f.size/1024)|0)+'KB':f.size+'B')+'</div></div>';
  h+='<div class="ds"><div class="dl">REGION</div><div class="dt">'+(f.region||'unknown')+'</div></div>';
  openDP(h,'F',(f.name||'FILE').toUpperCase(),f.region?RCOL[f.region]||'#808080':'#404040');
};

window.showNullclaw=function(){
  let h='<div class="ds"><div class="dl">NULLCLAW / 9ROUTER</div><div class="dt">AI routing proxy that load-balances LLM requests across providers (Groq, NVIDIA, Gemini). Runs on localhost:20128. Part of episodic region — routes queries between brain subsystems.</div></div>';
  h+='<div class="ds"><div class="dl">STATUS</div><div class="dt">'+(curA.jcode?.status==='active'?'ACTIVE':'INACTIVE')+'</div></div>';
  openDP(h,'N','NULLCLAW','#FF0000');
};

function openDP(html,icon,title,color){
  document.getElementById('dpi').textContent=icon;document.getElementById('dpt').textContent=title;
  document.getElementById('dpi').style.background=color;document.getElementById('dpb').innerHTML=html;
  document.getElementById('dp').classList.add('open');document.getElementById('overlay').classList.add('open');
}
window.closeDP=function(){document.getElementById('dp').classList.remove('open');document.getElementById('overlay').classList.remove('open');};

// ─── ANIMATION LOOP ───
function animate(){
  requestAnimationFrame(animate);const t=clock.getElapsedTime();controls.update();
  // Float agent avatars
  Object.values(agentMeshes).forEach(grp=>{
    const ud=grp.userData;grp.position.y=ud.baseY+Math.sin(t*.8+ud.angle)*.03;
    grp.rotation.y=t*.3;
  });
  // Pulse file nodes
  fileMeshes.forEach((m,i)=>{m.rotation.y=t*.5+i;m.rotation.x=Math.sin(t+i)*.3;});
  // Pulse region cores
  Object.values(regionMeshes).forEach(m=>{m.rotation.y=t*.2;m.scale.setScalar(1+Math.sin(t*2)*.05);});
  renderer.render(scene,camera);
}

// ─── BOOT ───
function boot(){
  init3D();refresh();setInterval(refresh,5000);
  document.getElementById('clk').textContent=new Date().toTimeString().split(' ')[0];
  setInterval(()=>document.getElementById('clk').textContent=new Date().toTimeString().split(' ')[0],1000);
  let p=0;const pi=setInterval(()=>{p+=12;document.getElementById('ldf').style.width=p+'%';if(p>=100)clearInterval(pi)},80);
}
try{boot()}catch(e){console.error('BOOT FAIL:',e)}
</script>
</body>
</html>
'''

import os
os.makedirs('/config/brain/dashboard', exist_ok=True)
with open('/config/brain/dashboard/index.html', 'w') as f:
    f.write(TEMPLATE)
print(f"Wrote {len(TEMPLATE)} bytes")
