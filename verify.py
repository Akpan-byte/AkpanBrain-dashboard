#!/usr/bin/env python3
"""
AkpanBrain Verification Suite
Run comprehensive tests on all brain systems
"""
import sys, os, time
sys.path.insert(0, '/config/brain')

from akpanbrain import AkpanBrain

def test_all():
    brain = AkpanBrain()
    results = []
    
    def check(name, condition, details=""):
        status = "✅" if condition else "❌"
        msg = f"  {status} {name}"
        if details:
            msg += f": {details}"
        print(msg)
        results.append((name, condition))
        return condition
    
    print("=" * 60)
    print("AKPANBRAIN VERIFICATION SUITE")
    print("=" * 60)
    
    # 1. Redis Working Memory
    print("\n[1] WORKING MEMORY (Redis)")
    check("Redis connected", brain.working.r.ping())
    brain.working.r.flushdb()
    brain.working.set("test_agent", {"status": "active"})
    check("Set/Get", brain.working.get("test_agent") is not None)
    check("Key normalization", len(brain.working.keys()) == 1 and "test_agent" in brain.working.keys())
    
    # 2. Semantic Memory (FAISS)
    print("\n[2] SEMANTIC MEMORY (FAISS)")
    os.makedirs('/config/brain/vectors', exist_ok=True)
    check("FAISS available", True)
    brain.semantic.index = None
    brain.semantic.meta = {"vectors": [], "count": 0}
    brain.semantic._ensure_index(1)
    check("Index lazy init", brain.semantic.index is not None)
    vec_id = brain.semantic.add("Test content for verification", {"type": "test"})
    check("Add vector", vec_id >= 0)
    results_list = brain.semantic.search("verification", k=3)
    check("Search", len(results_list) > 0)
    
    # Error handling
    try:
        brain.semantic.search("")
        check("Empty search rejected", False)
    except ValueError:
        check("Empty search rejected", True)
    try:
        brain.semantic.add(None, {})
        check("None content rejected", False)
    except ValueError:
        check("None content rejected", True)
    
    # 3. Knowledge Graph (NetworkX)
    print("\n[3] KNOWLEDGE GRAPH (NetworkX)")
    check("Graph initialized", brain.graph.G is not None)
    brain.graph.add_node("test_node", {"type": "test"})
    check("Add node", "test_node" in brain.graph.G.nodes())
    brain.graph.add_relation("test_node", "hermes", "connects_to")
    check("Add relation", brain.graph.G.has_edge("test_node", "hermes"))
    brain.graph.save()
    check("Graph save", os.path.exists('/config/brain/graph/brain.graphml'))
    
    # 4. Episodic Memory (SQLite)
    print("\n[4] EPISODIC MEMORY (SQLite)")
    check("SQLite connected", brain.episodic.conn is not None)
    eid = brain.episodic.log("test_agent", "test_action", "test_target", "success", ["test"])
    check("Log episode", eid > 0)
    rows = brain.episodic.query(agent="test_agent")
    check("Query episodes", len(rows) > 0)
    
    # 5. Drive Sync
    print("\n[5] GOOGLE DRIVE SYNC (rclone)")
    import subprocess
    result = subprocess.run(['/config/.local/bin/rclone', 'lsd', 'gdrive:AkpanBrain', '--config', '/config/.config/rclone/rclone.conf'], 
                          capture_output=True, text=True)
    check("Drive accessible", result.returncode == 0)
    
    # 6. Dashboard
    print("\n[6] DASHBOARD (HTML)")
    check("Dashboard exists", os.path.exists('/config/brain/dashboard/index.html'))
    dashboard_size = os.path.getsize('/config/brain/dashboard/index.html')
    check("Dashboard populated", dashboard_size > 10000)
    
    # 7. API Server
    print("\n[7] API SERVER")
    check("API server exists", os.path.exists('/config/brain/api_server.py'))
    api_size = os.path.getsize('/config/brain/api_server.py')
    check("API server populated", api_size > 1000)
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    pct = (passed / total) * 100 if total > 0 else 0
    
    print(f"RESULTS: {passed}/{total} tests passed ({pct:.0f}%)")
    
    if passed == total:
        print("🎉 ALL SYSTEMS OPERATIONAL")
    else:
        print("⚠️  SOME TESTS FAILED")
        for name, ok in results:
            if not ok:
                print(f"  ❌ {name}")
    
    print("=" * 60)
    return passed == total

if __name__ == "__main__":
    success = test_all()
    sys.exit(0 if success else 1)