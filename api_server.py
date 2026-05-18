#!/usr/bin/env python3
"""
AkpanBrain API Server v2 — WebSocket + REST
- Real-time agent auto-detection (process + Redis + CLI + subagent tree)
- Accurate status: only active when actually running
- Subagent tracking via Redis keys
- WebSocket for live dashboard updates
- Neuron→file associations
- Built-in nullclaw dashboard page (not raw JSON)
"""
import json, os, sqlite3, time, subprocess, hashlib, glob, re, threading, socket
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs
import redis
import struct

BRAIN_DIR = "/config/brain"
DASHBOARD_DIR = f"{BRAIN_DIR}/dashboard"
PORT = 8199
WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
ws_clients = []

# ─── Agent Signatures ─── Every CLI coding agent we know about
AGENT_SIGNATURES = {
    "hermes": {"cmd": "hermes", "color": "#3B82F6", "type": "reasoning", "desc": "Hermes Agent — autonomous AI agent orchestrator. Routes tasks to subagents, manages cron, memory, skills.", "region": "working"},
    "gemini-cli": {"cmd": "gemini", "color": "#4285F4", "type": "search", "desc": "Google Gemini CLI — search-augmented LLM with Google grounding. Function calling limited to gemini-* models.", "region": "semantic"},
    "kilo-code": {"cmd": "kilo", "color": "#F59E0B", "type": "coding", "desc": "Kilo Code — lightweight coding agent. CLI-based code generation and editing.", "region": "procedural"},
    "kimi-code": {"cmd": "kimi", "color": "#EF4444", "type": "coding", "desc": "Kimi Code (Moonshot) — coding agent with large context window. Chinese LLM backend.", "region": "procedural"},
    "nullclaw": {"cmd": "nullclaw", "color": "#8B5CF6", "type": "routing", "desc": "Nullclaw AI Router — local brain with 999 concurrent connections. Routes between all agents and models.", "region": "working"},
    "claude-code": {"cmd": "claude", "color": "#D97706", "type": "coding", "desc": "Claude Code (Anthropic) — agentic coding CLI. Reads codebase, makes edits, runs tests, creates PRs.", "region": "procedural"},
    "opencode": {"cmd": "opencode", "color": "#10B981", "type": "coding", "desc": "OpenCode — open-source coding agent. TUI-based code editing and review.", "region": "procedural"},
    "qwen-code": {"cmd": "qwen-code", "color": "#6366F1", "type": "llm", "desc": "Qwen Code (Alibaba) — coding agent built on Qwen LLM. Strong multi-language support.", "region": "procedural"},
    "codebuff": {"cmd": "codebuff", "color": "#EC4899", "type": "coding", "desc": "CodeBuff — AI coding assistant. Focus on code quality and refactoring.", "region": "procedural"},
    "jcode": {"cmd": "jcode", "color": "#64748B", "type": "coding", "desc": "JCode — JavaScript/TypeScript focused coding agent. Discord bridge integration.", "region": "episodic"},
    "claw-code": {"cmd": "claw-code-agent", "color": "#F97316", "type": "coding", "desc": "Claw Code — coding agent variant. Part of the Claw family.", "region": "procedural"},
    "cline": {"cmd": "cline", "color": "#06B6D4", "type": "coding", "desc": "Cline — autonomous coding agent for VS Code. Plans, creates, edits files with human approval.", "region": "procedural"},
    "ironclaw": {"cmd": "ironclaw", "color": "#A855F7", "type": "security", "desc": "IronClaw — security-hardened agent runner. Sandboxes external code, enforces safety policies.", "region": "working"},
    "openfang": {"cmd": "cli-anything-openfang", "color": "#EF4444", "type": "coding", "desc": "OpenFang — CLI-anything coding agent. Community-driven fork with enhanced features.", "region": "procedural"},
    "codex": {"cmd": "codex", "color": "#22D3EE", "type": "coding", "desc": "OpenAI Codex CLI — agentic coding. Plans features, writes code, creates PRs via OpenAI models.", "region": "procedural"},
}

