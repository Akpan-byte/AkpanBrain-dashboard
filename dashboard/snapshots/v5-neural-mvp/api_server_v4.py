#!/usr/bin/env python3
"""
AkpanBrain API Server v4 — LIVE NEURAL DASHBOARD
- WebSocket real-time push (agents move, file interactions, electrical pulses)
- Agent position tracking with smooth region transitions
- Activity feed with file→agent→region mapping
- Every REST endpoint still works
"""
import json, os, sqlite3, time, subprocess, hashlib, glob, re, threading, socket, struct, select, hashlib, base64
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

# ─── CONFIG ───
BRAIN_DIR = "/config/brain"
DASHBOARD_DIR = f"{BRAIN_DIR}/dashboard"
PORT = 8199
WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
ws_clients = []
activity_log = []  # rolling activity log
agent_positions = {}  # agent_name -> {region, file, x, y, z, target_x, target_y, target_z, ts}
_agent_lock = threading.Lock()

# ─── AGENT SIGNATURES ───
AGENT_SIGNATURES = {
 "hermes": {"cmd": "hermes", "color": "#FF0000", "type": "reasoning", "desc": "Hermes Agent — autonomous AI agent orchestrator", "region": "working"},
 "gemini-cli": {"cmd": "gemini", "color": "#C0C0C0", "type": "search", "desc": "Google Gemini CLI", "region": "semantic"},
 "kilo-code": {"cmd": "kilo", "color": "#800000", "type": "coding", "desc": "Kilo Code", "region": "procedural"},
 "kimi-code": {"cmd": "kimi", "color": "#A0A0A0", "type": "coding", "desc": "Kimi Code (Moonshot)", "region": "procedural"},
 "nullclaw": {"cmd": "nullclaw", "color": "#FF3333", "type": "routing", "desc": "Nullclaw AI Router", "region": "working"},
 "claude-code": {"cmd": "claude", "color": "#C0C0C0", "type": "coding", "desc": "Claude Code", "region": "procedural"},
 "opencode": {"cmd": "opencode", "color": "#404040", "type": "coding", "desc": "OpenCode", "region": "procedural"},
 "qwen-code": {"cmd": "qwen-code", "color": "#606060", "type": "llm", "desc": "Qwen Code", "region": "procedural"},
 "codebuff": {"cmd": "codebuff", "color": "#808080", "type": "coding", "desc": "CodeBuff", "region": "procedural"},
 "jcode": {"cmd": "jcode", "color": "#555555", "type": "coding", "desc": "JCode", "region": "episodic"},
 "claw-code": {"cmd": "claw-code-agent", "color": "#FF4444", "type": "coding", "desc": "Claw Code", "region": "procedural"},
 "cline": {"cmd": "cline", "color": "#B0B0B0", "type": "coding", "desc": "Cline", "region": "procedural"},
 "ironclaw": {"cmd": "ironclaw", "color": "#CC0000", "type": "security", "desc": "IronClaw", "region": "working"},
 "openfang": {"cmd": "cli-anything-openfang", "color": "#FF2222", "type": "coding", "desc": "OpenFang", "region": "procedural"},
 "codex": {"cmd": "codex", "color": "#E0E0E0", "type": "coding", "desc": "OpenAI Codex CLI", "region": "procedural"},
}

# ─── Brain Regions — Red/Black/Silver ───
BRAIN_REGIONS = {
 "semantic": {"name": "Semantic Cortex", "backend": "FAISS", "color": "#C0C0C0",
  "folder": f"{BRAIN_DIR}/vectors/", "file": f"{BRAIN_DIR}/vectors/brain.index"},
 "graph": {"name": "Knowledge Graph", "backend": "NetworkX", "color": "#808080",
  "folder": f"{BRAIN_DIR}/graph/", "file": f"{BRAIN_DIR}/graph/brain.graphml"},
 "episodic": {"name": "Episodic Memory", "backend": "SQLite", "color": "#FF0000",
  "folder": f"{BRAIN_DIR}/memory/", "file": f"{BRAIN_DIR}/memory/episodic.db"},
 "working": {"name": "Working Memory", "backend": "Redis", "color": "#A0A0A0",
  "folder": f"{BRAIN_DIR}/cache/", "port": 6379},
 "procedural": {"name": "Procedural Cortex", "backend": "Skills", "color": "#FF3333",
  "folder": f"{BRAIN_DIR}/skills/"},
 "sensory": {"name": "Sensory Buffer", "backend": "FileWatch", "color": "#D0D0D0",
  "folder": f"{BRAIN_DIR}/sensory/"},
}

