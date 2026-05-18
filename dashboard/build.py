#!/usr/bin/env python3
"""Build dashboard HTML with embedded live data from API"""
import json, sys
from urllib.request import urlopen

API = "http://localhost:8199"

def fetch(path):
    try:
        with urlopen(f"{API}{path}", timeout=3) as r:
            return json.loads(r.read())
    except:
        return {}

def build():
    agents = fetch("/api/agents")
    brain = fetch("/api/brain")
    positions = fetch("/api/positions")
    regions_data = fetch("/api/regions")
    
    # Read template
    with open("/config/brain/dashboard/index_v5.html") as f:
        html = f.read()
    
    # Build embedded data
    embedded = json.dumps({
        "agents": agents,
        "brain": brain,
        "positions": positions,
        "regions": regions_data.get("positions", {}),
    }, separators=(',',':'))
    
    # Replace placeholder
    html = html.replace('$EMBEDded$', embedded)
    
    # Write as index.html for Vercel
    with open("/config/brain/dashboard/index.html", "w") as f:
        f.write(html)
    
    active = sum(1 for a in agents.values() if a.get("status") == "active")
    total_files = sum(b.get("file_count", 0) for b in brain.values()) if brain else 0
    print(f"Dashboard built: {len(html)} bytes, {len(agents)} agents ({active} active), {total_files} files, {len(positions)} positions")

if __name__ == "__main__":
    build()