# ─── Brain Region Definitions ───
BRAIN_REGIONS = {
    "semantic": {
        "name": "Semantic Cortex", "backend": "FAISS", "color": "#00f5ff",
        "description": "Long-term semantic memory store. Stores embedded vectors for concept retrieval. Uses FAISS int8 quantization for 4x RAM savings.",
        "location": "Parietal Lobe (top-back)",
        "functions": ["Vector embedding storage", "Similarity search", "Concept retrieval", "TF-IDF fallback (Gemini on hold)"],
        "capacity": "Unlimited (disk-backed index)", "status": "active",
        "file": f"{BRAIN_DIR}/vectors/brain.index",
        "folder": f"{BRAIN_DIR}/vectors/",
        "groups": ["embeddings", "vectors", "search"],
    },
    "graph": {
        "name": "Knowledge Graph", "backend": "NetworkX + GraphML", "color": "#00ff9d",
        "description": "Relational knowledge store. Maps connections between concepts, agents, and processes. Supports graph traversal patterns for multi-hop reasoning.",
        "location": "Hippocampus (deep center)",
        "functions": ["Entity relationships", "Graph traversal", "Multi-hop reasoning", "Agent dependency mapping"],
        "capacity": "Memory-limited (104 nodes currently)", "status": "active",
        "file": f"{BRAIN_DIR}/graph/brain.graphml",
        "folder": f"{BRAIN_DIR}/graph/",
        "groups": ["knowledge", "relationships", "graph-traversal"],
    },
    "episodic": {
        "name": "Episodic Memory", "backend": "SQLite", "color": "#f59e0b",
        "description": "Time-stamped episode storage. Records what happened, when, and which agent was involved. Supports chronological recall and pattern detection.",
        "location": "Temporal Lobe (sides)",
        "functions": ["Event logging", "Chronological recall", "Agent activity history", "Pattern detection across time"],
        "capacity": "Unlimited (disk-backed SQLite)", "status": "active",
        "file": f"{BRAIN_DIR}/memory/episodic.db",
        "folder": f"{BRAIN_DIR}/memory/",
        "groups": ["episodes", "timeline", "history"],
    },
    "working": {
        "name": "Working Memory", "backend": "Redis", "color": "#ff2d55",
        "description": "Short-term high-speed scratchpad. Current task context, active agent states, real-time coordination data. Volatile — TTL 1hr default.",
        "location": "Prefrontal Cortex (front)",
        "functions": ["Active task context", "Agent state tracking", "Real-time coordination", "Session management"],
        "capacity": "Memory-limited (volatile, TTL-based)", "status": "active", "port": 6379,
        "folder": f"{BRAIN_DIR}/cache/",
        "groups": ["redis", "realtime", "coordination"],
    },
    "procedural": {
        "name": "Procedural Cortex", "backend": "Skills (SKILL.md)", "color": "#8b5cf6",
        "description": "Learned procedures and workflows. Stores reusable skills, code patterns, and operational knowledge. Auto-loads relevant skills per task.",
        "location": "Motor Cortex (top strip)",
        "functions": ["Skill storage and retrieval", "Workflow patterns", "Code generation templates", "Auto-skill loading"],
        "capacity": "Unlimited (file-based, synced to Drive)", "status": "active",
        "file": f"{BRAIN_DIR}/skills/",
        "folder": f"{BRAIN_DIR}/skills/",
        "groups": ["skills", "procedures", "workflows"],
    },
    "sensory": {
        "name": "Sensory Buffer", "backend": "File Watcher", "color": "#ff6b35",
        "description": "Short-term input buffer. Watches filesystem for new files, changes, and events. Auto-ingests new data into appropriate brain regions.",
        "location": "Sensory Cortex (front strip)",
        "functions": ["File change detection", "New file ingestion", "Event buffering", "Trigger cascading brain updates"],
        "capacity": "Fixed-size ring buffer", "status": "active",
        "folder": f"{BRAIN_DIR}/sensory/",
        "groups": ["files", "watcher", "ingestion"],
    },
}

# Neuron → file associations (region → files in that region's folder)
def get_region_files(region_name):
    """Get files associated with a brain region"""
    region = BRAIN_REGIONS.get(region_name, {})
    folder = region.get("folder", "")
    files = []
    if folder and os.path.exists(folder):
        for f in glob.glob(f"{folder}**/*", recursive=True):
            if os.path.isfile(f):
                rel = os.path.relpath(f, BRAIN_DIR)
                size = os.path.getsize(f)
                files.append({"path": rel, "size": size, "name": os.path.basename(f)})
    # Also add the main file if specified
    main_file = region.get("file", "")
    if main_file and os.path.exists(main_file):
        rel = os.path.relpath(main_file, BRAIN_DIR)
        if not any(f["path"] == rel for f in files):
            files.insert(0, {"path": rel, "size": os.path.getsize(main_file), "name": os.path.basename(main_file), "primary": True})
    return files

# Redis connection
try:
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    r.ping()
    redis_ok = True
except:
    redis_ok = False
    r = None

