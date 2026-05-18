# AkpanBrain — Status Snapshot (2026-05-18)

## Dashboard v7 — Live at https://brain-gules-eight.vercel.app/

### What's Working
- **3D Neural Map**: 40 neurons, 51 synapses, 6 brain regions, holographic grid
- **16 Agent Orbs**: Hermes, Gemini CLI, Kilo Code, Kimi Code, Nullclaw + 11 more
- **Click-to-Inspect**: Click agents → detail panel (name, type, region, status, activity)
- **Click Regions**: Shows backend, file count, agents in region
- **Click Neurons**: Shows type (hub/normal), region, synapse count, fire status
- **Hover Tooltips**: Follow cursor with entity info
- **Electrical Activity**: 36/40 neurons firing, 6 lightning arcs, 12 pulse particles
- **Visual Polish**: Scan lines, vignette, red scan sweep, CSS bloom (1/4-res + blur + screen blend)
- **Camera**: OrbitControls with auto-rotate, focus-on-click, smooth transitions

### Brain ↔ Drive Sync
- ✅ Local → Drive (rclone sync) — working
- ✅ Drive → Local (rclone copy) — working  
- ✅ Token refresh automated (refresh_token.py)
- ✅ Remote: `akpanbrain:` (Google Drive, root_folder_id set)
- ✅ Redis: PONG on port 6379

### Key Files
- `/config/brain/dashboard/index_v7.html` — main dashboard (55KB, Three.js r160)
- `/config/brain/dashboard/build.py` — embeds live data, deploys to Vercel
- `/config/brain/akpanbrain.py` — brain module (FAISS + NetworkX + SQLite + Redis)
- `/config/brain/refresh_token.py` — Google OAuth token refresh

### Architecture
- Semantic Cortex → FAISS (vectors)
- Knowledge Graph → NetworkX (brain.graphml)
- Memory Hippocampus → SQLite (episodic.db)
- Working Memory → Redis (port 6379)
- Procedural Cortex → Skills
- Sensory Buffer → File watcher

### ON HOLD
- Gemini embeddings — waiting for user API key
- Qdrant — no Docker, using FAISS instead

### NEXT PHASE — What's Needed
1. **Real Agent Data Pipeline** — WebSocket from Hermes/agents to dashboard (currently static/mock data)
2. **Subagent/Swarm Visualization** — Tiny icons for spawned subagents, parent-child hierarchy
3. **Session Tracking** — Live session info per agent, past sessions, work summaries
4. **System Monitoring** — CPU, RAM, disk, network, process health in 3D
5. **Real-time Activity Feed** — What each agent is doing RIGHT NOW
6. **Task/Objective Tracking** — Current tasks, next steps, completion status

### Research Targets (repos/tools to evaluate)
- Agent observability: LangFuse, LangSmith alternatives, OpenTelemetry
- Swarm visualization: D3.js force graphs, 3D particle swarms
- System monitoring: Glances, Netdata, Prometheus+Grafana
- WebSocket dashboards: Socket.IO, FastAPI WebSocket
- Session tracking: Custom SQLite + WebSocket bridge
