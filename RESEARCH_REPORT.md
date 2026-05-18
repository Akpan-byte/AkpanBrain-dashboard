# AkpanBrain Dashboard — Ocean-Boiling Research Report
## Making the Dashboard ACTUALLY Work: Live Agent Activity, Sessions, Swarms, System Monitoring

**Goal**: Transform the 3D neural dashboard from cosmetic/mock data to REAL — showing actual live agent activity, subagent hierarchies, session details, system monitoring, all clickable and explorable.

---

## 🏆 TIER 1 — MUST USE (Directly solves our problems)

### 1. OpenLIT ⭐2451 | Apache-2.0 | TypeScript
**github.com/openlit/openlit**
- **What**: OpenTelemetry-native LLM observability platform
- **Why it's gold**: GPU monitoring, distributed tracing, 50+ LLM provider integrations, ClickHouse backend, Grafana dashboards
- **How to integrate**:
  - Install OpenLIT Python SDK → auto-instruments all LLM calls from Hermes/agents
  - Sends OTel traces to ClickHouse → our dashboard reads from same DB
  - GPU monitoring via nvidia-smi → feed into our 3D brain regions
  - **Key**: This gives us the REAL agent activity data pipeline — what every agent is doing, token usage, latency, errors

### 2. Aegra ⭐913 | Apache-2.0 | Python
**github.com/aegra/aegra**
- **What**: Self-hosted LangGraph Platform alternative (FastAPI + PostgreSQL)
- **Why it's gold**: Agent backend with session management, state persistence, streaming, cron scheduling
- **How to integrate**:
  - Use Aegra as the agent session store — every agent session gets a UUID, state tracked in Postgres
  - FastAPI WebSocket endpoints → push live session data to our 3D dashboard
  - Cron scheduling = our cron jobs managed here
  - **Key**: Solves the session tracking + past sessions + work summaries problem

### 3. OpenClaw Office ⭐591 | MIT | TypeScript
**github.com/WW-AI-Lab/openclaw-office**
- **What**: Visual monitoring frontend for multi-agent systems — "digital office" metaphor
- **Why it's GOLD**: WebSocket-connected, real-time agent collaboration viz, isometric office scene, agent avatars with status animation, workspace = session, meeting room = collaboration context
- **How to integrate**:
  - STUDY their WebSocket protocol for agent status updates
  - Borrow their avatar generation (deterministic SVG from agent ID)
  - Their "workspace = session" metaphor maps directly to our brain regions
  - **Key**: This is the closest existing project to what we want. Copy their approach, make it 3D.

### 4. AgentScope Studio ⭐548 | Apache-2.0 | TypeScript
**github.com/agentscope-ai/agentscope-studio**
- **What**: Development-oriented visualization toolkit for multi-agent systems
- **Why it's gold**: OpenTelemetry tracing, agent conversation visualization, distributed trace viewer
- **How to integrate**:
  - Use their trace format as our standard — every agent action becomes a trace span
  - Their timeline visualization → adapt to our 3D neuron firing
  - **Key**: Standardized tracing format that works across all agent frameworks

### 5. Claude Code Agent Monitor ⭐373 | MIT | TypeScript
**github.com/hoangsonww/Claude-Code-Agent-Monitor**
- **What**: Real-time monitoring dashboard for Claude Code agents — SQLite + Node.js + Express + React + WebSockets
- **Why it's GOLD**: Tracks sessions, agent activity, tool usage, subagent orchestration via Claude Code hooks. Has Kanban status board.
- **How to integrate**:
  - Their hook system → we write similar hooks for Hermes agents
  - SQLite schema for sessions → adapt for our brain episodic memory
  - WebSocket server → pipe to our 3D dashboard
  - **Key**: Exact architecture we need — hooks → SQLite → WebSocket → dashboard