def get_process_agents():
    """Auto-detect agents by scanning running processes — STRICT matching only"""
    agents = {}
    try:
        ps = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
        procs = ps.stdout
        procs_lower = procs.lower()
        for name, sig in AGENT_SIGNATURES.items():
            cmd = sig["cmd"].lower()
            # Strict: match full command word, not substring
            # e.g. "gemini" should NOT match "gemini-cli" process
            found = False
            for line in procs.split('\n'):
                line_lower = line.lower()
                if 'grep' in line_lower or 'python3 api_server' in line_lower:
                    continue
                # Check if the command appears as a distinct word in the process
                parts = line_lower.split()
                # Check COMMAND column (after column 10 typically)
                cmdline = ' '.join(parts[10:]) if len(parts) > 10 else ''
                # Match as word boundary
                if re.search(r'\b' + re.escape(cmd) + r'\b', cmdline):
                    parts = line.strip().split()
                    pid = parts[1] if len(parts) > 1 else "?"
                    cpu = parts[2] if len(parts) > 2 else "?"
                    mem = parts[3] if len(parts) > 3 else "?"
                    agents[name] = {
                        "status": "active",
                        "color": sig["color"],
                        "type": sig["type"],
                        "desc": sig["desc"],
                        "region": sig["region"],
                        "last_activity": str(int(time.time() * 1000)),
                        "last_action": "Process running (PID " + pid + ")",
                        "pid": pid,
                        "cpu": cpu,
                        "mem": mem,
                        "detected_by": "process_scan",
                        "objective": get_agent_objective(name),
                        "plans": get_agent_plans(name),
                        "interactions": get_agent_interactions(name),
                        "subagents": get_subagents(name),
                    }
                    found = True
                    break

            # Special: nullclaw detected via 9router process
            if name == "nullclaw" and not found:
                for line in procs.split('\n'):
                    line_lower = line.lower()
                    if ('9router' in line_lower or 'nullclaw' in line_lower) and 'grep' not in line_lower:
                        # Check if it's actually the 9router/nullclaw service
                        if 'node' in line_lower or 'pnpm' in line_lower or 'nullclaw' in line_lower:
                            parts = line.strip().split()
                            agents["nullclaw"] = {
                                "status": "active",
                                "color": AGENT_SIGNATURES["nullclaw"]["color"],
                                "type": AGENT_SIGNATURES["nullclaw"]["type"],
                                "desc": AGENT_SIGNATURES["nullclaw"]["desc"],
                                "region": AGENT_SIGNATURES["nullclaw"]["region"],
                                "last_activity": str(int(time.time() * 1000)),
                                "last_action": "9Router service active",
                                "pid": parts[1] if len(parts) > 1 else "?",
                                "cpu": parts[2] if len(parts) > 2 else "?",
                                "mem": parts[3] if len(parts) > 3 else "?",
                                "detected_by": "service_scan",
                                "objective": get_agent_objective("nullclaw"),
                                "plans": get_agent_plans("nullclaw"),
                                "interactions": get_agent_interactions("nullclaw"),
                                "subagents": get_subagents("nullclaw"),
                            }
                            found = True
                            break

            # Special: hermes detected via python3 hermes process
            if name == "hermes" and not found:
                for line in procs.split('\n'):
                    line_lower = line.lower()
                    if 'hermes' in line_lower and 'grep' not in line_lower and 'api_server' not in line_lower:
                        parts = line.strip().split()
                        agents["hermes"] = {
                            "status": "active",
                            "color": AGENT_SIGNATURES["hermes"]["color"],
                            "type": AGENT_SIGNATURES["hermes"]["type"],
                            "desc": AGENT_SIGNATURES["hermes"]["desc"],
                            "region": AGENT_SIGNATURES["hermes"]["region"],
                            "last_activity": str(int(time.time() * 1000)),
                            "last_action": "Hermes agent process running",
                            "pid": parts[1] if len(parts) > 1 else "?",
                            "cpu": parts[2] if len(parts) > 2 else "?",
                            "mem": parts[3] if len(parts) > 3 else "?",
                            "detected_by": "process_scan",
                            "objective": get_agent_objective("hermes"),
                            "plans": get_agent_plans("hermes"),
                            "interactions": get_agent_interactions("hermes"),
                            "subagents": get_subagents("hermes"),
                        }
                        found = True
                        break
    except Exception as e:
        pass
    return agents

def get_subagents(agent_name):
    """Get subagents/children of an agent from Redis or process list"""
    subagents = []
    # Check Redis for registered subagents
    if redis_ok:
        try:
            # Hermes-style subagent tracking
            keys = r.keys(f"subagent:{agent_name}:*")
            for k in keys[:10]:
                data = r.get(k)
                if data:
                    try:
                        d = json.loads(data)
                        subagents.append({
                            "id": d.get("id", k.split(":")[-1]),
                            "status": d.get("status", "unknown"),
                            "task": d.get("task", d.get("goal", "unknown")),
                            "started": d.get("started", ""),
                        })
                    except:
                        subagents.append({"id": k.split(":")[-1], "status": "unknown", "task": "unknown"})
        except:
            pass

        # Also check delegate_task patterns
        try:
            keys = r.keys(f"delegate:{agent_name}:*")
            for k in keys[:10]:
                data = r.get(k)
                if data:
                    try:
                        d = json.loads(data)
                        subagents.append({
                            "id": d.get("id", k.split(":")[-1]),
                            "status": d.get("status", "running"),
                            "task": d.get("goal", d.get("task", "delegated task")),
                            "started": d.get("started", ""),
                        })
                    except:
                        pass
        except:
            pass

    # If this is hermes, also check for any hermes subagent processes
    if agent_name == "hermes":
        try:
            ps = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
            for line in ps.stdout.split('\n'):
                ll = line.lower()
                if ('hermes' in ll or 'delegate' in ll) and 'grep' not in ll and 'api_server' not in ll:
                    parts = line.strip().split()
                    pid = parts[1] if len(parts) > 1 else "?"
                    if pid != "?":
                        subagents.append({
                            "id": f"proc-{pid}",
                            "status": "active",
                            "task": ' '.join(parts[10:][:3]) if len(parts) > 10 else "hermes subprocess",
                            "started": "",
                        })
        except:
            pass

    return subagents[:15]

