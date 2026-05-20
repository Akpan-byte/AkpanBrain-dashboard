#!/usr/bin/env python3
"""
AkpanBrain WebSocket Server — Real-time brain + agent + system data pipeline.

Reads from:
- Hermes state.db (sessions, messages, subagents, costs)
- Brain FAISS index (semantic cortex)
- Brain NetworkX graph (knowledge graph)
- Brain SQLite (episodic memory)
- Redis (working memory / live state)
- psutil (system metrics: CPU, RAM, disk, network)

Pushes via WebSocket to 3D dashboard.
Also serves as REST API for historical queries.
"""
import asyncio, json, os, sqlite3, time, hashlib, threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from collections import defaultdict

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse

# ─── Config ───
HERMES_HOME = os.environ.get("HERMES_HOME", "/config/.hermes")
STATE_DB = os.path.join(HERMES_HOME, "state.db")
BRAIN_DIR = "/config/brain"
BRAIN_DB = os.path.join(BRAIN_DIR, "memory/episodic.db")
BRAIN_INDEX = os.path.join(BRAIN_DIR, "vectors/brain.index")
BRAIN_META = os.path.join(BRAIN_DIR, "vectors/meta.json")
BRAIN_GRAPH = os.path.join(BRAIN_DIR, "graph/brain.graphml")
REDIS_HOST = "localhost"
REDIS_PORT = 6379

POLL_INTERVAL = 2.0  # seconds between state.db polls
METRIC_INTERVAL = 3.0  # seconds between system metric reads