# Region 3D positions for agent placement
REGION_POSITIONS = {
 "semantic":  {"x": -2.0, "y":  0.8, "z":  0.0},
 "graph":     {"x": -1.0, "y":  0.4, "z": -1.2},
 "episodic":  {"x":  0.0, "y": -0.5, "z": -0.8},
 "working":   {"x":  1.0, "y":  0.6, "z":  0.8},
 "procedural":{"x":  2.0, "y": -0.2, "z":  0.0},
 "sensory":   {"x":  0.5, "y":  1.0, "z": -0.5},
}

try:
 import redis
 r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
 r.ping()
 redis_ok = True
except:
 redis_ok = False
 r = None

# ─── FILE SYSTEM SCANNER ───
def scan_directory(path, base_dir=BRAIN_DIR):
 files = []
 if not os.path.exists(path): return files
 for root, dirs, names in os.walk(path):
  dirs[:] = [d for d in dirs if d != '.git']
  for n in names:
   full = os.path.join(root, n)
   try:
    size = os.path.getsize(full)
    mtime = os.path.getmtime(full)
    rel = os.path.relpath(full, base_dir) if base_dir else full
    ext = os.path.splitext(n)[1].lower()
    files.append({"path": rel, "size": size, "name": n, "ext": ext, "mtime": mtime, "region": infer_region(rel)})
   except: pass
 return sorted(files, key=lambda x: x["size"], reverse=True)

def infer_region(path):
 p = path.lower()
 if "vectors" in p or "index" in p: return "semantic"
 if "graph" in p: return "graph"
 if "memory" in p or ".db" in p: return "episodic"
 if "cache" in p or "sync" in p: return "working"
 if "skills" in p or "api_server" in p or p.endswith(".py"): return "procedural"
 if "sensory" in p or "watch" in p: return "sensory"
 if "dashboard" in p or p.endswith(".html") or p.endswith(".md"): return "semantic"
 return "semantic"

def get_region_files(region_name):
 region = BRAIN_REGIONS.get(region_name, {})
 folder = region.get("folder", "")
 return scan_directory(folder) if folder else []

def get_all_files():
 all_files = {}
 all_flat = scan_directory(BRAIN_DIR, BRAIN_DIR)
 for region in BRAIN_REGIONS:
  region_files = [f for f in all_flat if f.get("region") == region]
  all_files[region] = region_files
 matched = set()
 for fl in all_files.values():
  for f in fl: matched.add(f["path"])
 unmatched = [f for f in all_flat if f["path"] not in matched]
 if unmatched: all_files.setdefault("semantic", []).extend(unmatched)
 return all_files