### 6. AgentPrism ⭐344 | MIT | TypeScript
**github.com/evilmartians/agent-prism**
- **What**: React components for visualizing traces from AI agents — hierarchical timeline
- **Why it's gold**: Turns traces into visual diagrams — LLM calls, tool executions, agent workflows
- **How to integrate**:
  - Use their React components IN the detail panel when you click an agent
  - Show trace timeline as a nested visualization inside our 3D popup
  - **Key**: Beautiful, ready-made trace visualization components

### 7. ClawMetry ⭐332 | MIT | Python
**github.com/vivekchand/clawmetry**
- **What**: Real-time observability dashboard for OpenClaw agents — "see your agent think"
- **Why it's gold**: Python-native, ClickHouse backend, OpenTelemetry, PyPI package
- **How to integrate**:
  - Install as Python package → auto-instruments our agent calls
  - Feed traces into our dashboard instead of their default UI
  - **Key**: Python-native (matches our stack), easy pip install

---

## 🥈 TIER 2 — HIGHLY USEFUL (Solves specific sub-problems)

### 8. Token Tracker ⭐234 | Python
**github.com/stormzhang/token-tracker**
- Token usage + cost tracking across Claude Code, Codex
- Custom StatusLine + CLI Dashboard with rate limit monitoring
- **Use**: Track real token costs per agent, show in dashboard

### 9. OpsRobot ⭐137 | Apache-2.0 | JavaScript
**github.com/opsrobot-ai/opsrobot**
- Full-link tracing via OTel + eBPF technology
- 24/7 observability for AI agent workflows
- **Use**: eBPF-level process monitoring for our VM

### 10. OpenAEON ⭐82 | MIT | TypeScript
**github.com/openaeon/OpenAEON**
- AI cognitive observability — dialectic flow tracking, memory distillation, knowledge aging visualization
- **Use**: Their memory distillation approach → our episodic memory aging in 3D

### 11. Claude Team Dashboard ⭐46 | MIT | JavaScript
**github.com/mukul975/claude-team-dashboard**
- Real-time monitoring for Claude Code agent teams via WebSocket
- npm package, MCP integration
- **Use**: Simple WebSocket agent status protocol to copy

### 12. OpenClaw Dashboard ⭐36 | MIT | TypeScript
**github.com/ChristianAlmurr/openclaw-dashboard**
- Mission Control for AI agent fleets — cost analytics, memory health, cron pipelines, Kanban
- **Use**: Their Kanban + cron monitoring approach for our task tracking

### 13. Traccia ⭐31 | Apache-2.0 | Python
**github.com/traccia-ai/traccia-py**
- OpenTelemetry-based tracing SDK for AI agents
- Auto-patches OpenAI, Anthropic, requests, HTTP
- **Use**: Drop-in tracing instrumentation for all our agent API calls

### 14. Vibe Cockpit ⭐22 | Rust
**github.com/Dicklesworthstone/vibe_cockpit**
- Real-time monitoring for AI coding agent fleets — session health, output streaming
- **Use**: Their multi-agent session health approach

### 15. OpenSmith ⭐18 | MIT | Python
**github.com/shivnathtathe/opensmith**
- Local-first LangSmith alternative — no cloud, no setup
- **Use**: Local tracing storage + evaluation, private by default

### 16. Claude Ville ⭐11 | JavaScript
**github.com/honorstudio/claude-ville**
- Real-time isometric pixel world for agent teams & swarms
- **Use**: Their swarm visualization approach → our tiny subagent icons

### 17. PM2 Hawkeye ⭐14 | Apache-2.0 | JavaScript
**github.com/orangecoding/pm2-hawkeye**
- Real-time PM2 process monitoring over WebSocket
- CPU, memory, uptime, log streaming, restart controls
- **Use**: Direct system process monitoring → feed into our dashboard

---

## 🥉 TIER 3 — SPECIALIZED (Nice-to-have components)

