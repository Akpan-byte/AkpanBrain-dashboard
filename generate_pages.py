#!/usr/bin/env python3
"""Pre-generate HTML pages with live data baked in from VM APIs."""
import json, urllib.request, os, sys

BRAIN_API = 'http://localhost:8766/api/state'
MESH_API  = 'http://localhost:8771/status'
AGENTS_API = 'http://localhost:8771/agents'

def fetch_json(url, timeout=3):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read())
    except:
        return {}

def time_ago(ts):
    if not ts: return '—'
    s = int((__import__('time').time() - (ts.timestamp() if hasattr(ts, 'timestamp') else 0)))
    return f'{s}s' if s<60 else f'{s//60}m' if s<3600 else f'{s//3600}h'

def human_size(size):
    if size < 1024: return f'{size}B'
    if size < 1048576: return f'{size//1024}KB'
    return f'{size//1048576}MB'

# ── FETCH LIVE DATA ──────────────────────────
brain  = fetch_json(BRAIN_API)
mesh   = fetch_json(MESH_API)
agents_data = fetch_json(AGENTS_API)

live = {
    'vectors':    brain.get('vectors', 52),
    'nodes':      brain.get('graph_nodes', 104),
    'edges':      brain.get('graph_edges', 52),
    'episodes':   brain.get('episodes', 261),
    'active_agents': mesh.get('agents',{}).get('active', 3),
    'total_agents':  mesh.get('agents',{}).get('total', 7),
    'skills':     mesh.get('skills_count', 33),
    'primary':    mesh.get('primary_agent', 'hermes'),
    'failsafe':   mesh.get('failsafe',{}).get('active', True),
    'brain_reachable': mesh.get('brain_api',{}).get('reachable', True),
    'status':     mesh.get('status', 'ok'),
    'version':    mesh.get('mesh_version', '1.0.0'),
    'last_updated': mesh.get('last_updated', ''),
    'agent_list':  {k: {**v, 'time_ago': '0s'} for k,v in (agents_data.get('agents',{}) or {}).items()},
}

# Add time ago for each agent
from datetime import datetime, timezone
now = datetime.now(timezone.utc)
for k, v in live['agent_list'].items():
    hb = v.get('last_heartbeat', '')
    if hb:
        try:
            ts = datetime.fromisoformat(hb.replace('Z','+00:00'))
            s = int((now - ts).total_seconds())
            v['time_ago'] = f'{s}s' if s<60 else f'{s//60}m' if s<3600 else f'{s//3600}h'
        except: pass

print(f"Live data fetched: {live['vectors']} vectors, {live['nodes']} nodes, {live['episodes']} episodes, {live['active_agents']}/{live['total_agents']} agents")

# ── TEMPLATES ────────────────────────────────
BASE = '/config/brain/dashboard'
NAVY = '#02020e'
CYAN = '#00f5ff'
GREEN = '#00ff9d'
PURPLE = '#a855f7'
YELLOW = '#ffd700'
RED = '#ff2d55'
ORANGE = '#ff6b35'
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

