#!/usr/bin/env python3
"""Research GitHub repos for AkpanBrain dashboard capabilities."""
import json, urllib.request, urllib.parse

token = open('/config/.git-credentials').read().strip().split(':')[2].split('@')[0]

queries = [
    "agent observability dashboard real-time",
    "multi-agent monitoring visualization",
    "AI agent session tracking dashboard",
    "swarm visualization three.js",
    "langfuse alternative open source",
    "agent telemetry tracing LLM",
    "real-time system monitoring 3d dashboard",
    "websocket agent status dashboard",
    "subagent orchestration visualization",
    "agent activity feed live dashboard",
    "agent tracing opentelemetry LLM",
    "process monitoring 3d visualization web",
    "neural network visualization dashboard three.js",
    "agent fleet monitoring dashboard",
    "langsmith open source alternative",
    "crewai monitoring dashboard",
    "autogen monitoring visualization",
    "ai agent memory visualization",
    "real-time log dashboard websocket",
    "hierarchical agent visualization",
]

all_repos = {}

for q in queries:
    url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(q)}&sort=stars&order=desc&per_page=5"
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'token {token}')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            items = data.get('items', [])
            for i in items[:5]:
                name = i['full_name']
                if name not in all_repos:
                    all_repos[name] = {
                        'stars': i.get('stargazers_count') or 0,
                        'updated': (i.get('updated_at') or '')[:10],
                        'desc': (i.get('description') or 'No description')[:120],
                        'lang': i.get('language') or '?',
                        'license': (i.get('license') or {}).get('spdx_id', '') if i.get('license') else '',
                        'url': i.get('html_url', ''),
                        'topics': i.get('topics', []),
                        'forks': i.get('forks_count') or 0,
                    }
    except Exception as e:
        pass

# Sort by stars
sorted_repos = sorted(all_repos.items(), key=lambda x: x[1]['stars'], reverse=True)

# Output
for name, r in sorted_repos[:40]:
    stars = r['stars'] or 0
    lang = r['lang'] or '?'
    lic = r['license'] or '?'
    print(f"⭐{stars:>5} | {name[:55]:55} | {str(lang):10} | {lic:15} | {r['updated']} | {r['desc'][:70]}")

print(f"\n--- Total unique repos found: {len(all_repos)} ---")