# ─── AGENT DETECTION ───
def detect_agents():
 agents = {}
 try:
  ps = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
  proc_raw = ps.stdout
 except:
  proc_raw = ""
 
 for name, sig in AGENT_SIGNATURES.items():
  agents[name] = {
   "status": "inactive", "color": sig["color"], "type": sig["type"],
   "desc": sig["desc"], "region": sig["region"],
   "pid": None, "cpu": "0", "mem": "0",
   "detected_by": "signature_scan", "last_seen": 0,
   "current_file": None, "current_action": None,
  }
 
 for name, sig in AGENT_SIGNATURES.items():
  cmd = sig["cmd"].lower()
  for line in proc_raw.split('\n'):
   line_lower = line.lower()
   if 'grep' in line_lower or 'api_server' in line_lower: continue
   parts = line.strip().split()
   if len(parts) < 11: continue
   cmdline = ' '.join(parts[10:]).lower()
   if re.search(r'\b' + re.escape(cmd) + r'\b', cmdline):
    # Try to extract what file they're working on from cmdline
    current_file = extract_working_file(cmdline, name)
    current_action = infer_action(cmdline)
    agents[name] = {
     "status": "active", "color": sig["color"], "type": sig["type"],
     "desc": sig["desc"], "region": sig["region"],
     "pid": parts[1], "cpu": parts[2], "mem": parts[3],
     "detected_by": "process_scan",
     "last_seen": int(time.time() * 1000),
     "current_file": current_file, "current_action": current_action,
     "cmdline": cmdline,
    }
    break
 
 # Special: nullclaw via 9router port check
 if "nullclaw" in agents and agents["nullclaw"]["status"] == "inactive":
  try:
   s = socket.create_connection(("localhost", 20128), timeout=1)
   s.close()
   sig = AGENT_SIGNATURES["nullclaw"]
   agents["nullclaw"] = {
    "status": "active", "color": sig["color"], "type": sig["type"],
    "desc": sig["desc"], "region": sig["region"],
    "pid": None, "detected_by": "port_scan",
    "last_seen": int(time.time() * 1000),
    "current_file": None, "current_action": "routing",
   }
  except: pass
 
 # 9router
 try:
  s = socket.create_connection(("localhost", 20128), timeout=1)
  s.close()
  agents["9router"] = {
   "status": "active", "color": "#FF0000", "type": "routing",
   "desc": "9Router — LLM routing proxy on :20128", "region": "episodic",
   "pid": None, "cpu": "0", "mem": "0", "detected_by": "port_scan",
   "last_seen": int(time.time() * 1000),
   "current_file": None, "current_action": "routing",
  }
 except:
  agents["9router"] = {
   "status": "inactive", "color": "#FF0000", "type": "routing",
   "desc": "9Router — LLM routing proxy on :20128", "region": "episodic",
   "pid": None, "cpu": "0", "mem": "0", "detected_by": "signature_scan", "last_seen": 0,
   "current_file": None, "current_action": None,
  }
 
 return agents

def extract_working_file(cmdline, agent_name):
 """Extract the file an agent is currently working on from its command line"""
 # Common patterns: agent ... /path/to/file, agent ... -f file, agent ... file.py
 parts = cmdline.split()
 for p in reversed(parts):
  if '/' in p and ('.' in p.split('/')[-1]):
   if not p.startswith('-') and p not in ('python3', 'python', 'node', 'npm'):
    return p
  if p.endswith(('.py', '.js', '.ts', '.md', '.json', '.yaml', '.yml', '.toml', '.html', '.css', '.sh', '.sql')):
   if not p.startswith('-'):
    return p
 return None

def infer_action(cmdline):
 """Infer what action the agent is performing"""
 c = cmdline.lower()
 if 'edit' in c or 'write' in c or 'patch' in c: return "editing"
 if 'read' in c or 'cat' in c or 'view' in c: return "reading"
 if 'test' in c or 'pytest' in c or 'jest' in c: return "testing"
 if 'build' in c or 'compile' in c: return "building"
 if 'deploy' in c: return "deploying"
 if 'search' in c or 'grep' in c or 'find' in c: return "searching"
 if 'git' in c and ('push' in c or 'commit' in c): return "committing"
 if 'server' in c or 'serve' in c: return "serving"
 if 'route' in c or 'proxy' in c: return "routing"
 return "processing"