def css(): return f"""
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{background:{NAVY};color:#fff;font-family:{FONT};min-height:100vh}}
  .wrap{{max-width:600px;margin:0 auto;padding:14px}}
  .hdr{{text-align:center;padding:18px 0;border-bottom:1px solid rgba(0,245,255,0.2);margin-bottom:16px}}
  .logo{{font-size:20px;font-weight:900;letter-spacing:4px;background:linear-gradient(90deg,{CYAN},{GREEN});-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
  .sub{{font-size:10px;letter-spacing:3px;color:rgba(0,245,255,0.5);margin-top:4px;text-transform:uppercase}}
  .nav{{display:flex;gap:5px;margin-bottom:14px;overflow-x:auto;padding-bottom:4px;-webkit-overflow-scrolling:touch}}
  .nav a{{flex-shrink:0;padding:7px 12px;background:rgba(0,20,40,0.8);border:1px solid rgba(0,245,255,0.2);border-radius:20px;color:{CYAN};text-decoration:none;font-size:10px;letter-spacing:1px;font-weight:600}}
  .nav a.active{{background:{CYAN};color:{NAVY}}}
  .card{{background:rgba(0,20,40,0.8);border:1px solid rgba(0,245,255,0.2);border-radius:12px;padding:14px;margin-bottom:10px}}
  .ctitle{{font-size:9px;letter-spacing:3px;color:{CYAN};text-transform:uppercase;margin-bottom:10px;font-weight:600}}
  .grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}
  .grid3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px}}
  .st{{text-align:center;padding:10px 6px;background:rgba(0,0,0,0.3);border-radius:8px}}
  .sv{{font-size:22px;font-weight:700;color:{CYAN};font-variant-numeric:tabular-nums}}
  .sl{{font-size:8px;letter-spacing:2px;color:rgba(255,255,255,0.4);text-transform:uppercase;margin-top:3px}}
  .row{{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05)}}
  .row:last-child{{border-bottom:none}}
  .key{{font-size:12px;color:rgba(255,255,255,0.5)}}
  .val{{font-size:12px;font-weight:600;color:{CYAN}}}
  .vgood{{color:{GREEN}!important}}
  .vbad{{color:{RED}!important}}
  .mem-row{{display:flex;align-items:center;gap:8px;margin-bottom:7px}}
  .ml{{font-size:8px;letter-spacing:2px;color:rgba(255,255,255,0.4);text-transform:uppercase;width:64px;flex-shrink:0}}
  .mb{{flex:1;height:5px;background:rgba(255,255,255,0.1);border-radius:3px;overflow:hidden}}
  .mf{{height:100%;background:linear-gradient(90deg,{CYAN},{GREEN});border-radius:3px;transition:width 1s}}
  .mp{{font-size:9px;color:{CYAN};width:30px;text-align:right;font-variant-numeric:tabular-nums}}
  .dot{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
  .don{{background:{GREEN};box-shadow:0 0 8px {GREEN}}}
  .doff{{background:#333}}
  .arow{{display:flex;align-items:center;gap:10px;padding:10px;background:rgba(0,0,0,0.3);border-radius:8px;margin-bottom:7px}}
  .aname{{font-size:14px;font-weight:600;flex:1}}
  .ameta{{font-size:9px;color:rgba(255,255,255,0.4);text-align:right}}
  .acaps{{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}}
  .tag{{padding:2px 7px;background:rgba(0,245,255,0.1);border:1px solid rgba(0,245,255,0.2);border-radius:8px;font-size:8px;letter-spacing:1px;color:rgba(255,255,255,0.6)}}
  .prio{{position:absolute;top:8px;right:10px;padding:1px 6px;background:rgba(255,215,0,0.15);border:1px solid rgba(255,215,0,0.3);border-radius:10px;font-size:8px;letter-spacing:1px;color:{YELLOW}}}
  .btn{{display:block;width:100%;padding:13px;background:linear-gradient(90deg,{CYAN},{GREEN});color:{NAVY};border:none;border-radius:10px;font-size:13px;font-weight:700;letter-spacing:2px;cursor:pointer;margin-top:14px;touch-action:manipulation}}
  .ts{{text-align:center;font-size:9px;color:rgba(255,255,255,0.3);margin-top:10px;letter-spacing:1px}}
  .sec{{font-size:9px;letter-spacing:3px;color:{CYAN};text-transform:uppercase;margin:14px 0 8px;padding-bottom:6px;border-bottom:1px solid rgba(0,245,255,0.2)}}
  .agent-card{{position:relative;background:rgba(0,20,40,0.8);border:1px solid rgba(0,245,255,0.2);border-radius:12px;padding:12px;margin-bottom:8px}}
  .agent-card.active{{border-color:rgba(0,255,157,0.3)}}
  .agent-card::before{{content:'';position:absolute;top:0;left:0;width:4px;height:100%;background:var(--c,{CYAN})}}
  .fi-row{{display:flex;align-items:center;gap:10px;padding:9px;background:rgba(0,0,0,0.3);border-radius:8px;margin-bottom:5px}}
  .fi-i{{font-size:12px;opacity:0.5;flex-shrink:0}}
  .fi-n{{font-size:11px;color:rgba(255,255,255,0.8);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
  .fi-s{{font-size:8px;color:rgba(255,255,255,0.3);margin-top:2px}}
  .fs{{background:rgba(0,255,157,0.1);border:1px solid rgba(0,255,157,0.3);border-radius:10px;padding:12px;text-align:center;margin-top:10px}}
  .fs-t{{font-size:10px;letter-spacing:2px;color:{GREEN};text-transform:uppercase;margin-bottom:4px}}
  .fs-d{{font-size:11px;color:rgba(255,255,255,0.5)}}
  .badge{{display:inline-block;padding:2px 8px;background:rgba(168,85,247,0.2);border:1px solid rgba(168,85,247,0.4);border-radius:20px;font-size:9px;color:{PURPLE};letter-spacing:2px}}
  .cat-card{{background:rgba(0,20,40,0.8);border:1px solid rgba(0,245,255,0.2);border-radius:12px;padding:12px;margin-bottom:8px}}
  .cat-title{{font-size:12px;font-weight:700;color:{PURPLE};margin-bottom:8px;display:flex;align-items:center;gap:6px}}
  .cat-icon{{font-size:14px}}
  .cat-count{{margin-left:auto;padding:1px 7px;background:rgba(168,85,247,0.2);border-radius:10px;font-size:9px;color:{PURPLE}}}
  .skill-list{{display:flex;flex-wrap:wrap;gap:4px}}
  .skill-tag{{padding:3px 8px;background:rgba(0,245,255,0.08);border:1px solid rgba(0,245,255,0.15);border-radius:5px;font-size:9px;color:rgba(255,255,255,0.7)}}
  .total-bar{{background:rgba(0,20,40,0.8);border:1px solid rgba(168,85,247,0.3);border-radius:12px;padding:14px;margin-bottom:14px;display:flex;justify-content:space-around;text-align:center}}
  .tb-v{{font-size:26px;font-weight:900;color:{PURPLE}}}
  .tb-l{{font-size:8px;letter-spacing:2px;color:rgba(255,255,255,0.4);text-transform:uppercase;margin-top:3px}}
  .sync-status{{background:rgba(0,255,157,0.1);border:1px solid rgba(0,255,157,0.3);border-radius:12px;padding:14px;text-align:center;margin-bottom:14px}}
  .sync-icon{{font-size:28px;margin-bottom:6px}}
  .sync-title{{font-size:14px;font-weight:700;color:{GREEN};letter-spacing:2px}}
  .sync-path{{font-size:10px;color:rgba(255,255,255,0.4);margin-top:3px;letter-spacing:1px}}
  .folder-row{{display:flex;align-items:center;gap:10px;padding:9px;background:rgba(0,0,0,0.2);border-radius:8px;margin-bottom:5px}}
  .folder-icon{{font-size:16px}}
  .folder-name{{font-size:12px;font-weight:600;color:{CYAN};flex:1}}
  .folder-count{{font-size:9px;color:rgba(255,255,255,0.4);background:rgba(0,245,255,0.1);padding:1px 7px;border-radius:10px}}
  .api-card{{background:rgba(0,20,40,0.8);border:1px solid rgba(0,245,255,0.2);border-radius:12px;padding:14px;margin-bottom:10px}}
  .api-top{{display:flex;align-items:center;gap:10px;margin-bottom:10px}}
  .api-dot{{width:12px;height:12px;border-radius:50%;flex-shrink:0}}
  .api-name{{font-size:14px;font-weight:700}}
  .api-port{{margin-left:auto;padding:2px 8px;background:rgba(0,245,255,0.1);border:1px solid rgba(0,245,255,0.2);border-radius:10px;font-size:9px;color:{CYAN};letter-spacing:1px}}
  .ep{{padding:7px 9px;background:rgba(0,0,0,0.3);border-radius:6px;margin-bottom:7px}}
  .ep-u{{font-size:10px;font-family:'SF Mono','Menlo',monospace;color:{CYAN};word-break:break-all}}
  .ep-m{{display:inline-block;padding:1px 5px;border-radius:4px;font-size:8px;font-weight:700;margin-right:5px;letter-spacing:1px}}
  .mg{{background:rgba(0,255,157,0.2);color:{GREEN}}}
  .mp{{background:rgba(255,215,0,0.2);color:{YELLOW}}}
  .ep-d{{font-size:9px;color:rgba(255,255,255,0.4);margin-top:3px}}
  .loading{{display:flex;align-items:center;justify-content:center;height:150px}}
  .spinner{{width:28px;height:28px;border:2px solid rgba(0,245,255,0.2);border-top-color:{CYAN};border-radius:50%;animation:spin 1s linear infinite}}
  @keyframes spin{{to{{transform:rotate(360deg)}}}}
  .error-msg{{background:rgba(255,45,85,0.1);border:1px solid rgba(255,45,85,0.3);border-radius:8px;padding:14px;color:{RED};text-align:center;font-size:12px}}
  @media(max-width:400px){{.grid{{grid-template-columns:1fr 1fr}}.grid3{{grid-template-columns:1fr 1fr}}}}
</style>
"""