def get_redis_agents():
    """Get agents registered in Redis working memory"""
    agents = {}
    if not redis_ok:
        return agents
    try:
        for key in r.keys("agent:*"):
            agent_id = key.replace("brain:agent:", "").replace("agent:", "")
            data = r.get(key)
            if data:
                try:
                    d = json.loads(data)
                    agents[agent_id] = {
                        "status": d.get("status", "unknown"),
                        "color": d.get("metadata", {}).get("color", AGENT_SIGNATURES.get(agent_id, {}).get("color", "#888")),
                        "type": d.get("metadata", {}).get("type", "unknown"),
                        "last_activity": d.get("last_activity", ""),
                        "last_action": d.get("last_action", ""),
                        "registered_at": d.get("registered_at", ""),
                        "detected_by": "redis",
                        "subagents": d.get("subagents", []),
                    }
                except:
                    pass
    except:
        pass
    return agents

def get_cli_agents():
    """Detect agents by checking if their CLI binary exists — these are INSTALLED only, NOT active"""
    agents = {}
    for name, sig in AGENT_SIGNATURES.items():
        cmd = sig["cmd"]
        try:
            result = subprocess.run(["which", cmd], capture_output=True, text=True, timeout=3)
            if result.returncode == 0 and result.stdout.strip():
                agents[name] = {
                    "status": "installed",
                    "color": sig["color"],
                    "type": sig["type"],
                    "desc": sig["desc"],
                    "region": sig["region"],
                    "path": result.stdout.strip(),
                    "detected_by": "cli_scan"
                }
        except:
            pass
    return agents

def get_agent_objective(name):
    """Determine what an agent is currently working on"""
    if redis_ok:
        try:
            task = r.get(f"task:{name}")
            if task:
                return task
        except:
            pass
    try:
        db_path = f"{BRAIN_DIR}/memory/episodic.db"
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            row = conn.execute(
                "SELECT action, content FROM episodes WHERE agent_id=? ORDER BY timestamp DESC LIMIT 1",
                (name,)
            ).fetchone()
            conn.close()
            if row:
                return f"{row[0]}: {row[1][:100]}"
    except:
        pass
    sig = AGENT_SIGNATURES.get(name, {})
    atype = sig.get("type", "")
    defaults = {
        "reasoning": "Orchestrating tasks and routing to optimal agents",
        "coding": "Awaiting code task assignment",
        "search": "Available for search-augmented queries",
        "routing": "Managing agent connections and model routing",
        "security": "Monitoring code safety and sandbox policies",
        "llm": "Available for language model tasks",
    }
    return defaults.get(atype, "Idle — awaiting task assignment")

def get_agent_plans(name):
    plans = []
    sig = AGENT_SIGNATURES.get(name, {})
    atype = sig.get("type", "")
    if redis_ok:
        try:
            queued = r.lrange(f"queue:{name}", 0, 4)
            if queued:
                plans.extend([f"Queued: {q}" for q in queued])
        except:
            pass
    if name == "hermes":
        plans.extend(["Monitor cron jobs", "Process incoming messages", "Route delegated tasks", "Update memory/skills"])
    elif name == "nullclaw":
        plans.extend(["Route incoming model requests", "Balance load across connections", "Monitor agent health"])
    elif name == "ironclaw":
        plans.extend(["Scan incoming code for security", "Enforce sandbox policies", "Review skill safety"])
    elif atype == "coding":
        plans.extend(["Await code task", "Ready for file editing", "Available for test execution"])
    elif atype == "search":
        plans.extend(["Process search queries", "Ground responses with web data"])
    if not plans:
        plans = ["No pending tasks", "Awaiting assignment"]
    return plans

def get_agent_interactions(name):
    interactions = []
    if redis_ok:
        try:
            keys = r.keys(f"interaction:{name}:*")
            for k in keys[:5]:
                interactions.append(r.get(k))
        except:
            pass
    try:
        db_path = f"{BRAIN_DIR}/memory/episodic.db"
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            rows = conn.execute(
                "SELECT DISTINCT agent_id FROM episodes WHERE agent_id != ? ORDER BY timestamp DESC LIMIT 5",
                (name,)
            ).fetchall()
            conn.close()
            for row in rows:
                if row[0]:
                    interactions.append(f"Collaborating with {row[0]}")
    except:
        pass
    sig = AGENT_SIGNATURES.get(name, {})
    if sig.get("type") == "routing":
        interactions.extend(["9Router (localhost:20128)", "All active agents"])
    elif name == "hermes":
        interactions.extend(["Telegram gateway", "Cron scheduler", "Brain API (localhost:8199)"])
    elif sig.get("type") == "coding":
        interactions.extend(["Filesystem", "Git repositories"])
    return interactions[:8] if interactions else ["No active interactions"]

