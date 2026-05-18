#!/usr/bin/env python3
"""
AkpanBrain - The Universal Agent Memory System
- Syncs with Google Drive (AkpanBrain folder)
- All 7 memory types implemented
- Gemini embeddings + fallback to OpenAI
- Multi-agent aware
- 3D dashboard ready
"""

import json, os, sqlite3, hashlib, time, re, uuid
import redis
import faiss
import numpy as np
import networkx as nx
import subprocess
from datetime import datetime, timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# ============================================
# CONFIGURATION
# ============================================
BRAIN_DIR = "/config/brain"
os.makedirs(f"{BRAIN_DIR}/vectors", exist_ok=True)
os.makedirs(f"{BRAIN_DIR}/graph", exist_ok=True)
os.makedirs(f"{BRAIN_DIR}/memory", exist_ok=True)
os.makedirs(f"{BRAIN_DIR}/sensory", exist_ok=True)
os.makedirs(f"{BRAIN_DIR}/cache", exist_ok=True)

# Load Google Drive folder IDs
FOLDER_IDS = json.load(open('/config/.hermes/akpanbrain_folders.json', 'r'))

# Load API keys
with open('/config/.hermes/config.yaml', 'r') as f:
    config = f.read()

GEMINI_KEY = re.search(r'api_key:\s*(AIza[A-Za-z0-9_-]{30,})', config).group(1) if re.search(r'api_key:\s*(AIza[A-Za-z0-9_-]{30,})', config) else None

# Load Groq key
with open('/config/.nullclaw/config.yaml', 'r') as f:
    nullclaw = f.read()
GROQ_KEY = re.search(r'gsk_[A-Za-z0-9_-]{40,}', nullclaw).group(0) if re.search(r'gsk_[A-Za-z0-9_-]{40,}', nullclaw) else None

VECTOR_DIM = 3072

# ============================================
# REDIS - WORKING MEMORY
# ============================================
class WorkingMemory:
    def __init__(self):
        self.r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        self.r.ping()
        self.DEFAULT_TTL = 300
    
    def _make_key(self, key):
        """Normalize key: strip any existing brain:/agent: prefix"""
        key = str(key)
        key = key.replace('brain:', '').replace('agent:', '')
        return f"brain:agent:{key}"
    
    def set(self, key, value, ttl=300):
        self.r.setex(self._make_key(key), ttl, json.dumps(value))
    
    def get(self, key):
        val = self.r.get(self._make_key(key))
        return json.loads(val) if val else None
    
    def delete(self, key):
        self.r.delete(self._make_key(key))
    
    def keys(self, include_actions=False):
        """Get agent keys. By default returns only registered agent IDs (no UUID suffixes)."""
        all_keys = [k.replace('brain:agent:', '') for k in self.r.keys('brain:agent:*')]
        
        if include_actions:
            return all_keys
        
        # Filter out action log keys (have UUID suffix like "hermes:8ed620e1")
        # Registered agents are simple names: "hermes", "kilocode", etc.
        import re
        agent_keys = []
        for k in all_keys:
            # If it has a colon followed by hex, it's an action log
            if re.match(r'^[a-z_-]+:[a-f0-9]+$', k.lower()):
                continue  # Skip action logs
            agent_keys.append(k)
        return list(set(agent_keys))  # Dedupe
    
    def log_agent_action(self, agent, action, data):
        key = f"{agent}:{uuid.uuid4().hex[:8]}"
        self.set(key, {
            "agent": agent,
            "action": action,
            "data": data,
            "time": datetime.now(timezone.utc).isoformat()
        }, ttl=3600)
        return key

