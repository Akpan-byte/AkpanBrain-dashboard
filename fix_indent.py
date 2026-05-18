#!/usr/bin/env python3
"""Fix indentation in api_server.py get_activity function"""

path = '/config/brain/api_server.py'
lines = open(path).readlines()

# Find line numbers of the get_activity function
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if 'def get_activity()' in line:
        start_idx = i
    if start_idx is not None and i > start_idx and line.strip() and not line.startswith(' ') and 'def ' in line:
        end_idx = i
        break

if start_idx is None:
    print("ERROR: get_activity not found")
    exit(1)

print(f"Found get_activity at line {start_idx+1}, ends before line {end_idx+1 if end_idx else 'EOF'}")

# Replace the function
new_func = '''def get_activity():
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

'''

if end_idx:
    new_lines = lines[:start_idx] + [new_func] + lines[end_idx:]
else:
    new_lines = lines[:start_idx] + [new_func]

open(path, 'w').writelines(new_lines)
print(f"Wrote {len(new_lines)} lines")