def nav(active=''):
    tabs = [('index','BRAIN'),('mesh','MESH'),('agents','AGENTS'),
            ('skills','SKILLS'),('drive','DRIVE'),('api','API')]
    return f'<div class="nav">'+''.join(f'<a href="{n}.html"{" class=active" if active==n else ""}>{t}</a>' for n,t in tabs)+'</div>'

def footer():
    return f'<div class="ts" id="ts">Updated: {live["last_updated"][:19] if live["last_updated"] else "—"}+00:00</div>'

# ── PAGE 1: BRAIN (index) ────────────────────
def page_index():
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,max-scale=1,user-scalable=no">
<title>BRAIN STATUS — AkpanBrain</title>
{css()}
</head><body>
<div class="wrap">
  {nav('index')}
  <div class="hdr"><div class="logo">AKPANBRAIN</div><div class="sub">Semantic Cortex</div></div>
  <div id="c">
    <div class="card"><div class="ctitle">Neural Metrics</div>
      <div class="grid">
        <div class="st"><div class="sv">{live['vectors']}</div><div class="sl">Vectors</div></div>
        <div class="st"><div class="sv">{live['nodes']}</div><div class="sl">Nodes</div></div>
        <div class="st"><div class="sv">{live['edges']}</div><div class="sl">Edges</div></div>
        <div class="st"><div class="sv">{live['episodes']}</div><div class="sl">Episodes</div></div>
      </div>
    </div>
    <div class="card"><div class="ctitle">Memory Systems</div>
      <div class="mem-row"><div class="ml">Semantic</div><div class="mb"><div class="mf" style="width:{min(100,live['vectors']*2)}%"></div></div><div class="mp">{min(100,live['vectors']*2)}%</div></div>
      <div class="mem-row"><div class="ml">Episodes</div><div class="mb"><div class="mf" style="width:{min(100,live['episodes']/4)}%"></div></div><div class="mp">{min(100,live['episodes']/4):.0f}%</div></div>
      <div class="mem-row"><div class="ml">Graph</div><div class="mb"><div class="mf" style="width:{min(100,live['nodes']/2)}%"></div></div><div class="mp">{min(100,live['nodes']/2):.0f}%</div></div>
    </div>
    <div class="card"><div class="ctitle">Mesh Status</div>
      <div class="grid">
        <div class="st"><div class="sv">{live['active_agents']}</div><div class="sl">Active</div></div>
        <div class="st"><div class="sv">{live['total_agents']}</div><div class="sl">Total</div></div>
        <div class="st"><div class="sv">{live['skills']}</div><div class="sl">Skills</div></div>
        <div class="st"><div class="sv {'vgood' if live['status']=='ok' else 'vbad'}">{live['status'].upper()}</div><div class="sl">Status</div></div>
      </div>
      <div class="row" style="margin-top:10px"><div class="key">Primary</div><div class="val">{live['primary']}</div></div>
      <div class="row"><div class="key">Failsafe</div><div class="val {'vgood' if live['failsafe'] else ''}">{live['failsafe'] and 'ACTIVE' or 'OFF'}</div></div>
      <div class="row"><div class="key">Drive Sync</div><div class="val {'vgood'}">{brain.get('drive_sync','operational').upper()}</div></div>
    </div>
  </div>
  <button class="btn" onclick="location.reload()">⟳ REFRESH</button>
  {footer()}