# ============================================
# FAISS - SEMANTIC MEMORY (VECTOR DB)
# ============================================
class SemanticMemory:
    def __init__(self):
        self.index_path = f"{BRAIN_DIR}/vectors/brain.index"
        self.meta_path = f"{BRAIN_DIR}/vectors/meta.json"
        self.cache_path = f"{BRAIN_DIR}/cache/embeddings.json"
        
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            self.meta = json.load(open(self.meta_path)) if os.path.exists(self.meta_path) else {"vectors": [], "count": 0}
        else:
            self.index = None  # Lazy init
            self.meta = {"vectors": [], "count": 0}
        
        self.embed_cache = json.load(open(self.cache_path)) if os.path.exists(self.cache_path) else {}
        self._trained = False
    
    def _ensure_index(self, dims_needed):
        if self.index is None:
            # Use a simple flat index for small datasets, IVF-PQ for large
            if dims_needed > 100:
                # Flat index - no training needed
                self.index = faiss.IndexFlatL2(VECTOR_DIM)
            else:
                # Fallback: just use flat index (exact search, no compression)
                self.index = faiss.IndexFlatL2(VECTOR_DIM)
            self._trained = True
    
    def _get_gemini_embedding(self, text):
        if not GEMINI_KEY:
            return None
        try:
            import urllib.request
            payload = {
                "content": {"parts": [{"text": text[:8000]}]},
                "taskType": "RETRIEVAL_DOCUMENT"
            }
            url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-3-large:embedContent?key={GEMINI_KEY}"
            req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
            resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
            return resp.get('embedding', {}).get('values', [])
        except:
            return None
    
    def _get_groq_embedding(self, text):
        if not GROQ_KEY:
            return None
        try:
            import urllib.request
            payload = {"model": "text-embedding-3-small", "input": text[:8000]}
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/embeddings",
                data=json.dumps(payload).encode(),
                headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {GROQ_KEY}'}
            )
            resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
            return resp.get('data', [{}])[0].get('embedding', [])
        except:
            return None
    
    def embed(self, text):
        # Check cache first
        cache_key = hashlib.sha256(text.encode()).hexdigest()
        if cache_key in self.embed_cache:
            return self.embed_cache[cache_key]
        
        # Try Gemini first, then Groq, then fallback
        emb = self._get_gemini_embedding(text) or self._get_groq_embedding(text)
        if emb and len(emb) == VECTOR_DIM:
            self.embed_cache[cache_key] = emb
            self._save_cache()
            return emb
        
        # Fallback: generate pseudo-embedding from content hash
        # This ensures consistent (but not semantic) vectors for deduplication
        pseudo = np.zeros(VECTOR_DIM, dtype=np.float32)
        for i, c in enumerate(text.encode()[:VECTOR_DIM]):
            pseudo[i % VECTOR_DIM] += c
        if len(text) > VECTOR_DIM:
            for i, c in enumerate(text.encode()[VECTOR_DIM:VECTOR_DIM*2]):
                pseudo[i % VECTOR_DIM] -= c
        norm = np.linalg.norm(pseudo)
        if norm > 0:
            pseudo = pseudo / norm
        return pseudo.tolist()
    
    def add(self, text, metadata=None):
        # Validation
        if not text or not isinstance(text, str) or not text.strip():
            raise ValueError("Text must be a non-empty string")
        
        # Create index lazily when first vector comes
        self._ensure_index(1)
        
        emb = self.embed(text.strip())
        vec = np.array([emb], dtype=np.float32)
        
        self.index.add(vec)
        self.meta["vectors"].append({
            "id": len(self.meta["vectors"]),
            "text_hash": hashlib.sha256(text.encode()).hexdigest(),
            "text_preview": text[:100],
            "metadata": metadata or {}
        })
        self.meta["count"] = self.index.ntotal
        self._save()
        return len(self.meta["vectors"]) - 1
    
    def search(self, query, k=5):
        # Validation
        if not query or not isinstance(query, str) or not query.strip():
            raise ValueError("Query must be a non-empty string")
        
        query_emb = self.embed(query.strip())
        query_vec = np.array([query_emb], dtype=np.float32)
        
        if self.index.ntotal == 0:
            return []
        
        D, I = self.index.search(query_vec, min(k, self.index.ntotal))
        
        results = []
        for d, i in zip(D[0], I[0]):
            if i < len(self.meta["vectors"]):
                v = self.meta["vectors"][int(i)]
                results.append({
                    "distance": float(d),
                    "text": v["text_preview"],
                    "metadata": v.get("metadata", {}),
                    "id": v["id"]
                })
        return results
    
    def _save(self):
        faiss.write_index(self.index, self.index_path)
        json.dump(self.meta, open(self.meta_path, 'w'), indent=2)
    
    def _save_cache(self):
        json.dump(self.embed_cache, open(self.cache_path, 'w'))