def get_all_agents():
    """Merge agents from all detection sources, prioritize: process > redis > cli
    CRITICAL: CLI-only agents are INACTIVE, not active."""
    cli_agents = get_cli_agents()
    redis_agents = get_redis_agents()
    proc_agents = get_process_agents()

    all_agents = {}
    # Start with CLI (lowest priority) — these are INSTALLED only
    for name, data in cli_agents.items():
        all_agents[name] = {**data, "status": "inactive"}

    # Override with Redis
    for name, data in redis_agents.items():
        all_agents[name] = {**all_agents.get(name, {}), **data}

    # Override with process (highest priority) — these are truly ACTIVE
    for name, data in proc_agents.items():
        all_agents[name] = {**all_agents.get(name, {}), **data}

    # Fill in missing fields from signatures
    for name, data in all_agents.items():
        sig = AGENT_SIGNATURES.get(name, {})
        if "desc" not in data: data["desc"] = sig.get("desc", "")
        if "region" not in data: data["region"] = sig.get("region", "semantic")
        if "objective" not in data: data["objective"] = get_agent_objective(name)
        if "plans" not in data: data["plans"] = get_agent_plans(name)
        if "interactions" not in data: data["interactions"] = get_agent_interactions(name)
        if "subagents" not in data: data["subagents"] = get_subagents(name)

    # ENFORCE STATUS ACCURACY:
    # Only process_scan agents are truly "active"
    # Redis agents with recent activity can be "active" or "staged"
    # CLI-only agents are always "inactive"
    now = time.time() * 1000
    for name, data in all_agents.items():
        detected = data.get("detected_by", "")
        if detected == "process_scan" or detected == "service_scan":
            data["status"] = "active"
        elif detected == "redis":
            last = data.get("last_activity", 0)
            try: last = int(str(last)) if last else 0
            except: last = 0
            if last and (now - last) < 300000:
                data["status"] = "active"
            elif last and (now - last) < 3600000:
                data["status"] = "staged"
            else:
                data["status"] = "inactive"
        elif detected == "cli_scan":
            # CLI scan = binary exists but NOT running
            if data.get("status") not in ("active", "staged"):
                data["status"] = "inactive"

    # Register active agents in Redis for persistence
    if redis_ok:
        for name, data in all_agents.items():
            if data.get("status") == "active":
                r.set(f"agent:{name}", json.dumps(data, default=str))
                r.expire(f"agent:{name}", 3600)

    # Also include agents from signatures that weren't detected at all
    for name, sig in AGENT_SIGNATURES.items():
        if name not in all_agents:
            all_agents[name] = {
                "status": "dormant",
                "color": sig["color"],
                "type": sig["type"],
                "desc": sig["desc"],
                "region": sig["region"],
                "detected_by": "none",
                "objective": "Not installed or detected",
                "plans": ["Not available"],
                "interactions": ["None"],
                "subagents": [],
            }

    return all_agents

def get_agent_detail(name):
    agents = get_all_agents()
    if name in agents:
        agent = agents[name]
        sig = AGENT_SIGNATURES.get(name, {})
        return {
            "name": name,
            "status": agent.get("status", "unknown"),
            "color": agent.get("color", sig.get("color", "#888")),
            "type": agent.get("type", sig.get("type", "")),
            "desc": agent.get("desc", sig.get("desc", "")),
            "region": agent.get("region", sig.get("region", "")),
            "objective": agent.get("objective", ""),
            "plans": agent.get("plans", []),
            "interactions": agent.get("interactions", []),
            "subagents": agent.get("subagents", []),
            "pid": agent.get("pid", "N/A"),
            "cpu": agent.get("cpu", "N/A"),
            "mem": agent.get("mem", "N/A"),
            "path": agent.get("path", "N/A"),
            "detected_by": agent.get("detected_by", "N/A"),
            "last_activity": agent.get("last_activity", "N/A"),
            "last_action": agent.get("last_action", "N/A"),
            "brain_region": BRAIN_REGIONS.get(agent.get("region", ""), {}),
        }
    return {"error": f"Agent '{name}' not found", "known_agents": list(AGENT_SIGNATURES.keys())}

