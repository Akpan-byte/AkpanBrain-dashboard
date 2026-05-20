#!/usr/bin/env python3
"""Build dashboard HTML with embedded live data from API"""
import json, os, sys
from urllib.request import urlopen

DIR = os.path.dirname(os.path.abspath(__file__))
API = "http://localhost:8199"
TEMPLATE = "index_v11.html"

def fetch(path):
 try:
  with urlopen(f"{API}{path}", timeout=3) as r:
   return json.loads(r.read())
 except:
  return {}

def build():
 agents = fetch("/api/agents")
 brain = fetch("/api/brain")
 tree = fetch("/api/tree")
 metrics = fetch("/api/metrics")
 stats = fetch("/api/stats")
 
 with open(os.path.join(DIR, TEMPLATE)) as f:
  html = f.read()
 
 # agents is a list
 agents_dict = {}
 if isinstance(agents, list):
  for a in agents:
   agents_dict[a["name"]] = a
 elif isinstance(agents, dict):
  agents_dict = agents
 
 embedded = json.dumps({
  "agents": agents_dict,
  "brain": brain,
  "tree": tree.get("roots", tree) if isinstance(tree, dict) else [],
  "metrics": metrics,
  "stats": stats,
 }, separators=(',', ':'))
 
 html = html.replace('$EMBEDded$', embedded)
 
 with open(os.path.join(DIR, "index.html"), "w") as f:
  f.write(html)
 
 active_count = sum(1 for a in (agents if isinstance(agents, list) else agents.values()) if a.get("running") or a.get("status") == "active")
 total_count = len(agents) if isinstance(agents, (list, dict)) else 0
 print(f"Dashboard built: {len(html)} bytes, {total_count} agents ({active_count} active)")

if __name__ == "__main__":
 build()