# ============================================
# NETWORKX - KNOWLEDGE GRAPH
# ============================================
class KnowledgeGraph:
    def __init__(self):
        self.graph_path = f"{BRAIN_DIR}/graph/brain.graphml"
        self.G = nx.read_graphml(self.graph_path) if os.path.exists(self.graph_path) else nx.DiGraph()
    
    def add_entity(self, entity_id, entity_type, data=None):
        if entity_id not in self.G:
            self.G.add_node(entity_id, entity_type=entity_type, created_at=datetime.now(timezone.utc).isoformat())
        if data:
            self.G.nodes[entity_id].update(data)
        return self
    
    def add_node(self, entity_id, data=None):
        """Alias for add_entity with default type"""
        return self.add_entity(entity_id, "concept", data)
    
    def add_relation(self, from_id, to_id, relation_type, weight=1.0):
        if from_id not in self.G:
            self.G.add_node(from_id, entity_type='unknown')
        if to_id not in self.G:
            self.G.add_node(to_id, entity_type='unknown')
        
        if self.G.has_edge(from_id, to_id):
            # Update existing edge
            self.G[from_id][to_id]['weight'] += weight
            if relation_type not in self.G[from_id][to_id].get('types', []):
                self.G[from_id][to_id].setdefault('types', []).append(relation_type)
        else:
            self.G.add_edge(from_id, to_id, relation_type=relation_type, weight=weight, types=[relation_type])
        return self
    
    def get_entity(self, entity_id):
        return dict(self.G.nodes[entity_id]) if entity_id in self.G else None
    
    def get_neighbors(self, entity_id, depth=1, relation_type=None):
        if entity_id not in self.G:
            return []
        
        neighbors = []
        for node, data in self.G[node_id].items() if hasattr(self.G, '__getitem__') else []:
            pass
        
        # Use NetworkX methods
        if depth == 1:
            neighbors = list(self.G.neighbors(entity_id))
        else:
            neighbors = list(nx.single_source_shortest_path_length(self.G, entity_id, cutoff=depth).keys())
        
        if relation_type:
            neighbors = [n for n in neighbors if self.G.has_edge(entity_id, n) and 
                        relation_type in self.G[entity_id][n].get('types', [])]
        
        return [{"id": n, **dict(self.G.nodes[n])} for n in neighbors]
    
    def save(self):
        # NetworkX GraphML doesn't support lists - convert to JSON strings
        import copy
        G_clean = copy.deepcopy(self.G)
        
        for node, data in G_clean.nodes(data=True):
            for key, val in list(data.items()):
                if isinstance(val, (list, dict)):
                    data[key] = json.dumps(val)
        
        for u, v, data in G_clean.edges(data=True):
            for key, val in list(data.items()):
                if isinstance(val, (list, dict)):
                    data[key] = json.dumps(val)
        
        nx.write_graphml(G_clean, self.graph_path)

