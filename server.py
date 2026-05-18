#!/usr/bin/env python3
"""AkpanBrain Dashboard Server - Simple & Robust"""
import json, os, sys, sqlite3
from datetime import datetime, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
BRAIN_DIR = '/config/brain'
PORT = 8765

# Find first free port starting from 8765
for test_port in range(8765, 8888):
    try:
        s = HTTPServer(('0.0.0.0', test_port), type('X', (), {}))
        s.server_close()
        PORT = test_port
        break
    except OSError:
        continue

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BRAIN_DIR, **kwargs)
    
    def do_GET(self):
        if self.path.startswith('/api/'):
            self.send_api_response()
        elif self.path == '/' or self.path == '/index':
            self.path = '/dashboard/index.html'
            super().do_GET()
        else:
            super().do_GET()
    
    def send_api_response(self):
        import redis, faiss, networkx as nx
        sys.path.insert(0, BRAIN_DIR)
        
        # Build state
        state = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agents": [],
            "vectors": 0,
            "graph_nodes": 0,
            "graph_edges": 0,
            "episodes": 0,
            "drive_sync": "operational",
            "status": "healthy"
        }
        
        try:
            r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            r.ping()
            import re
            all_keys = r.keys('brain:agent:*')
            clean_keys = set()
            for k in all_keys:
                key = k.replace('brain:agent:', '')
                if not re.match(r'^[a-z_-]+:[a-f0-9]+$', key.lower()):
                    clean_keys.add(key)
            state["agents"] = list(clean_keys)
            state["agent_count"] = len(clean_keys)
        except:
            state["agents"] = []
            state["agent_count"] = 0
        
        try:
            import numpy as np
            sys.path.insert(0, BRAIN_DIR)
            meta_path = f"{BRAIN_DIR}/vectors/meta.json"
            if os.path.exists(meta_path):
                with open(meta_path) as f:
                    m = json.load(f)
                    state["vectors"] = m.get("count", 0)
            
            idx_path = f"{BRAIN_DIR}/vectors/brain.index"
            if os.path.exists(idx_path):
                state["vector_index_bytes"] = os.path.getsize(idx_path)
        except:
            pass
        
        try:
            gml_path = f"{BRAIN_DIR}/graph/brain.graphml"
            if os.path.exists(gml_path):
                G = nx.read_graphml(gml_path)
                state["graph_nodes"] = G.number_of_nodes()
                state["graph_edges"] = G.number_of_edges()
        except:
            pass
        
        try:
            db_path = f"{BRAIN_DIR}/memory/episodic.db"
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                state["episodes"] = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
                conn.close()
        except:
            pass
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(state, indent=2).encode())
    
    def do_POST(self):
        """Handle POST requests - heartbeat, agent registration, etc."""
        import redis, sqlite3, os, networkx as nx
        from datetime import datetime, timezone
        
        BRAIN_DIR = '/config/brain'
        path = self.path
        
        if path == '/api/heartbeat':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                agent_id = data.get('agent', 'unknown')
                status = data.get('status', 'active')
                
                # Update Redis working memory
                r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                r.set(f"agent:{agent_id}", json.dumps({"status": status, "timestamp": datetime.now(timezone.utc).isoformat()}), ex=300)
                
                # Log to episodic
                db_path = f"{BRAIN_DIR}/memory/episodic.db"
                if os.path.exists(db_path):
                    conn = sqlite3.connect(db_path)
                    conn.execute("INSERT INTO episodes (agent, action, target, result, tags, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                        (agent_id, 'heartbeat', '', status, '["heartbeat"]', datetime.now(timezone.utc).isoformat()))
                    conn.commit()
                    conn.close()
                
                response = {"status": "ok", "agent": agent_id, "timestamp": datetime.now(timezone.utc).isoformat()}
            except Exception as e:
                response = {"status": "error", "message": str(e)}
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Silent

os.chdir(BRAIN_DIR)
server = HTTPServer(('0.0.0.0', PORT), Handler)
print(f"🌐 AkpanBrain Dashboard → http://localhost:{PORT}")
print(f"   API State → http://localhost:{PORT}/api/state")
sys.stdout.flush()
server.serve_forever()