### 18. Hermes Dashboard ⭐10 | HTML
**github.com/mojomast/hermesdashboard**
- Standalone web dashboard for HERMES AI agent runtime
- Chat, sessions, memory, skills, secrets, config, graph visualization
- **Use**: Directly compatible with our Hermes instance!

### 19. 3DMonitor ⭐5 | TypeScript
**github.com/CubeVi/3DMonitor**
- Electron + Vue 3 3D system monitoring — CPU, GPU, memory, disk, network
- **Use**: Their 3D system metric rendering approach

### 20. Agent Hooks Multi-Agent Observability ⭐6
**github.com/toomas-tt/claude-code-hooks-multi-agent-observability**
- Real-time observability for Claude Code agents with hook event tracking
- **Use**: Hook pattern for capturing agent events

---

## 🔧 ARCHITECTURE PLAN — How to Make It All Work

### Data Pipeline (the missing piece)
```
Agent Actions → Hooks/Webhook → FastAPI WebSocket Server → Dashboard
     ↓                              ↓
  SQLite (sessions)          Redis (live state)
     ↓                              ↓
  Google Drive (archive)    ClickHouse (traces)
```

### Stack
1. **OpenLIT SDK** — auto-instruments all LLM calls, sends OTel traces
2. **Aegra** — FastAPI backend for session management + WebSocket push
3. **SQLite** — session store (already have episodic.db)
4. **Redis** — live agent state, positions, status (already running)
5. **AgentPrism** — React trace visualization in detail panels
6. **OpenClaw Office patterns** — WebSocket protocol, agent avatars
7. **Traccia** — Python tracing SDK for API call instrumentation

### Implementation Order
1. **WebSocket server** (FastAPI) — push real agent data to dashboard
2. **Agent hooks** — capture every agent action (tool calls, LLM requests, file ops)
3. **Session store** (SQLite) — track session start/end, tasks, summaries
4. **Live state** (Redis) — agent positions, status, current task, subagents
5. **3D rendering** — subagent particles, activity trails, session info panels
6. **System monitoring** — psutil → Redis → dashboard (CPU, RAM, disk, network)
7. **Trace visualization** — AgentPrism components in click-detail panels
8. **Subagent hierarchy** — parent→child tree rendered as neuron clusters

### What Each Click Should Show
- **Agent click**: Live sessions, current task, subagent count, token usage, recent activity feed, past sessions with summaries, next steps
- **Subagent click**: Parent agent, spawned time, current work, tool usage
- **Region click**: Backend status, file count, connected agents, memory health
- **Neuron click**: Type, synapse count, fire history, region affiliation
- **System click** (new): CPU/RAM/disk/network per process, service health checks

---

## 📊 COMPATIBILITY MATRIX

| Repo | License | Python | WebSocket | 3D/Viz | Sessions | System Mon | Subagents |
|------|---------|--------|-----------|--------|----------|------------|-----------|
| OpenLIT | Apache-2.0 | ✅ | ✅ | ❌ (Grafana) | ✅ | ✅ GPU | ❌ |
| Aegra | Apache-2.0 | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| OpenClaw Office | MIT | ❌ | ✅ | ✅ 2D iso | ✅ | ❌ | ✅ |
| AgentScope Studio | Apache-2.0 | ❌ | ✅ | ✅ timeline | ✅ | ❌ | ✅ |
| Claude Code Monitor | MIT | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| AgentPrism | MIT | ❌ | ❌ | ✅ React | ✅ | ❌ | ❌ |
| ClawMetry | MIT | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| Hermes Dashboard | ? | ✅ | ❌ | ✅ graph | ✅ | ❌ | ❌ |

**None of them have everything.** We combine the best parts:
- OpenLIT for tracing + GPU monitoring
- Aegra for session management + WebSocket backend
- OpenClaw Office for agent status protocol
- Claude Code Monitor for hooks + SQLite session schema
- AgentPrism for trace visualization components
- Our existing Three.js dashboard for 3D rendering