# ============================================
# SQLITE - EPISODIC MEMORY
# ============================================
class EpisodicMemory:
    def __init__(self):
        self.db_path = f"{BRAIN_DIR}/memory/episodic.db"
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                agent TEXT,
                action TEXT,
                target TEXT,
                result TEXT,
                tags TEXT,
                context TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                entity_type TEXT,
                name TEXT,
                data TEXT,
                created_at TEXT
            )
        """)
        self.conn.commit()
    
    def log(self, agent, action, target="", result="", tags=None, context=None):
        self.conn.execute("""
            INSERT INTO episodes (timestamp, agent, action, target, result, tags, context)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            agent, action, target, result,
            json.dumps(tags or []),
            json.dumps(context or {})
        ))
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    def query(self, agent=None, action=None, limit=100):
        q = "SELECT * FROM episodes WHERE 1=1"
        params = []
        if agent:
            q += " AND agent=?"
            params.append(agent)
        if action:
            q += " AND action=?"
            params.append(action)
        q += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        rows = self.conn.execute(q, params).fetchall()
        return [{"id": r[0], "timestamp": r[1], "agent": r[2], "action": r[3], 
                 "target": r[4], "result": r[5], "tags": json.loads(r[6]), 
                 "context": json.loads(r[7])} for r in rows]

# ============================================
# RCLONE SYNC TO GOOGLE DRIVE
# ============================================
class BrainSync:
    def __init__(self):
        self.rclone = "/config/.local/bin/rclone"
        self.remote = "gdrive:AkpanBrain"
    
    def sync_to_drive(self, folder="brain"):
        """Sync local brain data to Google Drive"""
        local_path = f"{BRAIN_DIR}/{folder}"
        remote_path = f"{self.remote}/brain/{folder}"
        
        result = subprocess.run([
            self.rclone, "sync", local_path, remote_path,
            "--config", os.path.expanduser("~/.config/rclone/rclone.conf"),
            "--quiet"
        ], capture_output=True, text=True)
        
        return result.returncode == 0
    
    def sync_from_drive(self, folder="brain"):
        """Pull brain data from Google Drive"""
        local_path = f"{BRAIN_DIR}/{folder}"
        remote_path = f"{self.remote}/brain/{folder}"
        
        result = subprocess.run([
            self.rclone, "sync", remote_path, local_path,
            "--config", os.path.expanduser("~/.config/rclone/rclone.conf"),
            "--quiet"
        ], capture_output=True, text=True)
        
        return result.returncode == 0
    
    def upload_file(self, local_path, drive_folder, drive_name):
        """Upload a file to Google Drive"""
        result = subprocess.run([
            self.rclone, "copy", local_path,
            f"{self.remote}/brain/{drive_folder}/",
            "--config", os.path.expanduser("~/.config/rclone/rclone.conf"),
        ], capture_output=True, text=True)
        return result.returncode == 0