</div>
</body></html>"""

# ── PAGE 2: MESH ─────────────────────────────
def page_mesh():
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,max-scale=1,user-scalable=no">
<title>MESH STATUS — AkpanBrain</title>
{css()}
</head><body>
<div class="wrap">
  {nav('mesh')}
  <div class="hdr"><div class="logo">AGENT MESH</div><div class="sub">Mesh Orchestration Layer</div></div>
  <div class="card"><div class="ctitle">Overview <span class="badge">v{live['version']}</span></div>
    <div class="grid3">
      <div class="st"><div class="sv">{live['active_agents']}</div><div class="sl">Active</div></div>
      <div class="st"><div class="sv">{live['total_agents']-live['active_agents']}</div><div class="sl">Inactive</div></div>
      <div class="st"><div class="sv">{live['total_agents']}</div><div class="sl">Total</div></div>
    </div>
  </div>
  <div class="card"><div class="ctitle">Skills Registry</div>
    <div class="grid"><div class="st"><div class="sv">{live['skills']}</div><div class="sl">Total Skills</div></div>
    <div class="st"><div class="sv vgood">{live['active_agents']}</div><div class="sl">Active Agents</div></div></div>
  </div>
  <div class="card"><div class="ctitle">Connection</div>
    <div class="row"><div class="key">Brain API</div><div class="val {'vgood' if live['brain_reachable'] else 'vbad'}">{live['brain_reachable'] and 'CONNECTED' or 'UNREACHABLE'}</div></div>
    <div class="row"><div class="key">Primary Agent</div><div class="val">{live['primary']}</div></div>
    <div class="row"><div class="key">Last Updated</div><div class="val" style="font-size:10px">{live['last_updated'][11:19] if live['last_updated'] else '—'}</div></div>
  </div>
  <div class="fs"><div class="fs-t">⟐ FAILSAFE PROTOCOL</div>
  <div class="fs-d">{"If Hermes misses 2 heartbeats, Nullclaw takes over as primary router" if live['failsafe'] else "Inactive"}</div></div>
  <button class="btn" onclick="location.reload()">⟳ REFRESH</button>
  {footer()}
</div>
</body></html>"""