# ─── ACTIVITY TRACKING ───
def log_activity(agent, action, target, region=None):
 """Log an activity event and push to all WebSocket clients"""
 if not region and target:
  region = infer_region(target) if '/' in str(target) else "semantic"
 
 event = {
  "agent": agent, "action": action, "target": str(target) or "",
  "region": region or "semantic",
  "ts": int(time.time() * 1000),
 }
 
 with _agent_lock:
  activity_log.append(event)
  if len(activity_log) > 200: activity_log.pop(0)
  
  # Update agent position
  if agent in AGENT_SIGNATURES or agent == "9router":
   rp = REGION_POSITIONS.get(region or "semantic", REGION_POSITIONS["semantic"])
   # Add slight random offset so agents don't stack
   import random
   ox = (random.random() - 0.5) * 0.4
   oy = (random.random() - 0.5) * 0.3
   oz = (random.random() - 0.5) * 0.4
   agent_positions[agent] = {
    "region": region or "semantic",
    "file": str(target) or None,
    "action": action,
    "x": rp["x"] + ox, "y": rp["y"] + oy, "z": rp["z"] + oz,
    "ts": event["ts"],
   }
 
 # Push to WebSocket clients
 broadcast_ws({"type": "activity", "data": event})
 broadcast_ws({"type": "agent_positions", "data": agent_positions})

def get_current_activity():
 activity = []
 # System file modifications
 for region, info in BRAIN_REGIONS.items():
  folder = info.get("folder", "")
  if folder and os.path.exists(folder):
   try:
    for f in glob.glob(f"{folder}**/*", recursive=True):
     if os.path.isfile(f):
      mtime = os.path.getmtime(f)
      if time.time() - mtime < 300:
       rel = os.path.relpath(f, BRAIN_DIR)
       activity.append({"agent": "system", "action": "file_update", "target": rel, "region": region, "ts": int(mtime * 1000)})
   except: pass
 
 # Add agent positions as activity
 with _agent_lock:
  for name, pos in agent_positions.items():
   activity.append({
    "agent": name, "action": pos.get("action", "idle"),
    "target": pos.get("file", ""), "region": pos.get("region", ""),
    "ts": pos.get("ts", 0),
   })
 
 seen = set()
 unique = []
 for a in sorted(activity, key=lambda x: x["ts"], reverse=True):
  key = f"{a['agent']}:{a.get('target','')}"
  if key not in seen:
   seen.add(key)
   unique.append(a)
 return unique[:30]

def get_brain_stats():
 stats = {}
 for name, info in BRAIN_REGIONS.items():
  folder = info.get("folder", "")
  files = get_region_files(name) if folder else []
  file_count = len(files)
  total_size = sum(f["size"] for f in files)
  stats[name] = {
   "name": info["name"], "backend": info["backend"],
   "color": info["color"], "file_count": file_count,
   "total_size": total_size, "files": files[:50],
  }
 return stats

def get_nullclaw_status():
 status = {"online": False, "models": [], "latency_ms": -1, "connections": 0}
 try:
  s = socket.create_connection(("localhost", 20128), timeout=2)
  s.close()
  status["online"] = True
 except: pass
 try:
  import urllib.request
  with urllib.request.urlopen("http://localhost:20128/v1/models", timeout=3) as resp:
   data = json.loads(resp.read().decode())
   status["models"] = [m.get("id", "unknown") for m in data.get("data", [])]
   status["connections"] = len(data.get("data", []))
 except: pass
 return status

# ─── WEBSOCKET ───
def ws_handshake(sock):
 """Perform WebSocket handshake on an accepted socket"""
 try:
  data = sock.recv(4096)
  if not data: return False
  headers = data.decode('utf-8', errors='replace')
  key = None
  for line in headers.split('\r\n'):
   if line.lower().startswith('sec-websocket-key'):
    key = line.split(':', 1)[1].strip()
    break
  if not key: return False
  accept = base64.b64encode(hashlib.sha1((key + WS_MAGIC).encode()).digest()).decode()
  response = (
   "HTTP/1.1 101 Switching Protocols\r\n"
   "Upgrade: websocket\r\n"
   "Connection: Upgrade\r\n"
   f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
  )
  sock.sendall(response.encode())
  return True
 except:
  return False