# ─── FastAPI App ───
app = FastAPI(title="AkpanBrain WS Server", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ─── State ───
ws_clients: Set[WebSocket] = set()
last_message_id = 0
last_session_count = 0
agent_cache: Dict = {}
session_cache: Dict = {}
system_metrics: Dict = {}


# ═══════════════════════════════════════════════════════
# STATE DB READER (from ClawMetry HermesAdapter)
# ═══════════════════════════════════════════════════════
def _open_state_db():
    """Open state.db in read-only mode with retry on lock."""
    uri = f"file:{STATE_DB}?mode=ro"
    for attempt in range(2):
        try:
            conn = sqlite3.connect(uri, uri=True, timeout=2.0)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.OperationalError:
            if attempt == 0:
                time.sleep(0.1)
                continue
            raise
    return None


def get_active_sessions():
    """Get all currently active sessions with subagent hierarchy."""
    conn = _open_state_db()
    if not conn:
        return []
    try:
        cur = conn.execute("""
            SELECT id, title, model, started_at, ended_at, parent_session_id,
                   source, message_count, input_tokens, output_tokens,
                   cache_read_tokens, cache_write_tokens, reasoning_tokens,
                   estimated_cost_usd, actual_cost_usd, cost_status, end_reason,
                   tool_call_count, api_call_count, handoff_platform
            FROM sessions WHERE ended_at IS NULL
            ORDER BY started_at DESC
        """)
        sessions = []
        for r in cur.fetchall():
            actual = r['actual_cost_usd']
            estimated = r['estimated_cost_usd']
            cost = actual if actual is not None else estimated
            sessions.append({
                'id': r['id'],
                'title': r['title'] or '',
                'model': r['model'] or '',
                'startedAt': r['started_at'],
                'parentId': r['parent_session_id'],
                'source': r['source'] or '',
                'messageCount': r['message_count'] or 0,
                'inputTokens': r['input_tokens'] or 0,
                'outputTokens': r['output_tokens'] or 0,
                'totalTokens': (r['input_tokens'] or 0) + (r['output_tokens'] or 0),
                'cacheRead': r['cache_read_tokens'] or 0,
                'cacheWrite': r['cache_write_tokens'] or 0,
                'reasoning': r['reasoning_tokens'] or 0,
                'costUsd': float(cost) if cost is not None else 0.0,
                'toolCallCount': r['tool_call_count'] or 0,
                'apiCallCount': r['api_call_count'] or 0,
                'platform': r['handoff_platform'] or r['source'] or '',
            })
        return sessions
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def get_session_tree():
    """Build parent→children tree for subagent hierarchy."""
    sessions = get_active_sessions()
    tree = {}
    roots = []
    children = defaultdict(list)
    
    for s in sessions:
        if s['parentId']:
            children[s['parentId']].append(s)
        else:
            roots.append(s)
        tree[s['id']] = s
    
    # Also get ended sessions that are parents of active subagents
    parent_ids = {s['parentId'] for s in sessions if s['parentId']}
    if parent_ids:
        conn = _open_state_db()
        if conn:
            try:
                placeholders = ','.join(['?'] * len(parent_ids))
                cur = conn.execute(f"""
                    SELECT id, title, model, started_at, ended_at, parent_session_id, source
                    FROM sessions WHERE id IN ({placeholders})
                """, list(parent_ids))
                for r in cur.fetchall():
                    if r['id'] not in tree:
                        tree[r['id']] = {
                            'id': r['id'],
                            'title': r['title'] or '',
                            'model': r['model'] or '',
                            'startedAt': r['started_at'],
                            'parentId': r['parent_session_id'],
                            'source': r['source'] or '',
                            'endedAt': r['ended_at'],
                            'children': [],
                        }
            except:
                pass
            finally:
                conn.close()
    
    # Attach children
    for sid, session in tree.items():
        session['children'] = children.get(sid, [])
    
    return {'roots': roots, 'tree': tree, 'children': dict(children)}


def get_recent_events(limit=50):
    """Get most recent messages/events across all sessions."""
    conn = _open_state_db()
    if not conn:
        return []
    try:
        cur = conn.execute("""
            SELECT id, session_id, role, content, tool_name, tool_calls, 
                   timestamp, token_count, finish_reason
            FROM messages ORDER BY id DESC LIMIT ?
        """, (limit,))
        events = []
        for r in cur.fetchall():
            tool_calls = []
            if r['tool_calls']:
                try:
                    tool_calls = json.loads(r['tool_calls'])
                except:
                    pass
            events.append({
                'id': r['id'],
                'sessionId': r['session_id'],
                'role': r['role'],
                'content': (r['content'] or '')[:500],  # truncate for WS
                'toolName': r['tool_name'] or '',
                'toolCalls': tool_calls,
                'ts': r['timestamp'],
                'tokens': r['token_count'] or 0,
                'finishReason': r['finish_reason'] or '',
            })
        return events
    except:
        return []
    finally:
        conn.close()


def get_new_events(last_id):
    """Poll for events since last_id (ClawMetry stream_events pattern)."""
    conn = _open_state_db()
    if not conn:
        return [], last_id
    try:
        cur = conn.execute("""
            SELECT id, session_id, role, content, tool_name, tool_calls,
                   timestamp, token_count, finish_reason
            FROM messages WHERE id > ? ORDER BY id ASC
        """, (last_id,))
        events = []
        max_id = last_id
        for r in cur.fetchall():
            tool_calls = []
            if r['tool_calls']:
                try:
                    tool_calls = json.loads(r['tool_calls'])
                except:
                    pass
            events.append({
                'id': r['id'],
                'sessionId': r['session_id'],
                'role': r['role'],
                'content': (r['content'] or '')[:300],
                'toolName': r['tool_name'] or '',
                'toolCalls': tool_calls,
                'ts': r['timestamp'],
                'tokens': r['token_count'] or 0,
            })
            max_id = max(max_id, r['id'])
        return events, max_id
    except:
        return [], last_id
    finally:
        conn.close()


def get_session_details(session_id: str):
    """Full details for a specific session — all messages + metadata."""
    conn = _open_state_db()
    if not conn:
        return None
    try:
        # Session meta
        cur = conn.execute("""
            SELECT id, title, model, started_at, ended_at, parent_session_id,
                   source, message_count, tool_call_count, input_tokens, output_tokens,
                   cache_read_tokens, cache_write_tokens, reasoning_tokens,
                   estimated_cost_usd, actual_cost_usd, cost_status, end_reason,
                   system_prompt, handoff_platform, api_call_count
            FROM sessions WHERE id = ?
        """, (session_id,))
        row = cur.fetchone()
        if not row:
            return None
        
        actual = row['actual_cost_usd']
        estimated = row['estimated_cost_usd']
        
        # All messages
        cur2 = conn.execute("""
            SELECT id, role, content, tool_name, tool_calls, timestamp, 
                   token_count, finish_reason, reasoning
            FROM messages WHERE session_id = ? ORDER BY timestamp ASC
        """, (session_id,))
        messages = []
        for m in cur2.fetchall():
            messages.append({
                'id': m['id'],
                'role': m['role'],
                'content': (m['content'] or '')[:2000],
                'toolName': m['tool_name'] or '',
                'tokens': m['token_count'] or 0,
                'ts': m['timestamp'],
                'finishReason': m['finish_reason'] or '',
            })
        
        # Child sessions (subagents)
        cur3 = conn.execute("""
            SELECT id, title, model, started_at, ended_at, source, 
                   input_tokens, output_tokens, tool_call_count
            FROM sessions WHERE parent_session_id = ?
            ORDER BY started_at ASC
        """, (session_id,))
        subagents = []
        for s in cur3.fetchall():
            subagents.append({
                'id': s['id'],
                'title': s['title'] or '',
                'model': s['model'] or '',
                'startedAt': s['started_at'],
                'endedAt': s['ended_at'],
                'source': s['source'] or '',
                'tokens': (s['input_tokens'] or 0) + (s['output_tokens'] or 0),
                'toolCalls': s['tool_call_count'] or 0,
            })
        
        return {
            'id': row['id'],
            'title': row['title'] or '',
            'model': row['model'] or '',
            'startedAt': row['started_at'],
            'endedAt': row['ended_at'],
            'parentId': row['parent_session_id'],
            'source': row['source'] or '',
            'platform': row['handoff_platform'] or row['source'] or '',
            'messageCount': row['message_count'] or 0,
            'toolCallCount': row['tool_call_count'] or 0,
            'apiCallCount': row['api_call_count'] or 0,
            'inputTokens': row['input_tokens'] or 0,
            'outputTokens': row['output_tokens'] or 0,
            'totalTokens': (row['input_tokens'] or 0) + (row['output_tokens'] or 0),
            'cacheRead': row['cache_read_tokens'] or 0,
            'cacheWrite': row['cache_write_tokens'] or 0,
            'reasoning': row['reasoning_tokens'] or 0,
            'costUsd': float(actual if actual is not None else (estimated or 0)),
            'costStatus': row['cost_status'] or '',
            'endReason': row['end_reason'] or '',
            'systemPrompt': (row['system_prompt'] or '')[:500],
            'messages': messages,
            'subagents': subagents,
        }
    except:
        return None
    finally:
        conn.close()


def get_agent_stats():
    """Aggregate stats per agent/model."""
    conn = _open_state_db()
    if not conn:
        return {}
    try:
        cur = conn.execute("""
            SELECT model, source, 
                   COUNT(*) as total,
                   SUM(CASE WHEN ended_at IS NULL THEN 1 ELSE 0 END) as active,
                   SUM(input_tokens) as total_input,
                   SUM(output_tokens) as total_output,
                   SUM(message_count) as total_messages,
                   SUM(tool_call_count) as total_tool_calls,
                   SUM(CASE WHEN parent_session_id IS NOT NULL THEN 1 ELSE 0 END) as subagent_count,
                   SUM(estimated_cost_usd) as total_cost
            FROM sessions GROUP BY model, source
        """)
        stats = {}
        for r in cur.fetchall():
            key = f"{r['model']}|{r['source']}"
            stats[key] = {
                'model': r['model'] or 'unknown',
                'source': r['source'] or 'unknown',
                'totalSessions': r['total'],
                'activeSessions': r['active'],
                'totalInputTokens': r['total_input'] or 0,
                'totalOutputTokens': r['total_output'] or 0,
                'totalMessages': r['total_messages'] or 0,
                'totalToolCalls': r['total_tool_calls'] or 0,
                'subagentCount': r['subagent_count'],
                'totalCostUsd': float(r['total_cost'] or 0),
            }
        return stats
    except:
        return {}
    finally:
        conn.close()


def get_past_sessions(limit=100, offset=0):
    """Ended sessions with summaries."""
    conn = _open_state_db()
    if not conn:
        return []
    try:
        cur = conn.execute("""
            SELECT id, title, model, started_at, ended_at, parent_session_id,
                   source, message_count, input_tokens, output_tokens,
                   estimated_cost_usd, actual_cost_usd, end_reason,
                   tool_call_count, api_call_count
            FROM sessions WHERE ended_at IS NOT NULL
            ORDER BY ended_at DESC LIMIT ? OFFSET ?
        """, (limit, offset))
        sessions = []
        for r in cur.fetchall():
            cost = r['actual_cost_usd'] if r['actual_cost_usd'] is not None else r['estimated_cost_usd']
            duration = 0
            if r['ended_at'] and r['started_at']:
                duration = r['ended_at'] - r['started_at']
            sessions.append({
                'id': r['id'],
                'title': r['title'] or '',
                'model': r['model'] or '',
                'startedAt': r['started_at'],
                'endedAt': r['ended_at'],
                'duration': duration,
                'parentId': r['parent_session_id'],
                'source': r['source'] or '',
                'messageCount': r['message_count'] or 0,
                'totalTokens': (r['input_tokens'] or 0) + (r['output_tokens'] or 0),
                'costUsd': float(cost) if cost is not None else 0.0,
                'endReason': r['end_reason'] or '',
                'toolCallCount': r['tool_call_count'] or 0,
                'apiCallCount': r['api_call_count'] or 0,
            })
        return sessions
    except:
        return []
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════
# BRAIN LAYER READERS
# ═══════════════════════════════════════════════════════
def get_brain_status():
    """Read brain layer status — FAISS, NetworkX, SQLite, Redis."""
    status = {
        'semanticCortex': {'status': 'unknown', 'vectorCount': 0},
        'knowledgeGraph': {'status': 'unknown', 'nodes': 0, 'edges': 0},
        'episodicMemory': {'status': 'unknown', 'episodes': 0},
        'workingMemory': {'status': 'unknown', 'keys': 0},
        'driveSync': {'status': 'unknown'},
    }
    
    # FAISS
    try:
        import faiss
        if os.path.exists(BRAIN_INDEX):
            idx = faiss.read_index(BRAIN_INDEX)
            status['semanticCortex'] = {'status': 'active', 'vectorCount': idx.ntotal}
        else:
            status['semanticCortex'] = {'status': 'empty', 'vectorCount': 0}
    except Exception as e:
        status['semanticCortex'] = {'status': 'error', 'error': str(e)[:100]}
    
    # NetworkX
    try:
        import networkx as nx
        if os.path.exists(BRAIN_GRAPH):
            G = nx.read_graphml(BRAIN_GRAPH)
            status['knowledgeGraph'] = {'status': 'active', 'nodes': G.number_of_nodes(), 'edges': G.number_of_edges()}
        else:
            status['knowledgeGraph'] = {'status': 'empty', 'nodes': 0, 'edges': 0}
    except Exception as e:
        status['knowledgeGraph'] = {'status': 'error', 'error': str(e)[:100]}
    
    # SQLite episodic
    try:
        if os.path.exists(BRAIN_DB):
            conn = sqlite3.connect(BRAIN_DB)
            cur = conn.execute("SELECT COUNT(*) FROM episodes")
            count = cur.fetchone()[0]
            status['episodicMemory'] = {'status': 'active', 'episodes': count}
            conn.close()
        else:
            status['episodicMemory'] = {'status': 'empty', 'episodes': 0}
    except Exception as e:
        status['episodicMemory'] = {'status': 'error', 'error': str(e)[:100]}
    
    # Redis
    try:
        import redis
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, socket_timeout=2)
        r.ping()
        info = r.info('keyspace')
        keys = info.get('db0', {}).get('keys', 0) if info else 0
        status['workingMemory'] = {'status': 'active', 'keys': keys}
    except Exception as e:
        status['workingMemory'] = {'status': 'error', 'error': str(e)[:100]}
    
    # Drive sync — use Python Google Drive API (more reliable than rclone in headless)
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        token_path = os.path.join(HERMES_HOME, "google_token.json")
        if os.path.exists(token_path):
            with open(token_path) as f:
                t = json.load(f)
            creds = Credentials(
                token=t.get('token'),
                refresh_token=t.get('refresh_token'),
                token_uri=t.get('token_uri'),
                client_id=t.get('client_id'),
                client_secret=t.get('client_secret'),
            )
            drive = build('drive', 'v3', credentials=creds)
            results = drive.files().list(
                q="'1ag3h_WKBCPTCKaD07NXF2xEucjlaw3rj' in parents and trashed=false",
                spaces='drive', fields='files(id,name,size)', pageSize=20
            ).execute()
            files = results.get('files', [])
            total_size = sum(int(f.get('size', 0)) for f in files)
            status['driveSync'] = {'status': 'connected', 'files': len(files), 'totalSize': total_size}
        else:
            status['driveSync'] = {'status': 'no-token'}
    except Exception as e:
        status['driveSync'] = {'status': 'error', 'error': str(e)[:100]}
    
    return status