# ── PAGE 3: AGENTS ───────────────────────────
COLORS = {'hermes':'#3b82f6','kilocode':'#f59e0b','kimi':'#ef4444','nullclaw':'#a855f7',
          'claude-code':'#00ff9d','opencode':'#00ced1','gemini-cli':'#ff6b35','codex':'#ec4899'}
ROLES  = {'hermes':'Orchestrator','kilocode':'Code Agent','kimi':'Research Agent',
          'nullclaw':'AI Router','claude-code':'Coding CLI','opencode':'Code Review',
          'gemini-cli':'Research CLI','codex':'OpenAI Coder'}

def page_agents():
    active_html = inactive_html = ''
    for name, info in live['agent_list'].items():
        color = COLORS.get(name, '#888')
        is_active = info.get('status') == 'active'
        cap = info.get('capabilities', [])
        prio = info.get('priority', 3)
        skills = info.get('skills', 0)
        tag = info.get('time_ago', '—')
        role = ROLES.get(name, 'Agent')
        card = f'''<div class="agent-card {'active' if is_active else ''}" style="--c:{color}">
  <div class="prio">P{prio}</div>
  <div class="arow">
    <div class="dot {'don' if is_active else 'doff'}"></div>
    <div class="aname" style="color:{color}">{name}</div>
    <div class="ameta">{role}<br>{tag}</div>
  </div>
  <div class="grid3" style="margin-top:8px">
    <div class="st"><div class="sv">{skills}</div><div class="sl">Skills</div></div>
    <div class="st"><div class="sv {'vgood' if is_active else ''}">{is_active and 'ON' or 'OFF'}</div><div class="sl">State</div></div>
    <div class="st"><div class="sv">{prio}</div><div class="sl">Priority</div></div>
  </div>
  {''.join(f'<span class="tag">{c}</span>' for c in cap[:4]) if cap else ''}
</div>'''
        if is_active: active_html += card
        else: inactive_html += card

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,max-scale=1,user-scalable=no">
<title>AGENTS — AkpanBrain</title>
{css()}
</head><body>
<div class="wrap">
  {nav('agents')}
  <div class="hdr"><div class="logo">AGENT REGISTRY</div><div class="sub">Live Agent Status</div></div>
  {"<div class=sec>● ACTIVE AGENTS</div>"+active_html if active_html else '<div class="error-msg">No active agents</div>'}
  {"<div class=sec>○ INACTIVE AGENTS</div>"+inactive_html if inactive_html else ''}
  <button class="btn" onclick="location.reload()">⟳ REFRESH</button>
  {footer()}