def get_region_detail(region_name):
    if region_name in BRAIN_REGIONS:
        region = BRAIN_REGIONS[region_name]
        stats = {}
        if region_name == "semantic":
            meta_path = f"{BRAIN_DIR}/vectors/meta.json"
            if os.path.exists(meta_path):
                try: stats = json.load(open(meta_path))
                except: pass
            if os.path.exists(f"{BRAIN_DIR}/vectors/brain.index"):
                stats["index_size"] = os.path.getsize(f"{BRAIN_DIR}/vectors/brain.index")
        elif region_name == "graph":
            graph_path = f"{BRAIN_DIR}/graph/brain.graphml"
            if os.path.exists(graph_path):
                try:
                    from networkx import read_graphml
                    G = read_graphml(graph_path)
                    stats["nodes"] = G.number_of_nodes()
                    stats["edges"] = G.number_of_edges()
                except: pass
        elif region_name == "episodic":
            try:
                db_path = f"{BRAIN_DIR}/memory/episodic.db"
                if os.path.exists(db_path):
                    conn = sqlite3.connect(db_path)
                    stats["total_episodes"] = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
                    stats["agents_seen"] = conn.execute("SELECT COUNT(DISTINCT agent_id) FROM episodes WHERE agent_id IS NOT NULL").fetchone()[0]
                    stats["db_size"] = os.path.getsize(db_path)
                    rows = conn.execute("SELECT timestamp, agent_id, action FROM episodes ORDER BY timestamp DESC LIMIT 5").fetchall()
                    stats["recent"] = [{"time": r[0], "agent": r[1], "action": r[2]} for r in rows]
                    conn.close()
            except: pass
        elif region_name == "working":
            if redis_ok:
                try:
                    stats["total_keys"] = len(r.keys("*"))
                    stats["agent_keys"] = len(r.keys("agent:*"))
                    stats["task_keys"] = len(r.keys("task:*"))
                except: pass
        elif region_name == "procedural":
            skill_dir = f"{BRAIN_DIR}/skills/"
            if os.path.exists(skill_dir):
                skills = glob.glob(f"{skill_dir}**/*.md", recursive=True)
                stats["skill_count"] = len(skills)
                stats["skills"] = [os.path.basename(s) for s in skills[:20]]

        # Add file associations
        stats["files"] = get_region_files(region_name)
        stats["groups"] = region.get("groups", [])

        return {**region, "live_stats": stats}
    return {"error": f"Region '{region_name}' not found", "known_regions": list(BRAIN_REGIONS.keys())}

def get_brain_stats():
    stats = {}
    meta_path = f"{BRAIN_DIR}/vectors/meta.json"
    if os.path.exists(meta_path):
        try: stats["faiss"] = json.load(open(meta_path))
        except: stats["faiss"] = {"count": 0}
    else: stats["faiss"] = {"count": 0}
    try:
        from networkx import read_graphml
        graph_path = f"{BRAIN_DIR}/graph/brain.graphml"
        if os.path.exists(graph_path):
            G = read_graphml(graph_path)
            stats["graph"] = {"nodes": G.number_of_nodes(), "edges": G.number_of_edges()}
        else: stats["graph"] = {"nodes": 0, "edges": 0}
    except: stats["graph"] = {"nodes": 0, "edges": 0}
    try:
        db_path = f"{BRAIN_DIR}/memory/episodic.db"
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            count = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
            conn.close()
            stats["episodic"] = {"total": count}
        else: stats["episodic"] = {"total": 0}
    except: stats["episodic"] = {"total": 0}
    if redis_ok:
        try: stats["redis"] = {"keys": len(r.keys("*"))}
        except: stats["redis"] = {"keys": 0}
    else: stats["redis"] = {"keys": 0}
    stats["skills"] = {"count": len(glob.glob(f"{BRAIN_DIR}/skills/**/*.md", recursive=True))} if os.path.exists(f"{BRAIN_DIR}/skills/") else {"count": 0}
    return stats

def get_sync_stats():
    stats = {"status": "unknown", "last_sync": 0, "files": 0}
    sync_marker = f"{BRAIN_DIR}/cache/.last_sync"
    if os.path.exists(sync_marker):
        try:
            data = json.load(open(sync_marker))
            stats.update(data)
        except:
            mtime = os.path.getmtime(sync_marker)
            stats["last_sync"] = mtime * 1000
    try:
        from google.oauth2.credentials import Credentials
        token_path = "/config/.hermes/google_token.json"
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_info(json.load(open(token_path)))
            from googleapiclient.discovery import build
            drive = build('drive', 'v3', credentials=creds)
            drive.files().list(q="name='AkpanBrain'", spaces='drive', pageSize=1).execute()
            stats["status"] = "connected"
    except:
        stats["status"] = "disconnected"
    return stats

def get_activity():
    activities = []
    try:
        db_path = f"{BRAIN_DIR}/memory/episodic.db"
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            rows = conn.execute("SELECT timestamp, agent_id, action, content FROM episodes ORDER BY timestamp DESC LIMIT 20").fetchall()
            conn.close()
            for row in rows:
                activities.append({
                    "time": row[0],
                    "agent": row[1] or "system",
                    "msg": f"{row[2] or 'action'}: {(row[3] or '')[:80]}"
                })
    except:
        pass
    if not activities:
        now = datetime.now(timezone.utc).isoformat()
        activities = [
            {"time": now, "agent": "system", "msg": "Brain initialized — auto-detection scanning..."},
            {"time": now, "agent": "system", "msg": "Monitoring agent processes..."},
        ]
        for a in activities:
            a["bootstrap"] = True
    return activities