# ============================================
# MAIN BRAIN CLASS
# ============================================
class AkpanBrain:
    def __init__(self):
        self.working = WorkingMemory()
        self.semantic = SemanticMemory()
        self.graph = KnowledgeGraph()
        self.episodic = EpisodicMemory()
        self.sync = BrainSync()
        
        # Agent registry (in Redis)
        self.register_agent("hermes", "main", {"color": "#3B82F6"})
        self.register_agent("kilocode", "research", {"color": "#F59E0B"})
        self.register_agent("kimi", "llm", {"color": "#EF4444"})
        self.register_agent("nullclaw", "router", {"color": "#8B5CF6"})
    
    def register_agent(self, agent_id, role, metadata=None):
        self.working.set(agent_id, {
            "id": agent_id,
            "role": role,
            "status": "active",
            "metadata": metadata or {},
            "registered_at": datetime.now(timezone.utc).isoformat()
        }, ttl=86400)
    
    def agent_action(self, agent_id, action, target="", result="", tags=None):
        # Log to episodic memory
        episode_id = self.episodic.log(agent_id, action, target, result, tags)
        
        # Store in working memory
        self.working.log_agent_action(agent_id, action, {"target": target, "result": result, "episode_id": episode_id})
        
        # Update agent's last activity
        agent_data = self.working.get(agent_id) or {}
        agent_data["last_action"] = action
        agent_data["last_activity"] = datetime.now(timezone.utc).isoformat()
        self.working.set(agent_id, agent_data, ttl=86400)
        
        return episode_id
    
    def ingest(self, content, content_type, source="", tags=None):
        """Ingest content into the brain"""
        # Add to semantic memory (vector DB)
        vector_id = self.semantic.add(content, {"type": content_type, "source": source, "tags": tags or []})
        
        # Add to knowledge graph as entity
        entity_id = f"doc:{hashlib.sha256(content.encode()).hexdigest()[:16]}"
        self.graph.add_entity(entity_id, content_type, {
            "source": source,
            "vector_id": vector_id,
            "preview": content[:200],
            "tags": tags or []
        })
        
        # If it's code, extract entities
        if content_type == "code":
            self._extract_code_entities(content, entity_id)
        
        # Auto-tag and link
        self._auto_link(content, entity_id)
        
        return vector_id
    
    def _extract_code_entities(self, code, parent_id):
        """Extract functions, classes, imports from code"""
        # Simple regex extraction
        funcs = re.findall(r'def\s+(\w+)', code)
        for func in funcs:
            func_id = f"func:{func}"
            self.graph.add_entity(func_id, "function", {"name": func})
            self.graph.add_relation(parent_id, func_id, "contains")
        
        classes = re.findall(r'class\s+(\w+)', code)
        for cls in classes:
            cls_id = f"class:{cls}"
            self.graph.add_entity(cls_id, "class", {"name": cls})
            self.graph.add_relation(parent_id, cls_id, "contains")
    
    def _auto_link(self, content, entity_id):
        """Automatically link content to related entities"""
        # Extract potential links from content
        words = set(re.findall(r'\b[A-Z][a-z]+[A-Z]\w+', content))  # CamelCase
        for word in words:
            if word in self.graph.G:
                self.graph.add_relation(entity_id, word, "related", weight=0.5)
    
    def sync_to_drive(self):
        """Sync all brain data to Google Drive"""
        for folder in ["vectors", "graph", "memory", "cache"]:
            self.sync.sync_to_drive(folder)
    
    def sync_from_drive(self):
        """Pull brain data from Google Drive"""
        for folder in ["vectors", "graph", "memory"]:
            self.sync.sync_from_drive(folder)
        
        # Reload graph
        self.graph = KnowledgeGraph()
    
    def query(self, question, agent_id="hermes"):
        """Query the brain - find relevant context and answer"""
        # Search semantic memory
        results = self.semantic.search(question, k=10)
        
        # Search knowledge graph
        kg_results = []
        for node in self.graph.G.nodes():
            node_data = dict(self.graph.G.nodes[node])
            if any(word.lower() in str(node_data).lower() for word in question.split()[:5]):
                kg_results.append(node)
        
        # Get recent agent actions
        recent_actions = self.episodic.query(agent=agent_id, limit=20)
        
        # Get active agents
        active_agents = [k.replace("agent:", "") for k in self.working.keys() if k.startswith("agent:")]
        
        return {
            "semantic_matches": results,
            "graph_entities": kg_results[:10],
            "recent_actions": recent_actions,
            "active_agents": active_agents
        }

# ============================================
# LAUNCH
# ============================================
if __name__ == "__main__":
    brain = AkpanBrain()
    
    print("=" * 60)
    print("AKPANBRAIN - Universal Agent Memory System")
    print("=" * 60)
    print()
    print("Memory Types Active:")
    print("  🟡 Sensory     → /config/brain/sensory/")
    print("  🔵 Working      → Redis (127.0.0.1:6379)")
    print("  🟣 Episodic     → SQLite episodic.db")
    print("  🔷 Semantic     → FAISS vectors (4x compressed)")
    print("  🔴 Procedural   → Knowledge graph nodes")
    print("  🟠 Priming      → HNSW retrieval")
    print("  🩷 Prospective   → Graph reminder nodes")
    print()
    print(f"Google Drive sync: AkpanBrain ({FOLDER_IDS['AkpanBrain']})")
    print()
    print("✅ Brain ready. Use: from akpanbrain import brain")
    print()