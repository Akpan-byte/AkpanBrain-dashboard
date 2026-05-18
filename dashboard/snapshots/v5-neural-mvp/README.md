# AkpanBrain Dashboard — Snapshot v5 Neural MVP

**Saved:** 2026-06-15
**Deployed at:** brain-gules-eight.vercel.app

## What's in this snapshot
- `index.html` — Template with $EMBEDded$ placeholder (needs build.py)
- `index_built.html` — Fully built standalone HTML with embedded data (open directly in browser)
- `build.py` — Data embedding script (fetches from API localhost:8199)
- `api_server_v4.py` — Backend API server (agents, positions, brain, WebSocket)

## Known Issues (why we're moving to v6)
1. **Performance crash** — 60 neurons × 2 meshes each + ~200 synapse lines + 16 agent orbs = ~800 objects. Too heavy for mobile/low-end. Browser tab crashes.
2. **No mobile layout** — Sidebar (320px) steals all screen on portrait. No responsive design.
3. **No bloom** — Additive blending compensates but no real UnrealBloomPass (r160 removed examples/js/)
4. **No drill-down** — Can't click into regions to see files/data

## Scene Stats (at time of snapshot)
- 16 agents (5 active: hermes, gemini-cli, kimi-code, codebuff, jcode)
- 6 brain regions with labeled sprites
- 60 neurons (10 hub + 50 regular)
- ~200 synapse connections
- Electrical pulse system (traveling particles)
- Auto-rotating camera with drag/scroll

## To restore
1. Copy `index_built.html` to any web server or open locally
2. Or run `build.py` with API server v4 on port 8199, then deploy