def get_nullclaw_html():
    """Built-in Nullclaw dashboard page — not raw JSON"""
    nc_status = "offline"
    nc_port = 20128
    try:
        s = socket.create_connection(("localhost", nc_port), timeout=2)
        s.close()
        nc_status = "online"
    except:
        pass

    # Get 9Router models if available
    models = []
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://localhost:{nc_port}/v1/models", timeout=3) as resp:
            data = json.loads(resp.read())
            models = [m["id"] for m in data.get("data", [])]
    except:
        pass

    # Get active agents count
    agents = get_all_agents()
    active_count = sum(1 for a in agents.values() if a.get("status") == "active")

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NULLCLAW — AI Router</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{--c0:#0a0a1a;--c1:#8b5cf6;--c2:#a78bfa;--dim:rgba(139,92,246,.15)}}
body{{background:var(--c0);color:#fff;font-family:'Courier New',monospace;min-height:100vh;padding:20px}}
.back{{display:inline-block;margin-bottom:20px;color:var(--c1);text-decoration:none;font-size:12px;letter-spacing:2px;border:1px solid var(--dim);padding:6px 12px;border-radius:4px}}
.back:hover{{background:rgba(139,92,246,.1)}}
h1{{font-size:24px;letter-spacing:4px;margin-bottom:4px;background:linear-gradient(90deg,var(--c1),var(--c2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.sub{{font-size:10px;color:rgba(255,255,255,.4);letter-spacing:3px;margin-bottom:30px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px;margin-bottom:24px}}
.card{{background:rgba(139,92,246,.06);border:1px solid var(--dim);border-radius:8px;padding:16px}}
.card-title{{font-size:8px;letter-spacing:3px;color:var(--c1);text-transform:uppercase;margin-bottom:8px}}
.card-val{{font-size:28px;font-weight:900;color:#fff}}
.card-sub{{font-size:9px;color:rgba(255,255,255,.4);margin-top:4px}}
.status{{display:inline-block;padding:2px 10px;border-radius:12px;font-size:9px;letter-spacing:2px;font-weight:700}}
.status.on{{background:rgba(34,197,94,.2);color:#22c55e;border:1px solid rgba(34,197,94,.3)}}
.status.off{{background:rgba(239,68,68,.2);color:#ef4444;border:1px solid rgba(239,68,68,.3)}}
.models{{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}}
.model{{font-size:9px;padding:4px 8px;background:rgba(139,92,246,.1);border:1px solid var(--dim);border-radius:4px;color:var(--c2)}}
.agents-section{{margin-top:24px}}
.agent-row{{display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.05)}}
.agent-dot{{width:8px;height:8px;border-radius:50%}}
.agent-name{{font-size:11px;font-weight:700;flex:1}}
.agent-status{{font-size:8px;letter-spacing:1px}}
</style></head><body>
<a class="back" href="/">← AKPANBRAIN</a>
<h1>NULLCLAW</h1>
<div class="sub">AI ROUTING PROXY — 999 CONCURRENT CONNECTIONS</div>
<div class="grid">
<div class="card"><div class="card-title">Status</div><div class="card-val"><span class="status {'on' if nc_status=='online' else 'off'}">{nc_status.upper()}</span></div><div class="card-sub">Port {nc_port}</div></div>
<div class="card"><div class="card-title">Active Agents</div><div class="card-val">{active_count}</div><div class="card-sub">Auto-detected from process scan</div></div>
<div class="card"><div class="card-title">Available Models</div><div class="card-val">{len(models)}</div><div class="card-sub">Via 9Router</div></div>
<div class="card"><div class="card-title">Max Connections</div><div class="card-val">999</div><div class="card-sub">Concurrent routing capacity</div></div>
</div>
<div class="card"><div class="card-title">Model Catalog</div><div class="models">{''.join(f'<div class="model">{m}</div>' for m in models) or '<div style="color:rgba(255,255,255,.3);font-size:10px">9Router offline — no models available</div>'}</div></div>
<div class="agents-section"><div class="card"><div class="card-title">Routed Agents</div>"""
    for name, a in sorted(agents.items(), key=lambda x: 0 if x[1].get("status") == "active" else 1):
        col = a.get("color", "#888")
        status = a.get("status", "dormant")
        dot_class = "on" if status == "active" else ""
        html += f"""<div class="agent-row"><div class="agent-dot {dot_class}" style="background:{col}"></div><div class="agent-name" style="color:{col}">{name}</div><div class="agent-status" style="color:{'#22c55e' if status=='active' else 'rgba(255,255,255,.3)'}">{status.upper()}</div></div>"""

    html += """</div></div></body></html>"""
    return html

# ─── WebSocket Server (simple upgrade on same port) ───
def ws_handshake(headers):
    key = headers.get("Sec-WebSocket-Key", "")
    if not key:
        return None
    accept = hashlib.sha1((key + WS_MAGIC).encode()).digest()
    import base64
    return base64.b64encode(accept).decode()

def ws_encode(data):
    """Encode a text message as WebSocket frame"""
    payload = data.encode('utf-8')
    frame = bytearray()
    frame.append(0x81)  # text frame, FIN
    length = len(payload)
    if length <= 125:
        frame.append(length | 0x80)  # masked bit set (but no mask)
        frame.append(length | 0x00)  # actually no mask
        frame = bytearray([0x81])
        if length <= 125:
            frame.append(length)
        elif length <= 65535:
            frame.append(126)
            frame.extend(struct.pack('>H', length))
        else:
            frame.append(127)
            frame.extend(struct.pack('>Q', length))
    elif length <= 65535:
        frame.append(126)
        frame.extend(struct.pack('>H', length))
    else:
        frame.append(127)
        frame.extend(struct.pack('>Q', length))
    frame.extend(payload)
    return bytes(frame)

def ws_broadcast(data):
    """Broadcast data to all connected WebSocket clients"""
    msg = ws_encode(json.dumps(data, default=str))
    dead = []
    for client in ws_clients:
        try:
            client.sendall(msg)
        except:
            dead.append(client)
    for d in dead:
        ws_clients.remove(d)

# ─── Background: push updates to WS clients every 2s ───
def ws_push_loop():
    import time as _t
    while True:
        _t.sleep(2)
        if ws_clients:
            try:
                data = {
                    "agents": get_all_agents(),
                    "brain": get_brain_stats(),
                    "activity": get_activity()[:5],
                    "timestamp": int(time.time() * 1000),
                }
                ws_broadcast(data)
            except:
                pass

push_thread = threading.Thread(target=ws_push_loop, daemon=True)
push_thread.start()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class BrainHandler(SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS, POST")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split('?')[0]

        # WebSocket upgrade
        upgrade = self.headers.get("Upgrade", "").lower()
        if upgrade == "websocket":
            self._handle_ws_upgrade()
            return

        if path == '/api/agents':
            self._json(get_all_agents())
        elif path == '/api/brain':
            self._json(get_brain_stats())
        elif path == '/api/sync':
            self._json(get_sync_stats())
        elif path == '/api/activity':
            self._json(get_activity())
        elif path.startswith('/api/agent/'):
            name = path.replace('/api/agent/', '')
            self._json(get_agent_detail(name))
        elif path.startswith('/api/region/'):
            name = path.replace('/api/region/', '')
            self._json(get_region_detail(name))
        elif path == '/api/regions':
            self._json(BRAIN_REGIONS)
        elif path == '/api/neuron-files':
            """Get files for a specific neuron region"""
            qs = parse_qs(urlparse(self.path).query)
            region = qs.get('region', [''])[0]
            if region:
                self._json({"region": region, "files": get_region_files(region), "groups": BRAIN_REGIONS.get(region, {}).get("groups", [])})
            else:
                self._json({"error": "Missing ?region= parameter"})
        elif path.startswith('/9router'):
            self._proxy('http://localhost:20128', path.replace('/9router', '') or '/')
        elif path == '/nullclaw':
            self._serve_html(get_nullclaw_html())
        elif path == '/' or path == '/index.html':
            self._serve_file(f"{DASHBOARD_DIR}/index.html", "text/html")
        else:
            filepath = f"{DASHBOARD_DIR}{path}"
            if os.path.exists(filepath):
                ext = filepath.rsplit('.', 1)[-1]
                ct = {"html": "text/html", "css": "text/css", "js": "application/javascript"}.get(ext, "text/plain")
                self._serve_file(filepath, ct)
            else:
                self._404()

    def _handle_ws_upgrade(self):
        """Handle WebSocket upgrade on the same HTTP port"""
        try:
            key = self.headers.get("Sec-WebSocket-Key", "")
            if not key:
                self._404()
                return
            accept = hashlib.sha1((key + WS_MAGIC).encode()).digest()
            import base64
            accept_b64 = base64.b64encode(accept).decode()

            # Send upgrade response manually
            self.send_response(101)
            self.send_header("Upgrade", "websocket")
            self.send_header("Connection", "Upgrade")
            self.send_header("Sec-WebSocket-Accept", accept_b64)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            # Register the socket for push
            ws_clients.append(self.connection)
            # Keep connection alive — the push thread will send data
            # Just block until client disconnects
            try:
                while True:
                    time.sleep(1)
            except:
                pass
        except Exception as e:
            try:
                ws_clients.remove(self.connection)
            except:
                pass

    def _proxy(self, target_base, path):
        import urllib.request
        try:
            url = target_base + path
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                ct = resp.headers.get('Content-Type', 'text/html')
                body = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", ct)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
        except Exception as e:
            self._json({"error": str(e), "hint": "Service may be down"}, 502)

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def _serve_html(self, html_string):
        content = html_string.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", len(content))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(content)

    def _serve_file(self, path, content_type):
        try:
            with open(path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(content))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        except Exception:
            self._404()

    def _404(self):
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Not found")

    def log_message(self, format, *args):
        pass  # Suppress logging


if __name__ == '__main__':
    server = ThreadedHTTPServer(('0.0.0.0', 8199), BrainHandler)
    print(f'🧠 AkpanBrain API v2 running on http://0.0.0.0:8199 (WebSocket + REST)')
    server.serve_forever()