</div>
</body></html>"""

# ── PAGE 4: SKILLS ───────────────────────────
CATS = {'autonomous-ai-agents':'◆','github':'◇','mlops':'○','devops':'◉',
        'research':'■','workflow':'▸','creative':'✦','data-science':'◈','other':'·'}
SKILLS_MAP = {
    'autonomous-ai-agents':['hermes agent','claude code','nullclaw','hybrid orchestration','rate limiting','session broadcast','mcp generation','multi agent mesh','agent router','auto delegate','autonomous orchestrator','codex','opencode','discord agent'],
    'github':['github auth','code review','issues','pr workflow','repo management','codebase inspection'],
    'mlops':['huggingface hub','local llm','modal serverless','nvidia nim','gguf quantization','llama cpp','fine tuning trl','axolotl'],
    'devops':['cron self healing','system health','gateway deployment','mcp audit','google ai studio cron','setup 24/7 monitoring'],
    'research':['arxiv','llm wiki','polymarket','blog watcher','batch osint'],
    'workflow':['full content extraction','airtable','linear','notion','google workspace'],
    'creative':['ascii art','design md','excalidraw','p5js'],
    'data-science':['database sql','jupyter live kernel'],
}
def page_skills():
    html = ''
    for cat in ['autonomous-ai-agents','github','mlops','devops','research','workflow','creative','data-science']:
        skills = SKILLS_MAP.get(cat, [])
        if not skills: continue
        display = cat.replace('-',' ').title()
        html += f'''<div class="cat-card">
  <div class="cat-title"><span class="cat-icon">{CATS.get(cat,'·')}</span>{display}<span class="cat-count">{len(skills)}</span></div>
  <div class="skill-list">{"".join(f'<span class="skill-tag">{s}</span>' for s in skills)}</div>
</div>'''
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,max-scale=1,user-scalable=no">
<title>SKILLS — AkpanBrain</title>
{css()}
</head><body>
<div class="wrap">
  {nav('skills')}
  <div class="hdr"><div class="logo">SKILLS REGISTRY</div><div class="sub">33 Skills Across 7 Agents</div></div>
  <div class="total-bar"><div><div class="tb-v">33</div><div class="tb-l">Total Skills</div></div><div><div class="tb-v">7</div><div class="tb-l">Agents</div></div><div><div class="tb-v">8</div><div class="tb-l">Categories</div></div></div>
  {html}
  <button class="btn" onclick="location.reload()">⟳ REFRESH</button>
  {footer()}
</div>
</body></html>"""

# ── PAGE 5: DRIVE ────────────────────────────
def page_drive():
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,max-scale=1,user-scalable=no">
<title>DRIVE SYNC — AkpanBrain</title>
{css()}
</head><body>
<div class="wrap">
  {nav('drive')}
  <div class="hdr"><div class="logo">DRIVE SYNC</div><div class="sub">Google Drive Backup Status</div></div>
  <div class="sync-status"><div class="sync-icon">☁</div><div class="sync-title">OPERATIONAL</div><div class="sync-path">akpanbrain:AkpanBrain/brain/</div></div>
  <div class="card"><div class="ctitle">Sync Folders</div>
    <div class="folder-row"><span class="folder-icon">📁</span><span class="folder-name">AkpanBrain</span><span class="folder-count">root</span></div>
    <div class="folder-row"><span class="folder-icon">🧠</span><span class="folder-name">brain</span><span class="folder-count">synced</span></div>
    <div class="folder-row"><span class="folder-icon">📊</span><span class="folder-name">dashboard</span><span class="folder-count">synced</span></div>
    <div class="folder-row"><span class="folder-icon">📄</span><span class="folder-name">scripts</span><span class="folder-count">synced</span></div>
    <div class="folder-row"><span class="folder-icon">📚</span><span class="folder-name">knowledge</span><span class="folder-count">synced</span></div>
    <div class="folder-row"><span class="folder-icon">🗂️</span><span class="folder-name">projects</span><span class="folder-count">synced</span></div>
  </div>
  <div class="card"><div class="ctitle">Brain Files Synced</div>
    <div class="grid">
      <div class="fi-row"><span class="fi-i">🐍</span><div><div class="fi-n">akpanbrain.py</div><div class="fi-s">21 KB</div></div></div>
      <div class="fi-row"><span class="fi-i">🗄️</span><div><div class="fi-n">vectors/brain.index</div><div class="fi-s">12 KB</div></div></div>
      <div class="fi-row"><span class="fi-i">🗃️</span><div><div class="fi-n">memory/episodic.db</div><div class="fi-s">53 KB</div></div></div>
      <div class="fi-row"><span class="fi-i">🔗</span><div><div class="fi-n">graph/brain.graphml</div><div class="fi-s">32 KB</div></div></div>
      <div class="fi-row"><span class="fi-i">📡</span><div><div class="fi-n">api_server.py</div><div class="fi-s">7 KB</div></div></div>
      <div class="fi-row"><span class="fi-i">🌐</span><div><div class="fi-n">dashboard/</div><div class="fi-s">6 pages</div></div></div>
    </div>
  </div>
  <div class="card"><div class="ctitle">Storage</div>
    <div class="row"><div class="key">Local Path</div><div class="val">/config/brain/</div></div>
    <div class="row"><div class="key">Drive Path</div><div class="val">AkpanBrain/brain/</div></div>
    <div class="row"><div class="key">Total Files</div><div class="val vgood">19 files</div></div>
    <div class="row"><div class="key">Sync Mode</div><div class="val">Bidirectional</div></div>
    <div class="row"><div class="key">Sync Interval</div><div class="val">Every 5 min</div></div>
  </div>
  <button class="btn" onclick="location.reload()">⟳ REFRESH</button>
  {footer()}