def ws_frame_decode(data):
 """Decode a WebSocket frame, return payload string or None"""
 if not data or len(data) < 2: return None
 try:
  opcode = data[0] & 0x0F
  if opcode == 0x08: return None  # close
  masked = (data[1] & 0x80) != 0
  length = data[1] & 0x7F
  offset = 2
  if length == 126:
   length = struct.unpack('>H', data[2:4])[0]
   offset = 4
  elif length == 127:
   length = struct.unpack('>Q', data[2:10])[0]
   offset = 10
  if masked:
   mask = data[offset:offset+4]
   offset += 4
  else:
   mask = b'\x00\x00\x00\x00'
  payload = bytearray(data[offset:offset+length])
  if masked:
   for i in range(len(payload)):
    payload[i] ^= mask[i % 4]
  return payload.decode('utf-8', errors='replace')
 except:
  return None

def ws_frame_encode(message):
 """Encode a string as a WebSocket text frame"""
 payload = message.encode('utf-8')
 frame = bytearray([0x81])  # FIN + text opcode
 length = len(payload)
 if length < 126:
  frame.append(length)
 elif length < 65536:
  frame.append(126)
  frame.extend(struct.pack('>H', length))
 else:
  frame.append(127)
  frame.extend(struct.pack('>Q', length))
 frame.extend(payload)
 return bytes(frame)

def broadcast_ws(message):
 """Send a message to all connected WebSocket clients"""
 if isinstance(message, dict):
  message = json.dumps(message)
 frame = ws_frame_encode(message)
 dead = []
 for i, client in enumerate(ws_clients):
  try:
   client.sendall(frame)
  except:
   dead.append(i)
 for i in reversed(dead):
  ws_clients.pop(i)

def handle_ws_client(sock, addr):
 """Handle a single WebSocket client"""
 if not ws_handshake(sock):
  sock.close()
  return
 
 ws_clients.append(sock)
 
 # Send initial state
 try:
  agents = detect_agents()
  positions = {name: {"region": a["region"], "x": REGION_POSITIONS.get(a["region"], REGION_POSITIONS["semantic"])["x"],
   "y": REGION_POSITIONS.get(a["region"], REGION_POSITIONS["semantic"])["y"],
   "z": REGION_POSITIONS.get(a["region"], REGION_POSITIONS["semantic"])["z"],
   "status": a["status"], "file": a.get("current_file"), "action": a.get("current_action")}
   for name, a in agents.items()}
  
  init_msg = json.dumps({"type": "init", "agents": agents, "positions": positions, "regions": {k: v for k, v in REGION_POSITIONS.items()}})
  sock.sendall(ws_frame_encode(init_msg))
 except: pass
 
 # Keep-alive loop
 try:
  while True:
   ready = select.select([sock], [], [], 30)
   if ready[0]:
    data = sock.recv(4096)
    if not data: break
    msg = ws_frame_decode(data)
    if msg is None: break  # close frame
    # Client messages are pings or commands
    if msg == 'ping':
     sock.sendall(ws_frame_encode('pong'))
    elif msg.startswith('{'):
     try:
      cmd = json.loads(msg)
      if cmd.get('type') == 'get_state':
       agents = detect_agents()
       state = json.dumps({"type": "state_update", "agents": agents, "positions": agent_positions})
       sock.sendall(ws_frame_encode(state))
     except: pass
 except: pass
 finally:
  if sock in ws_clients: ws_clients.remove(sock)
  try: sock.close()
  except: pass

# ─── BACKGROUND: MONITOR AGENT CHANGES ───
_last_agents = {}