# ═══════════════════════════════════════════════════════
# SYSTEM MONITORING (psutil)
# ═══════════════════════════════════════════════════════
def get_system_metrics():
    """CPU, RAM, disk, network via psutil."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net = psutil.net_io_counters()
        
        # Per-process for known agents
        agent_procs = {}
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
            try:
                name = proc.info['name'] or ''
                cmdline = ' '.join(proc.info.get('cmdline') or [])
                for agent_name in ['hermes', 'claude', 'gemini', 'kimi', 'kilo', 'kilocode', 'codex', 'opencode', 'qwen', 'roo', 'nullclaw', 'codebuff', 'goose', 'gptme', 'jcode', 'python3']:
                    if agent_name in name.lower() or agent_name in cmdline.lower():
                        if agent_name not in agent_procs:
                            agent_procs[agent_name] = []
                        agent_procs[agent_name].append({
                            'pid': proc.info['pid'],
                            'cpu': proc.info['cpu_percent'] or 0,
                            'mem': round(proc.info['memory_percent'] or 0, 2),
                            'cmd': cmdline[:100],
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return {
            'cpu': cpu,
            'memTotal': mem.total,
            'memUsed': mem.used,
            'memPercent': mem.percent,
            'diskTotal': disk.total,
            'diskUsed': disk.used,
            'diskPercent': disk.percent,
            'netBytesSent': net.bytes_sent,
            'netBytesRecv': net.bytes_recv,
            'agentProcesses': agent_procs,
            'ts': time.time(),
        }
    except ImportError:
        return {'error': 'psutil not installed', 'ts': time.time()}
    except Exception as e:
        return {'error': str(e)[:100], 'ts': time.time()}


# ═══════════════════════════════════════════════════════
# AGENT AUTO-DETECTION
# ═══════════════════════════════════════════════════════
def detect_agents():
    """Auto-detect installed agents and their status."""
    import shutil
    agents = {
        'hermes':    {'bins': ['hermes'],          'type': 'orchestrator', 'color': '#4FC3F7', 'icon': '🧠'},
        'claude':    {'bins': ['claude'],           'type': 'coder',       'color': '#F59E0B', 'icon': '🟡'},
        'gemini':    {'bins': ['gemini'],           'type': 'coder',       'color': '#34D399', 'icon': '🟢'},
        'kilo':      {'bins': ['kilo', 'kilocode'], 'type': 'coder',      'color': '#A78BFA', 'icon': '🟣'},
        'kimi':      {'bins': ['kimi'],            'type': 'coder',       'color': '#FB923C', 'icon': '🟠'},
        'codex':     {'bins': ['codex'],           'type': 'coder',       'color': '#38BDF8', 'icon': '🔵'},
        'opencode':  {'bins': ['opencode'],        'type': 'coder',       'color': '#2DD4BF', 'icon': '🌊'},
        'qwen':      {'bins': ['qwen'],            'type': 'coder',       'color': '#F472B6', 'icon': '🩷'},
        'roo':       {'bins': ['roo'],             'type': 'coder',       'color': '#EF4444', 'icon': '🔴'},
        'nullclaw':  {'bins': ['nullclaw'],        'type': 'router',      'color': '#8B5CF6', 'icon': '🔮'},
        'gptme':     {'bins': ['gptme'],           'type': 'coder',       'color': '#06B6D4', 'icon': '💎'},
        'jcode':     {'bins': ['jcode'],           'type': 'coder',       'color': '#10B981', 'icon': '✅'},
        'codebuff':  {'bins': ['codebuff'],        'type': 'coder',       'color': '#FBBF24', 'icon': '⚡'},
        'goose':     {'bins': ['goose'],           'type': 'coder',       'color': '#F97316', 'icon': '🦆'},
        'codel':     {'bins': ['codel'],           'type': 'coder',       'color': '#A3E635', 'icon': '💻'},
    }
    
    # Build running set once (more efficient)
    running_names = set()
    try:
        import psutil
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                pname = (proc.info['name'] or '').lower()
                cmdline = ' '.join(proc.info.get('cmdline') or []).lower()
                for name, info in agents.items():
                    for binname in info['bins']:
                        if binname in pname or binname in cmdline:
                            running_names.add(name)
            except:
                continue
    except:
        pass
    
    detected = []
    for name, info in agents.items():
        # Try each bin alias
        path = None
        for binname in info['bins']:
            path = shutil.which(binname)
            if path:
                break
        
        is_installed = path is not None
        is_running = name in running_names
        
        detected.append({
            'name': name,
            'type': info['type'],
            'color': info['color'],
            'icon': info['icon'],
            'installed': is_installed,
            'running': is_running,
            'path': path or '',
        })
    
    return detected


# ═══════════════════════════════════════════════════════
# WEBSOCKET BROADCAST LOOP
# ═══════════════════════════════════════════════════════
async def broadcast_loop():
    """Main loop: poll data sources and push to all connected WS clients."""
    global last_message_id, last_session_count
    
    # Initialize last_message_id
    conn = _open_state_db()
    if conn:
        try:
            cur = conn.execute("SELECT COALESCE(MAX(id), 0) FROM messages")
            last_message_id = cur.fetchone()[0]
        except:
            pass
        conn.close()
    
    while True:
        if not ws_clients:
            await asyncio.sleep(POLL_INTERVAL)
            continue
        
        try:
            # 1. New events from state.db
            events, new_max = get_new_events(last_message_id)
            last_message_id = new_max
            
            # 2. Active sessions (check for changes)
            sessions = get_active_sessions()
            session_count = len(sessions)
            
            # 3. System metrics
            metrics = get_system_metrics()
            
            payload = {
                'type': 'update',
                'ts': time.time(),
                'events': events,
                'activeSessions': sessions,
                'sessionCount': session_count,
                'metrics': metrics,
            }
            
            # Only send session tree on change
            if session_count != last_session_count or events:
                payload['sessionTree'] = get_session_tree()
                payload['agentStats'] = get_agent_stats()
                last_session_count = session_count
            
            msg = json.dumps(payload, default=str)
            dead = set()
            for ws in ws_clients:
                try:
                    await ws.send_text(msg)
                except:
                    dead.add(ws)
            ws_clients -= dead
            
        except Exception as e:
            print(f"Broadcast error: {e}")
        
        await asyncio.sleep(POLL_INTERVAL)


async def metrics_loop():
    """Slower loop for system metrics + brain status."""
    while True:
        if not ws_clients:
            await asyncio.sleep(METRIC_INTERVAL)
            continue
        
        try:
            brain = get_brain_status()
            agents = detect_agents()
            metrics = get_system_metrics()
            
            payload = {
                'type': 'status',
                'ts': time.time(),
                'brain': brain,
                'agents': agents,
                'metrics': metrics,
            }
            
            msg = json.dumps(payload, default=str)
            dead = set()
            for ws in ws_clients:
                try:
                    await ws.send_text(msg)
                except:
                    dead.add(ws)
            ws_clients -= dead
            
        except Exception as e:
            print(f"Metrics error: {e}")
        
        await asyncio.sleep(METRIC_INTERVAL)


# ═══════════════════════════════════════════════════════
# REST API ENDPOINTS
# ═══════════════════════════════════════════════════════
@app.get("/api/agents")
async def api_agents():
    return detect_agents()

@app.get("/api/sessions/active")
async def api_active_sessions():
    return get_active_sessions()

@app.get("/api/sessions/past")
async def api_past_sessions(limit: int = 100, offset: int = 0):
    return get_past_sessions(limit, offset)

@app.get("/api/session/{session_id}")
async def api_session_detail(session_id: str):
    detail = get_session_details(session_id)
    if not detail:
        return JSONResponse(status_code=404, content={"error": "Session not found"})
    return detail

@app.get("/api/brain")
async def api_brain_status():
    return get_brain_status()

@app.get("/api/metrics")
async def api_metrics():
    return get_system_metrics()

@app.get("/api/stats")
async def api_stats():
    return get_agent_stats()

@app.get("/api/tree")
async def api_session_tree():
    return get_session_tree()

@app.get("/api/events/recent")
async def api_recent_events(limit: int = 50):
    return get_recent_events(limit)

# ─── Dashboard HTML ───
DASHBOARD_PATH = os.path.join(BRAIN_DIR, "dashboard_v9.html")

@app.get("/")
async def dashboard():
    if os.path.exists(DASHBOARD_PATH):
        return FileResponse(DASHBOARD_PATH, media_type="text/html")
    return HTMLResponse("<h1>AkpanBrain Dashboard</h1><p>Dashboard file not found at {DASHBOARD_PATH}</p>")


# ═══════════════════════════════════════════════════════
# WEBSOCKET ENDPOINT
# ═══════════════════════════════════════════════════════
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.add(ws)
    
    # Send initial snapshot
    try:
        snapshot = {
            'type': 'snapshot',
            'ts': time.time(),
            'agents': detect_agents(),
            'activeSessions': get_active_sessions(),
            'sessionTree': get_session_tree(),
            'brain': get_brain_status(),
            'metrics': get_system_metrics(),
            'agentStats': get_agent_stats(),
            'recentEvents': get_recent_events(20),
        }
        await ws.send_text(json.dumps(snapshot, default=str))
    except:
        pass
    
    try:
        while True:
            # Listen for client requests (e.g., "get session XYZ")
            data = await ws.receive_text()
            req = json.loads(data) if data else {}
            
            if req.get('type') == 'getSession':
                detail = get_session_details(req.get('sessionId', ''))
                if detail:
                    await ws.send_text(json.dumps({'type': 'sessionDetail', 'data': detail}, default=str))
            
            elif req.get('type') == 'getPastSessions':
                past = get_past_sessions(req.get('limit', 50), req.get('offset', 0))
                await ws.send_text(json.dumps({'type': 'pastSessions', 'data': past}, default=str))
            
            elif req.get('type') == 'getBrainStatus':
                await ws.send_text(json.dumps({'type': 'brainStatus', 'data': get_brain_status()}, default=str))
            
            elif req.get('type') == 'getMetrics':
                await ws.send_text(json.dumps({'type': 'systemMetrics', 'data': get_system_metrics()}, default=str))
                
    except WebSocketDisconnect:
        ws_clients.discard(ws)
    except:
        ws_clients.discard(ws)


# ═══════════════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════════════
@app.on_event("startup")
async def startup():
    asyncio.create_task(broadcast_loop())
    asyncio.create_task(metrics_loop())


if __name__ == "__main__":
    print("🧠 AkpanBrain WebSocket Server starting on port 8199...")
    uvicorn.run(app, host="0.0.0.0", port=8199, log_level="info")