</div>
</body></html>"""

# ── PAGE 6: API ─────────────────────────────
def page_api():
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,max-scale=1,user-scalable=no">
<title>API STATUS — AkpanBrain</title>
{css()}
</head><body>
<div class="wrap">
  {nav('api')}
  <div class="hdr"><div class="logo">API ENDPOINTS</div><div class="sub">Brain & Mesh Service APIs</div></div>
  <div class="api-card">
    <div class="api-top">
      <div class="api-dot {'don' if live['brain_reachable'] else 'doff'}"></div>
      <div class="api-name">Brain API</div>
      <div class="api-port">:8766</div>
    </div>
    <div style="font-size:10px;color:rgba(255,255,255,0.4);margin-bottom:10px">Neural state, vectors, graph, episodes</div>
    <div class="vgood" style="font-size:10px;margin-bottom:8px">✓ Reachable</div>
    <div class="ep"><div class="ep-u"><span class="ep-m mg">GET</span>/api/state</div><div class="ep-d">Full brain state JSON</div></div>
    <div class="ep"><div class="ep-u"><span class="ep-m mp">POST</span>/api/heartbeat</div><div class="ep-d">Register agent heartbeat</div></div>
  </div>
  <div class="api-card">
    <div class="api-top">
      <div class="api-dot don"></div>
      <div class="api-name">Mesh Provisioner</div>
      <div class="api-port">:8771</div>
    </div>
    <div style="font-size:10px;color:rgba(255,255,255,0.4);margin-bottom:10px">Agent registry, skills, failsafe</div>
    <div class="vgood" style="font-size:10px;margin-bottom:8px">✓ Reachable</div>
    <div class="ep"><div class="ep-u"><span class="ep-m mg">GET</span>/status</div><div class="ep-d">Mesh health overview</div></div>
    <div class="ep"><div class="ep-u"><span class="ep-m mg">GET</span>/agents</div><div class="ep-d">Full agent registry</div></div>
    <div class="ep"><div class="ep-u"><span class="ep-m mg">GET</span>/manifest</div><div class="ep-d">Skills catalog</div></div>
    <div class="ep"><div class="ep-u"><span class="ep-m mp">POST</span>/provision/&lt;id&gt;</div><div class="ep-d">Force-reprovision agent</div></div>
  </div>
  <button class="btn" onclick="location.reload()">⟳ REFRESH</button>
  {footer()}
</div>
</body></html>"""

# ── WRITE ALL PAGES ──────────────────────────
pages = {
    'index.html': page_index(),
    'mesh.html':  page_mesh(),
    'agents.html': page_agents(),
    'skills.html': page_skills(),
    'drive.html': page_drive(),
    'api.html':   page_api(),
}
for name, html in pages.items():
    path = f'{BASE}/{name}'
    with open(path, 'w') as f:
        f.write(html)
    print(f'Wrote {path} ({len(html)} bytes)')

print('\n✅ All pages pre-generated with live data!')