def monitor_agents():
 """Background thread: detect agent changes and broadcast"""
 global _last_agents
 import random
 while True:
  try:
   agents = detect_agents()
   events = []
   with _agent_lock:
    for name, info in agents.items():
     old = _last_agents.get(name, {})
     # Always update positions for active agents
     if info["status"] == "active":
      rp = REGION_POSITIONS.get(info["region"], REGION_POSITIONS["semantic"])
      ox = (random.random() - 0.5) * 0.3
      oy = (random.random() - 0.5) * 0.2
      oz = (random.random() - 0.5) * 0.3
      agent_positions[name] = {
       "region": info["region"], "file": info.get("current_file"),
       "action": info.get("current_action", "processing"),
       "x": rp["x"] + ox, "y": rp["y"] + oy, "z": rp["z"] + oz,
       "ts": int(time.time() * 1000),
      }
     elif name in agent_positions:
      # Mark inactive but keep last known position
      agent_positions[name]["status"] = "inactive"
     
     # Collect events (don't call log_activity inside lock)
     if info["status"] != old.get("status"):
      events.append((name, f"status_{info['status']}", info.get("current_file"), info["region"]))
     elif info.get("current_file") and info["current_file"] != old.get("current_file"):
      events.append((name, info.get("current_action", "processing"), info["current_file"], info["region"]))
    
    _last_agents = agents
   
   # Fire events outside the lock
   for name, action, target, region in events:
    log_activity(name, action, target, region)
   
   # Broadcast positions every 2s
   broadcast_ws({"type": "agent_positions", "data": dict(agent_positions)})
  except Exception as e:
   print(f"Monitor error: {e}")
  time.sleep(2)

# ─── HTTP HANDLER ───
class Handler(SimpleHTTPRequestHandler):
 def do_GET(self):
  parsed = urlparse(self.path)
  path = parsed.path
  query = parse_qs(parsed.query)
  
  # WebSocket upgrade
  upgrade = self.headers.get('Upgrade', '').lower()
  if upgrade == 'websocket':
   self.handle_ws()
   return
  
  if path == "/api/agents":
   self._respond(200, detect_agents())
  elif path == "/api/brain":
   self._respond(200, get_brain_stats())
  elif path == "/api/activity":
   self._respond(200, get_current_activity())
  elif path == "/api/files":
   region = query.get("region", [""])[0]
   if region:
    self._respond(200, get_region_files(region))
   else:
    self._respond(200, get_all_files())
  elif path == "/api/positions":
   self._respond(200, dict(agent_positions))
  elif path == "/api/regions":
   self._respond(200, {"positions": REGION_POSITIONS, "info": {k: {"name": v["name"], "backend": v["backend"], "color": v["color"]} for k, v in BRAIN_REGIONS.items()}})
  elif path == "/api/sync":
   self._respond(200, {"status": "connected", "last_sync": open(f"{BRAIN_DIR}/cache/.last_sync").read().strip() if os.path.exists(f"{BRAIN_DIR}/cache/.last_sync") else "N/A"})
  elif path == "/api/nullclaw":
   self._respond(200, get_nullclaw_status())
  elif path == "/" or path == "/index.html":
   self.path = "/index.html"
   return super().do_GET()
  else:
   self._respond(404, {"error": "Not found"})
 
 def handle_ws(self):
  """Handle WebSocket upgrade by passing the socket to a handler thread"""
  # We need the raw socket — steal it from the HTTP server
  # This is a bit hacky but works with the ThreadingMixIn
  try:
   # Don't let SimpleHTTPRequestHandler close the socket
   self.close_connection = False
   # Hand off to WS handler in a new thread
   sock = self.request
   t = threading.Thread(target=handle_ws_client, args=(sock, self.client_address), daemon=True)
   t.start()
  except Exception as e:
   print(f"WS upgrade failed: {e}")
 
 def _respond(self, code, data):
  self.send_response(code)
  self.send_header("Content-Type", "application/json")
  self.send_header("Access-Control-Allow-Origin", "*")
  self.send_header("Access-Control-Allow-Headers", "*")
  self.end_headers()
  self.wfile.write(json.dumps(data).encode())
 
 def log_message(self, format, *args):
  pass

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
 daemon_threads = True
 allow_reuse_address = True

if __name__ == "__main__":
 print(f"AkpanBrain API Server v4 starting on port {PORT}")
 os.chdir(DASHBOARD_DIR)
 server = ThreadedHTTPServer(("", PORT), Handler)
 
 # Start agent monitor thread
 monitor_thread = threading.Thread(target=monitor_agents, daemon=True)
 monitor_thread.start()
 print("Agent monitor started — broadcasting every 2s")
 
 try:
  server.serve_forever()
 except KeyboardInterrupt:
  print("\nServer shutting down...")
