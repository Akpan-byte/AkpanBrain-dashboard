#!/usr/bin/env python3
"""
AkpanBrain API Server v3 — COMPLETE REWRITE
- Real-time agent auto-detection with proper lifecycle
- Activity tracking with file→region mapping
- File system tree for every brain region
- WebSocket + REST for live dashboard
"""
import json, os, sqlite3, time, subprocess, hashlib, glob, re, threading, socket, fnmatch
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
    """Recursively scan a directory, return all files with metadata"""
    files = []
    if not os.path.exists(path):
        return files
    for root, dirs, names in os.walk(path):
        # Skip .git directories
        dirs[:] = [d for d in dirs if d != '.git']
        for n in names:
            full = os.path.join(root, n)
            try:
                size = os.path.getsize(full)
                mtime = os.path.getmtime(full)
                rel = os.path.relpath(full, base_dir) if base_dir else full
                ext = os.path.splitext(n)[1].lower()
                files.append({
                    "path": rel, "size": size, "name": n,
                    "ext": ext, "mtime": mtime,
                    "region": infer_region(rel),
                })
            except:
                pass
    return sorted(files, key=lambda x: x["size"], reverse=True)

def infer_region(path):
    """Infer brain region from file path"""
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
    """Get ALL files in a region's folder"""
    region = BRAIN_REGIONS.get(region_name, {})
    folder = region.get("folder", "")
    return scan_directory(folder) if folder else []

def get_all_files():
    """Get ALL files across entire brain directory"""
    all_files = {}
    # Scan entire brain dir for flat list
    all_flat = scan_directory(BRAIN_DIR, BRAIN_DIR)
    # Group by region
    for region in BRAIN_REGIONS:
        region_files = [f for f in all_flat if f.get("region") == region]
        all_files[region] = region_files
    # Put unmatched in semantic
    matched = set()
    for fl in all_files.values():
        for f in fl:
            matched.add(f["path"])
    unmatched = [f for f in all_flat if f["path"] not in matched]
    if unmatched:
        all_files.setdefault("semantic", []).extend(unmatched)
    return all_files

# ─── AGENT DETECTION ───
def detect_agents():
    """Detect ALL known agents. Active = process running. Inactive = not found."""
    agents = {}
    try:
        ps = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
        proc_raw = ps.stdout
    except:
        proc_raw = ""
    
    # Start with ALL known agents as inactive
    for name, sig in AGENT_SIGNATURES.items():
        agents[name] = {
            "status": "inactive", "color": sig["color"], "type": sig["type"],
            "desc": sig["desc"], "region": sig["region"],
            "pid": None, "cpu": "0", "mem": "0",
            "detected_by": "signature_scan",
            "last_seen": 0,
        }
    
    # Now scan for active ones
    for name, sig in AGENT_SIGNATURES.items():
        cmd = sig["cmd"].lower()
        
        for line in proc_raw.split('\n'):
            line_lower = line.lower()
            if 'grep' in line_lower or 'api_server' in line_lower:
                continue
            parts = line.strip().split()
            if len(parts) < 11:
                continue
            cmdline = ' '.join(parts[10:]).lower()
            
            if re.search(r'\b' + re.escape(cmd) + r'\b', cmdline):
                agents[name] = {
                    "status": "active", "color": sig["color"], "type": sig["type"],
                    "desc": sig["desc"], "region": sig["region"],
                    "pid": parts[1], "cpu": parts[2], "mem": parts[3],
                    "detected_by": "process_scan",
                    "last_seen": int(time.time() * 1000),
                }
                break
        
        # Special: nullclaw via 9router port check
        if name == "nullclaw" and agents[name]["status"] == "inactive":
            try:
                s = socket.create_connection(("localhost", 20128), timeout=1)
                s.close()
                agents[name] = {
                    "status": "active", "color": sig["color"], "type": sig["type"],
                    "desc": sig["desc"], "region": sig["region"],
                    "pid": None, "detected_by": "port_scan",
                    "last_seen": int(time.time() * 1000),
                }
            except:
                pass
    
    # Also detect 9router as its own agent via port
    if "9router" not in agents:
        try:
            s = socket.create_connection(("localhost", 20128), timeout=1)
            s.close()
            agents["9router"] = {
                "status": "active", "color": "#FF0000", "type": "routing",
                "desc": "9Router — LLM routing proxy on :20128", "region": "episodic",
                "pid": None, "cpu": "0", "mem": "0",
                "detected_by": "port_scan",
                "last_seen": int(time.time() * 1000),
            }
        except:
            agents["9router"] = {
                "status": "inactive", "color": "#FF0000", "type": "routing",
                "desc": "9Router — LLM routing proxy on :20128", "region": "episodic",
                "pid": None, "cpu": "0", "mem": "0",
                "detected_by": "signature_scan", "last_seen": 0,
            }
        
    return agents

def get_agent_history():
    """Get recent agent activity from episodic memory"""
    history = {}
    try:
        db_path = f"{BRAIN_DIR}/memory/episodic.db"
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            rows = conn.execute(
                "SELECT agent_id, action, content, timestamp FROM episodes ORDER BY timestamp DESC LIMIT 50"
            ).fetchall()
            conn.close()
            for row in rows:
                agent, action, content, ts = row
                if agent not in history:
                    history[agent] = []
                history[agent].append({"action": action, "content": content, "ts": ts})
    except:
        pass
    return history

# ─── ACTIVITY TRACKING ───
_agent_last_positions = {}

def get_current_activity():
    """Get what agents are currently doing by checking Redis + filesystem + episodic"""
    activity = []
    
    # Check Redis for active tasks
    if redis_ok:
        try:
            for key in r.scan_iter("task:*"):
                agent = key.decode().split(":")[-1] if isinstance(key, bytes) else key.split(":")[-1]
                task = r.get(key)
                if task:
                    task_str = task.decode() if isinstance(task, bytes) else task
                    activity.append({
                        "agent": agent, "action": "working", "target": task_str,
                        "region": infer_region_from_task(task_str), "ts": int(time.time() * 1000),
                    })
        except:
            pass
    
    # Check filesystem for recent modifications
    for region, info in BRAIN_REGIONS.items():
        folder = info.get("folder", "")
        if folder and os.path.exists(folder):
            try:
                for f in glob.glob(f"{folder}**/*", recursive=True):
                    if os.path.isfile(f):
                        mtime = os.path.getmtime(f)
                        if time.time() - mtime < 300:  # Modified in last 5 min
                            rel = os.path.relpath(f, BRAIN_DIR)
                            activity.append({
                                "agent": "system", "action": "file_update",
                                "target": rel, "region": region,
                                "ts": int(mtime * 1000),
                            })
            except:
                pass
    
    # Check episodic DB for very recent activity
    try:
        db_path = f"{BRAIN_DIR}/memory/episodic.db"
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cutoff = int(time.time() - 600)  # 10 min ago
            rows = conn.execute(
                "SELECT agent_id, action, content, timestamp FROM episodes WHERE timestamp > ? ORDER BY timestamp DESC LIMIT 20",
                (cutoff,),
            ).fetchall()
            conn.close()
            for row in rows:
                activity.append({
                    "agent": row[0] or "system", "action": row[1], "target": row[2],
                    "region": infer_region_from_task(row[2]), "ts": row[3] * 1000,
                })
    except:
        pass
    
    # Sort by timestamp, most recent first, dedupe by agent+target
    seen = set()
    unique = []
    for a in sorted(activity, key=lambda x: x["ts"], reverse=True):
        key = f"{a['agent']}:{a.get('target','')}"
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique[:20]

def infer_region_from_task(task):
    task = task.lower()
    if "vector" in task or "embedding" in task or "faiss" in task: return "semantic"
    if "graph" in task or "relationship" in task or "node" in task: return "graph"
    if "memory" in task or "episode" in task or "sqlite" in task: return "episodic"
    if "redis" in task or "cache" in task or "working" in task: return "working"
    if "skill" in task or "procedural" in task: return "procedural"
    if "file" in task or "sensory" in task: return "sensory"
    return "semantic"

# ─── BRAIN STATS ───
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
            "total_size": total_size, "files": files[:50],  # limit to 50 files in response
        }
    return stats

# ─── NULLCLAW STATUS ───
def get_nullclaw_status():
    status = {"online": False, "models": [], "latency_ms": -1, "connections": 0}
    try:
        s = socket.create_connection(("localhost", 20128), timeout=2)
        s.close()
        status["online"] = True
    except:
        pass
    
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:20128/v1/models", timeout=3) as resp:
            data = json.loads(resp.read().decode())
            status["models"] = [m.get("id", "unknown") for m in data.get("data", [])]
            status["connections"] = len(data.get("data", []))
    except:
        pass
    
    return status

# ─── HTTP HANDLER ───
class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        
        if path == "/api/agents":
            agents = detect_agents()
            self._respond(200, agents)
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
        elif path == "/api/region":
            region = query.get("name", [""])[0]
            if region in BRAIN_REGIONS:
                files = get_region_files(region)
                self._respond(200, {
                    "name": BRAIN_REGIONS[region]["name"],
                    "backend": BRAIN_REGIONS[region]["backend"],
                    "color": BRAIN_REGIONS[region]["color"],
                    "files": files,
                    "file_count": len(files),
                })
            else:
                self._respond(404, {"error": "Region not found"})
        elif path == "/api/sync":
            self._respond(200, {"status": "connected", "last_sync": open(f"{BRAIN_DIR}/cache/.last_sync").read().strip() if os.path.exists(f"{BRAIN_DIR}/cache/.last_sync") else "N/A"})
        elif path == "/api/nullclaw":
            self._respond(200, get_nullclaw_status())
        elif path == "/" or path == "/index.html":
            self.path = "/index.html"
            return super().do_GET()
        elif path == "/nullclaw":
            self._respond(200, get_nullclaw_status())
        else:
            self._respond(404, {"error": "Not found"})
    
    def _respond(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def log_message(self, format, *args):
        pass

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

if __name__ == "__main__":
    print(f"AkpanBrain API Server v3 starting on port {PORT}")
    os.chdir(DASHBOARD_DIR)
    server = ThreadedHTTPServer(("", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down...")
